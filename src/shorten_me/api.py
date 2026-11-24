"""HTTP routes."""

import math
from collections.abc import Iterator
from datetime import datetime
from importlib import resources
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import AwareDatetime, BaseModel
from sqlalchemy.orm import Session

from shorten_me.ratelimit import RateLimited
from shorten_me.service import AliasTaken, LinkExpired, LinkNotFound, LinkService
from shorten_me.urls import MAX_URL_LENGTH

router = APIRouter()
MAX_BODY_BYTES = 12 * MAX_URL_LENGTH + 1024
HOME_PAGE = resources.files("shorten_me").joinpath("static/index.html").read_text()


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


class LinkStats(BaseModel):
    """What is stored about a link."""

    code: str
    long_url: str
    hits: int
    created_at: datetime
    expires_at: datetime | None


def get_service(request: Request) -> Iterator[LinkService]:
    """Give each request its own session."""
    with Session(request.app.state.engine) as session:
        yield LinkService(session, clock=request.app.state.clock)


Service = Annotated[LinkService, Depends(get_service)]


def limit_rate(request: Request) -> None:
    """Count the request against its client's rate limit, if limiting is on."""
    limiter = request.app.state.rate_limiter
    if limiter is None:
        return
    if request.client is None:
        raise RuntimeError("the server gave no client address to rate limit by")
    limiter.take(request.client.host)


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    return HOME_PAGE


@router.post("/", dependencies=[Depends(limit_rate)])
def shorten(body: ShortenRequest, service: Service, request: Request) -> ShortenResponse:
    code = service.shorten(body.long_url, body.alias, body.expires_at)
    return ShortenResponse(
        code=code,
        short_url=str(request.url_for("follow", code=code)),
        expires_at=service.find(code).expires_at,
    )


@router.get("/{code}", response_class=RedirectResponse)
def follow(code: str, service: Service) -> str:
    return service.resolve(code)


@router.head("/{code}", response_class=RedirectResponse, include_in_schema=False)
def preview(code: str, service: Service) -> str:
    return service.preview(code)


@router.get("/{code}/stats")
def stats(code: str, service: Service) -> LinkStats:
    link = service.find(code)
    return LinkStats(
        code=code,
        long_url=link.long_url,
        hits=link.hits,
        created_at=link.created_at,
        expires_at=link.expires_at,
    )


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


def invalid_input(_request: Request, error: ValueError) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=422)
