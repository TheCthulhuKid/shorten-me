"""HTTP routes."""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shorten_me.service import LinkNotFound, LinkService
from shorten_me.urls import InvalidUrl

router = APIRouter()


class ShortenRequest(BaseModel):
    """Body of `POST /`."""

    long_url: str


class ShortenResponse(BaseModel):
    """The short code for a long URL and the full short link."""

    code: str
    short_url: str


class LinkStats(BaseModel):
    """What is stored about a link."""

    code: str
    long_url: str
    hits: int
    created_at: datetime


def get_service(request: Request) -> Iterator[LinkService]:
    """Give each request its own session."""
    with Session(request.app.state.engine) as session:
        yield LinkService(session, clock=request.app.state.clock)


Service = Annotated[LinkService, Depends(get_service)]


@router.post("/")
def shorten(body: ShortenRequest, service: Service, request: Request) -> ShortenResponse:
    code = service.shorten(body.long_url)
    return ShortenResponse(code=code, short_url=str(request.url_for("follow", code=code)))


@router.get("/{code}", response_class=RedirectResponse)
def follow(code: str, service: Service) -> str:
    return service.resolve(code)


@router.get("/{code}/stats")
def stats(code: str, service: Service) -> LinkStats:
    link = service.find(code)
    return LinkStats(code=code, long_url=link.long_url, hits=link.hits, created_at=link.created_at)


def link_not_found(request: Request, error: LinkNotFound) -> JSONResponse:
    return JSONResponse({"detail": "Short URL not found"}, status_code=404)


def invalid_url(request: Request, error: InvalidUrl) -> JSONResponse:
    return JSONResponse({"detail": str(error)}, status_code=422)
