"""Build and run the web application, and the command line around it."""

import argparse
import time
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from shorten_me import api
from shorten_me.aliases import InvalidAlias
from shorten_me.ratelimit import RateLimited, RateLimiter
from shorten_me.schema import upgrade_to_head
from shorten_me.service import (
    AliasTaken,
    InvalidExpiry,
    LinkExpired,
    LinkNotFound,
    LinkService,
)
from shorten_me.settings import Settings
from shorten_me.urls import InvalidUrl


def create_app(settings: Settings) -> FastAPI:
    """Return the application wired to the database in `settings`."""
    engine = create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        upgrade_to_head(settings.database_url)
        yield
        engine.dispose()

    app = FastAPI(
        title="shorten-me",
        debug=settings.debug,
        lifespan=lifespan,
        max_body_size=api.MAX_BODY_BYTES,
    )
    app.state.engine = engine
    app.state.clock = utc_now
    app.state.rate_limiter = (
        RateLimiter(settings.rate_limit, period=60, clock=time.monotonic)
        if settings.rate_limit
        else None
    )
    app.include_router(api.router)
    app.add_exception_handler(LinkNotFound, api.link_not_found)
    app.add_exception_handler(LinkExpired, api.link_expired)
    app.add_exception_handler(RateLimited, api.rate_limited)
    app.add_exception_handler(AliasTaken, api.alias_taken)
    app.add_exception_handler(InvalidUrl, api.invalid_input)
    app.add_exception_handler(InvalidAlias, api.invalid_input)
    app.add_exception_handler(InvalidExpiry, api.invalid_input)
    return app


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)


def main(argv: Sequence[str] | None = None) -> None:
    """Run the service, or another command, with settings from the environment."""
    parser = argparse.ArgumentParser(
        prog="shorten-me", description="A small URL shortener. Without a command, run the service."
    )
    parser.set_defaults(command=serve)
    commands = parser.add_subparsers(title="commands")
    cleanup_parser = commands.add_parser("cleanup", help="delete links that expired long ago")
    cleanup_parser.add_argument(
        "--grace-days",
        type=int,
        default=30,
        help="keep links for this many days after they expire (default: %(default)s)",
    )
    cleanup_parser.set_defaults(command=cleanup)
    args = parser.parse_args(argv)
    args.command(Settings(), args)


def cleanup(settings: Settings, args: argparse.Namespace) -> None:
    """Delete links whose expiry passed more than `--grace-days` ago."""
    upgrade_to_head(settings.database_url)
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as session:
            service = LinkService(session, clock=utc_now)
            deleted = service.delete_expired(timedelta(days=args.grace_days))
    finally:
        engine.dispose()
    print(f"Expired links deleted: {deleted}")


def serve(settings: Settings, args: argparse.Namespace) -> None:
    """Run the web service."""
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        proxy_headers=settings.proxy_headers,
        forwarded_allow_ips=settings.forwarded_allow_ips,
    )
