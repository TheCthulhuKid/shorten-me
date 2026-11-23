"""Validate the long URLs that clients submit."""

from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})


class InvalidUrl(ValueError):
    """Raised when a submitted URL can't be shortened."""


def validate_long_url(url: str) -> str:
    """Return the URL unchanged if it is an absolute http(s) URL within the length limit."""
    if len(url) > MAX_URL_LENGTH:
        raise InvalidUrl(f"URL is longer than {MAX_URL_LENGTH} characters")
    try:
        parts = urlsplit(url)
    except ValueError as error:
        raise InvalidUrl(str(error)) from error
    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrl("URL must start with http:// or https://")
    if not parts.hostname:
        raise InvalidUrl("URL has no host")
    return url
