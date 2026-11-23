import pytest

from shorten_me.urls import InvalidUrl, validate_long_url


def test_url_without_http_scheme_is_rejected():
    with pytest.raises(InvalidUrl):
        validate_long_url("javascript://example.com/%0Aalert(1)")
