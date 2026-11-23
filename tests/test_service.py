from datetime import datetime

from shorten_me.models import Link


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
