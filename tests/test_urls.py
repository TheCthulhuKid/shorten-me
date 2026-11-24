import pytest

from shorten_me.urls import InvalidUrl, validate_long_url


def test_url_without_http_scheme_is_rejected():
    with pytest.raises(InvalidUrl):
        validate_long_url("javascript://example.com/%0Aalert(1)")


def test_url_with_whitespace_is_rejected():
    with pytest.raises(InvalidUrl):
        validate_long_url(" https://example.com/a")


def test_url_with_credentials_is_rejected():
    with pytest.raises(InvalidUrl):
        validate_long_url("https://example.com@evil.example/")


def test_url_to_a_local_address_is_rejected():
    for url in ["http://127.0.0.1/", "http://2130706433/", "http://localhost/"]:
        with pytest.raises(InvalidUrl):
            validate_long_url(url)


def test_url_to_this_service_is_rejected():
    with pytest.raises(InvalidUrl):
        validate_long_url("https://sho.rt/my-link", own_url="https://sho.rt")
