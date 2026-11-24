from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from shorten_me.app import create_app
from shorten_me.settings import Settings


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}"))
    with TestClient(app, follow_redirects=False) as client:
        yield client


def test_short_link_redirects_to_the_long_url(client):
    code = client.post("/", json={"long_url": "https://example.com/a"}).json()["code"]
    response = client.get(f"/{code}")
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/a"


def test_invalid_url_returns_422(client):
    assert client.post("/", json={"long_url": "ftp://example.com"}).status_code == 422


def test_unknown_short_code_returns_404(client):
    assert client.get("/vcTJ").status_code == 404


def test_alias_taken_by_another_url_returns_409(client):
    client.post("/", json={"long_url": "https://example.com/a", "alias": "my-link"})
    response = client.post("/", json={"long_url": "https://example.com/b", "alias": "my-link"})
    assert response.status_code == 409


def test_expired_short_link_returns_410(client):
    body = {"long_url": "https://example.com/a", "expires_at": "2030-01-01T00:00:00Z"}
    code = client.post("/", json=body).json()["code"]
    client.app.state.clock = lambda: datetime(2031, 1, 1, tzinfo=UTC)
    assert client.get(f"/{code}").status_code == 410


def test_too_many_requests_return_429_with_retry_after(tmp_path):
    settings = Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", rate_limit=1)
    with TestClient(create_app(settings)) as client:
        client.post("/", json={"long_url": "https://example.com/a"})
        response = client.post("/", json={"long_url": "https://example.com/a"})
    assert response.status_code == 429
    assert 0 < int(response.headers["retry-after"]) <= 60


def test_home_page_serves_the_form(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<form id="shorten">' in response.text
