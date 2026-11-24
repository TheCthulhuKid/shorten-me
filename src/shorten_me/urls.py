"""Validate the long URLs that clients submit."""

from urllib.parse import urlsplit

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})


class InvalidUrl(ValueError):
    """Raised when a submitted URL can't be shortened."""


def validate_long_url(url: str) -> str:
    """Return the URL unchanged if it is a clean, absolute http(s) URL within the length limit."""
    if len(url) > MAX_URL_LENGTH:
        raise InvalidUrl(f"URL is longer than {MAX_URL_LENGTH} characters")
    if any(char.isspace() or not char.isprintable() for char in url):
        raise InvalidUrl("URL must not contain whitespace or control characters")
    try:
        parts = urlsplit(url)
        # urlsplit only parses the port, and rejects a bad one, when it is read.
        parts.port
    except ValueError as error:
        raise InvalidUrl(str(error)) from error
    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrl("URL must start with http:// or https://")
    if not parts.hostname:
        raise InvalidUrl("URL has no host")
    return url
