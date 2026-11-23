"""Build and run the web application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import uvicorn
from fastapi import FastAPI
from sqlalchemy import create_engine

from shorten_me import api
from shorten_me.models import Base
from shorten_me.service import LinkNotFound
from shorten_me.settings import Settings
from shorten_me.urls import InvalidUrl


def create_app(settings: Settings) -> FastAPI:
    """Return the application wired to the database in `settings`."""
    engine = create_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        Base.metadata.create_all(engine)
        yield
        engine.dispose()

    app = FastAPI(title="shorten-me", debug=settings.debug, lifespan=lifespan)
    app.state.engine = engine
    app.state.clock = lambda: datetime.now(UTC)
    app.include_router(api.router)
    app.add_exception_handler(LinkNotFound, api.link_not_found)
    app.add_exception_handler(InvalidUrl, api.invalid_url)
    return app


def main() -> None:
    """Run the service with settings from the environment."""
    settings = Settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)
