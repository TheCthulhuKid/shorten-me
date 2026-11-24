import pytest

from shorten_me.ratelimit import RateLimited, RateLimiter, client_key


def test_requests_over_the_limit_are_refused():
    limiter = RateLimiter(2, period=60, clock=lambda: 0.0)
    limiter.take("client")
    limiter.take("client")
    with pytest.raises(RateLimited) as refused:
        limiter.take("client")
    assert refused.value.retry_after == 30
    limiter.take("other client")


def test_limit_allows_requests_again_after_waiting():
    now = 0.0
    limiter = RateLimiter(1, period=60, clock=lambda: now)
    limiter.take("client")
    now = 60.0
    limiter.take("client")


def test_ipv6_clients_in_the_same_network_share_a_limit():
    assert client_key("2001:db8:1:2::1") == client_key("2001:db8:1:2:ffff::9")
    assert client_key("2001:db8:1:2::1") != client_key("2001:db8:1:3::1")
