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
