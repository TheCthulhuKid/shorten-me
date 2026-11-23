"""Build and run the web application."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine

from shorten_me import api
from shorten_me.aliases import InvalidAlias
from shorten_me.ratelimit import RateLimited, RateLimiter
from shorten_me.schema import upgrade_to_head
from shorten_me.service import AliasTaken, InvalidExpiry, LinkExpired, LinkNotFound
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

    app = FastAPI(title="shorten-me", debug=settings.debug, lifespan=lifespan)
    app.state.engine = engine
    app.state.clock = lambda: datetime.now(UTC)
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


def main() -> None:
    """Run the service with settings from the environment."""
    settings = Settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
