from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from shorten_me.api import MAX_BODY_BYTES
from shorten_me.app import create_app, main
from shorten_me.schema import upgrade_to_head
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


def test_oversized_request_body_returns_413(client):
    long_url = "https://example.com/" + "a" * MAX_BODY_BYTES
    assert client.post("/", json={"long_url": long_url}).status_code == 413
    chunks = (chunk for chunk in [b'{"long_url": "', long_url.encode(), b'"}'])
    assert client.post("/", content=chunks).status_code == 413


def test_times_in_responses_are_in_utc_with_an_offset(client):
    body = {"long_url": "https://example.com/a", "expires_at": "2999-01-01T12:00:00+02:00"}
    assert client.post("/", json=body).json()["expires_at"] == "2999-01-01T10:00:00Z"


def test_cleanup_refuses_a_database_that_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTEN_ME_DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    with pytest.raises(SystemExit, match="missing.db"):
        main(["cleanup"])
    assert not (tmp_path / "missing.db").exists()


def test_head_request_redirects_without_counting_a_hit(client):
    code = client.post("/", json={"long_url": "https://example.com/a"}).json()["code"]
    response = client.head(f"/{code}")
    assert response.status_code == 307
    assert response.headers["location"] == "https://example.com/a"
    assert client.get(f"/{code}/stats").json()["hits"] == 0


def test_cleanup_rejects_a_negative_grace_period(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    upgrade_to_head(url)
    monkeypatch.setenv("SHORTEN_ME_DATABASE_URL", url)
    with pytest.raises(SystemExit, match="negative"):
        main(["cleanup", "--grace-days", "-1"])
