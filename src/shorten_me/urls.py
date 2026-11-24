"""Validate the long URLs that clients submit."""

import socket
from ipaddress import IPv4Address, IPv6Address, ip_address
from urllib.parse import SplitResult, urlsplit

from shorten_me.errors import InvalidInput

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})


class InvalidUrl(InvalidInput):
    """Raised when a submitted URL can't be shortened."""


def validate_long_url(url: str, own_url: str | None = None) -> None:
    """Raise `InvalidUrl` unless it is a clean, absolute http(s) URL to a public host.

    With `own_url`, the address of this service, a URL that points back at it is rejected too.
    Hostnames aren't looked up, so one that resolves to a private address is accepted.
    """
    if len(url) > MAX_URL_LENGTH:
        raise InvalidUrl(f"URL is longer than {MAX_URL_LENGTH} characters")
    if any(char.isspace() or not char.isprintable() for char in url):
        raise InvalidUrl("URL must not contain whitespace or control characters")
    parts = _split(url)
    if parts.scheme not in ALLOWED_SCHEMES:
        raise InvalidUrl("URL must start with http:// or https://")
    if not parts.hostname:
        raise InvalidUrl("URL has no host")
    if parts.username is not None or parts.password is not None:
        raise InvalidUrl("URL must not contain a username or password")
    if _is_local(parts.hostname):
        raise InvalidUrl("URL must not point to a private or local address")
    if own_url is not None and _is_under(parts, _split(own_url)):
        raise InvalidUrl("URL must not point to this service")


def _split(url: str) -> SplitResult:
    try:
        parts = urlsplit(url)
        # urlsplit only parses the port, and rejects a bad one, when it is read.
        parts.port
    except ValueError as error:
        raise InvalidUrl(str(error)) from error
    return parts


def _is_under(parts: SplitResult, base: SplitResult) -> bool:
    prefix = base.path.rstrip("/") + "/"
    return parts.hostname == base.hostname and parts.path.startswith(prefix)


def _is_local(hostname: str) -> bool:
    name = hostname.rstrip(".")
    if name == "localhost" or name.endswith(".localhost"):
        return True
    address = _ip_address(name)
    return address is not None and not address.is_global


def _ip_address(hostname: str) -> IPv4Address | IPv6Address | None:
    try:
        return ip_address(hostname)
    except ValueError:
        pass
    try:
        # Browsers also read 2130706433, 0x7f.1 and 127.1 as IPv4 addresses.
        return ip_address(socket.inet_aton(hostname))
    except OSError:
        return None
