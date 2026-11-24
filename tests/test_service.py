from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from shorten_me.expiry import InvalidExpiry
from shorten_me.models import Alias, Link
from shorten_me.service import AliasTaken, LinkExpired, ShortLink


def test_shortening_the_same_url_twice_returns_the_same_code(service, session):
    first = service.shorten("https://example.com/a")
    assert service.shorten("https://example.com/a") == first
    assert session.query(Link).count() == 1


def test_new_link_records_the_time_from_the_clock(service, session):
    service.shorten("https://example.com/a")
    assert session.query(Link).one().created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_following_a_short_link_counts_a_hit(service, session):
    code = service.shorten("https://example.com/a").code
    assert service.resolve(code) == "https://example.com/a"
    service.resolve(code)
    assert session.query(Link).one().hits == 2


def test_stats_do_not_count_a_hit(service):
    code = service.shorten("https://example.com/a").code
    assert service.find(code).hits == 0


def test_custom_alias_resolves_to_the_long_url(service):
    assert service.shorten("https://example.com/a", alias="my-link") == ShortLink("my-link", None)
    assert service.resolve("my-link") == "https://example.com/a"


def test_expired_link_no_longer_resolves(service, clock):
    code = service.shorten(
        "https://example.com/a", expires_at=datetime(2026, 1, 2, tzinfo=UTC)
    ).code
    assert service.resolve(code) == "https://example.com/a"
    clock.now = datetime(2026, 1, 3, tzinfo=UTC)
    with pytest.raises(LinkExpired):
        service.resolve(code)


def test_shortening_again_never_brings_the_expiry_forward(service):
    code = service.shorten(
        "https://example.com/a", expires_at=datetime(2027, 1, 1, tzinfo=UTC)
    ).code
    service.shorten("https://example.com/a", expires_at=datetime(2026, 6, 1, tzinfo=UTC))
    assert service.find(code).expires_at == datetime(2027, 1, 1, tzinfo=UTC)


def test_shortening_again_without_an_expiry_makes_the_link_permanent(service):
    link = service.shorten("https://example.com/a", expires_at=datetime(2027, 1, 1, tzinfo=UTC))
    assert service.shorten("https://example.com/a") == ShortLink(link.code, None)


def test_cleanup_deletes_only_links_expired_longer_than_the_grace_period(service, session, clock):
    service.shorten("https://example.com/old", "old-link", datetime(2026, 1, 2, tzinfo=UTC))
    service.shorten("https://example.com/recent", expires_at=datetime(2026, 1, 20, tzinfo=UTC))
    service.shorten("https://example.com/forever")
    clock.now = datetime(2026, 2, 1, tzinfo=UTC)
    assert service.delete_expired(timedelta(days=14)) == 1
    remaining = session.scalars(select(Link.long_url).order_by(Link.id)).all()
    assert remaining == ["https://example.com/recent", "https://example.com/forever"]
    assert session.query(Alias).count() == 0


def test_codes_of_deleted_links_are_not_reused(service, clock):
    code = service.shorten(
        "https://example.com/old", expires_at=datetime(2026, 1, 2, tzinfo=UTC)
    ).code
    clock.now = datetime(2026, 2, 1, tzinfo=UTC)
    service.delete_expired(timedelta(0))
    assert service.shorten("https://example.com/new").code != code


def test_expiry_beyond_the_latest_utc_time_is_rejected(service):
    expires_at = datetime(9999, 12, 31, 23, 59, tzinfo=timezone(timedelta(hours=-1)))
    with pytest.raises(InvalidExpiry):
        service.shorten("https://example.com/a", expires_at=expires_at)


def test_shortening_with_a_taken_alias_creates_no_link(service, session):
    service.shorten("https://example.com/a", alias="my-link")
    with pytest.raises(AliasTaken):
        service.shorten("https://example.com/b", alias="my-link")
    session.rollback()
    assert session.query(Link).count() == 1
