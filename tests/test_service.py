from datetime import UTC, datetime

import pytest

from shorten_me.models import Link
from shorten_me.service import LinkExpired, LinkService


def test_shortening_the_same_url_twice_returns_the_same_code(service, session):
    first = service.shorten("https://example.com/a")
    assert service.shorten("https://example.com/a") == first
    assert session.query(Link).count() == 1


def test_new_link_records_the_time_from_the_clock(service, session):
    service.shorten("https://example.com/a")
    assert session.query(Link).one().created_at == datetime(2026, 1, 1)


def test_following_a_short_link_counts_a_hit(service, session):
    code = service.shorten("https://example.com/a")
    assert service.resolve(code) == "https://example.com/a"
    service.resolve(code)
    assert session.query(Link).one().hits == 2


def test_stats_do_not_count_a_hit(service):
    code = service.shorten("https://example.com/a")
    assert service.find(code).hits == 0


def test_custom_alias_resolves_to_the_long_url(service):
    assert service.shorten("https://example.com/a", alias="my-link") == "my-link"
    assert service.resolve("my-link") == "https://example.com/a"


def test_expired_link_no_longer_resolves(session):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    service = LinkService(session, clock=lambda: now)
    code = service.shorten("https://example.com/a", expires_at=datetime(2026, 1, 2, tzinfo=UTC))
    assert service.resolve(code) == "https://example.com/a"
    now = datetime(2026, 1, 3, tzinfo=UTC)
    with pytest.raises(LinkExpired):
        service.resolve(code)


def test_shortening_again_never_brings_the_expiry_forward(service):
    code = service.shorten("https://example.com/a", expires_at=datetime(2027, 1, 1, tzinfo=UTC))
    service.shorten("https://example.com/a", expires_at=datetime(2026, 6, 1, tzinfo=UTC))
    assert service.find(code).expires_at == datetime(2027, 1, 1)
