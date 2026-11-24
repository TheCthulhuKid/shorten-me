"""Build the web application."""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI

from shorten_me import api
from shorten_me.ratelimit import RateLimiter
from shorten_me.schema import create_db_engine, upgrade_to_head
from shorten_me.settings import Settings

RATE_LIMIT_PERIOD_SECONDS = 60


def create_app(settings: Settings) -> FastAPI:
    """Return the application wired to the database in `settings`."""
    engine = create_db_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        upgrade_to_head(settings.database_url)
        yield
        engine.dispose()

    app = FastAPI(
        title="shorten-me",
        lifespan=lifespan,
        max_body_size=api.MAX_BODY_BYTES,
        exception_handlers=api.EXCEPTION_HANDLERS,
    )
    app.state.engine = engine
    app.state.clock = utc_now
    app.state.public_url = settings.public_url and str(settings.public_url).rstrip("/")
    app.state.creation_limiter = _limiter(settings.rate_limit)
    app.state.lookup_limiter = _limiter(settings.lookup_rate_limit)
    app.include_router(api.router)
    return app


def _limiter(per_minute: int) -> RateLimiter | None:
    if per_minute == 0:
        return None
    return RateLimiter(per_minute, RATE_LIMIT_PERIOD_SECONDS, clock=time.monotonic)


def utc_now() -> datetime:
    """Return the current time in UTC."""
    return datetime.now(UTC)
