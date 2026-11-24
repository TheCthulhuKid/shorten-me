"""HTTP routes."""

import base64
import hashlib
import math
import re
from collections.abc import Iterator
from datetime import datetime
from importlib import resources
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import AwareDatetime, BaseModel, ConfigDict

from shorten_me.aliases import ALIAS_PATTERN
from shorten_me.errors import InvalidInput
from shorten_me.ratelimit import RateLimited, RateLimiter, client_key
from shorten_me.service import AliasTaken, LinkExpired, LinkNotFound, LinkService, open_service
from shorten_me.urls import MAX_URL_LENGTH

router = APIRouter()
MAX_BODY_BYTES = 12 * MAX_URL_LENGTH + 1024
_HOME_TEMPLATE = resources.files("shorten_me").joinpath("static/index.html").read_text()
HOME_PAGE = _HOME_TEMPLATE.replace("__ALIAS_PATTERN__", ALIAS_PATTERN.pattern)


def _inline_hash(tag: str) -> str:
    content = re.search(rf"<{tag}>(.*?)</{tag}>", HOME_PAGE, re.DOTALL).group(1)
    digest = hashlib.sha256(content.encode()).digest()
    return f"'sha256-{base64.b64encode(digest).decode()}'"


HOME_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; "
        f"script-src {_inline_hash('script')}; "
        f"style-src {_inline_hash('style')}; "
        "connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


class ShortenRequest(BaseModel):
    """Body of `POST /`."""

    long_url: str
    alias: str | None = None
    expires_at: AwareDatetime | None = None


class ShortenResponse(BaseModel):
    """The short code for a long URL, the full short link and when it expires."""

    code: str
    short_url: str
    expires_at: datetime | None


class LinkDetails(BaseModel):
    """What is stored about a link."""

    model_config = ConfigDict(from_attributes=True)

    long_url: str
    hits: int
    created_at: datetime
    expires_at: datetime | None


class LinkStats(LinkDetails):
    """A link's details and the code they were asked for by."""

    code: str


def get_service(request: Request) -> Iterator[LinkService]:
    """Give each request its own session."""
    state = request.app.state
    with open_service(state.engine, state.clock, state.public_url) as service:
        yield service


Service = Annotated[LinkService, Depends(get_service)]


def limit_creation(request: Request) -> None:
    """Count the request against its client's limit for creating links, if that is on."""
    _take(request, request.app.state.creation_limiter)


def limit_lookups(request: Request) -> None:
    """Count the request against its client's limit for looking codes up, if that is on."""
    _take(request, request.app.state.lookup_limiter)


def _take(request: Request, limiter: RateLimiter | None) -> None:
    if limiter is None:
        return
    if request.client is None:
        raise RuntimeError("the server gave no client address to rate limit by")
    limiter.take(client_key(request.client.host))


@router.get("/", include_in_schema=False)
def home() -> HTMLResponse:
    return HTMLResponse(HOME_PAGE, headers=HOME_HEADERS)


@router.post("/", dependencies=[Depends(limit_creation)])
def shorten(body: ShortenRequest, service: Service, request: Request) -> ShortenResponse:
    link = service.shorten(body.long_url, body.alias, body.expires_at)
    return ShortenResponse(
        code=link.code,
        short_url=_short_url(request, link.code),
        expires_at=link.expires_at,
    )


def _short_url(request: Request, code: str) -> str:
    public_url = request.app.state.public_url
    if public_url is None:
        return str(request.url_for("follow", code=code))
    return f"{public_url}/{code}"


@router.get("/{code}", response_class=RedirectResponse, dependencies=[Depends(limit_lookups)])
def follow(code: str, service: Service) -> str:
    return service.resolve(code)


@router.head(
    "/{code}",
    response_class=RedirectResponse,
    include_in_schema=False,
    dependencies=[Depends(limit_lookups)],
)
def preview(code: str, service: Service) -> str:
    return service.preview(code)


@router.get("/{code}/stats", dependencies=[Depends(limit_lookups)])
def stats(code: str, service: Service) -> LinkStats:
    details = LinkDetails.model_validate(service.find(code))
    return LinkStats(code=code, **details.model_dump())


def link_not_found(_request: Request, _error: LinkNotFound) -> JSONResponse:
    return JSONResponse({"detail": "Short URL not found"}, status_code=404)


def link_expired(_request: Request, _error: LinkExpired) -> JSONResponse:
    return JSONResponse({"detail": "Short URL has expired"}, status_code=410)


def rate_limited(_request: Request, error: RateLimited) -> JSONResponse:
    return JSONResponse(
        {"detail": "Too many requests"},
        status_code=429,
        headers={"Retry-After": str(math.ceil(error.retry_after))},
    )


def alias_taken(_request: Request, _error: AliasTaken) -> JSONResponse:
    return JSONResponse({"detail": "Alias is already in use"}, status_code=409)


def invalid_input(_request: Request, error: InvalidInput) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=422)


EXCEPTION_HANDLERS = {
    LinkNotFound: link_not_found,
    LinkExpired: link_expired,
    RateLimited: rate_limited,
    AliasTaken: alias_taken,
    InvalidInput: invalid_input,
}
