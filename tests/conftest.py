import gc
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from shorten_me.models import Base
from shorten_me.schema import create_db_engine
from shorten_me.service import LinkService


@pytest.fixture(autouse=True)
def collect_garbage():
    """Free leaked objects after each test, so a ResourceWarning fails the test that leaked."""
    yield
    gc.collect()


@pytest.fixture
def session():
    engine = create_db_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def service(session):
    return LinkService(session, clock=lambda: datetime(2026, 1, 1, tzinfo=UTC))
