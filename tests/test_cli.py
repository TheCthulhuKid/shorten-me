from datetime import timedelta

import pytest

from shorten_me import cli
from shorten_me.schema import create_db_engine, upgrade_to_head
from shorten_me.service import open_service


@pytest.fixture
def database(database_url, monkeypatch):
    upgrade_to_head(database_url)
    monkeypatch.setenv("SHORTEN_ME_DATABASE_URL", database_url)
    engine = create_db_engine(database_url)
    yield engine
    engine.dispose()


def test_cleanup_command_deletes_long_expired_links(database, clock, capsys):
    with open_service(database, clock) as service:
        service.shorten("https://example.com/a", expires_at=clock.now + timedelta(days=1))
        service.shorten("https://example.com/b")
    cli.main(["cleanup"])
    assert capsys.readouterr().out == "Expired links deleted: 1\n"


def test_cleanup_rejects_a_negative_grace_period(database):
    with pytest.raises(SystemExit, match="negative"):
        cli.main(["cleanup", "--grace-days", "-1"])


def test_cleanup_refuses_a_database_that_does_not_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("SHORTEN_ME_DATABASE_URL", f"sqlite:///{tmp_path / 'missing.db'}")
    with pytest.raises(SystemExit, match="missing.db"):
        cli.main(["cleanup"])
    assert not (tmp_path / "missing.db").exists()


def test_no_command_serves_with_the_configured_proxy_settings(monkeypatch):
    served = {}
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **options: served.update(options))
    monkeypatch.setenv("SHORTEN_ME_FORWARDED_ALLOW_IPS", "10.0.0.1")
    cli.main([])
    assert served["proxy_headers"] is True
    assert served["forwarded_allow_ips"] == "10.0.0.1"
