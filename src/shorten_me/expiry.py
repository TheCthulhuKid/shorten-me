"""Validate the expiry times that clients choose for their links."""

from datetime import UTC, datetime

from shorten_me.errors import InvalidInput


class InvalidExpiry(InvalidInput):
    """Raised when a requested expiry has no timezone, is out of range or isn't in the future."""


def expiry_in_utc(expires_at: datetime, now: datetime) -> datetime:
    """Return the expiry converted to UTC, if it has a timezone and is later than `now`."""
    if expires_at.tzinfo is None:
        raise InvalidExpiry("expiry must include a timezone")
    try:
        expires_at = expires_at.astimezone(UTC)
    except OverflowError as error:
        raise InvalidExpiry("expiry is out of range") from error
    if expires_at <= now:
        raise InvalidExpiry("expiry must be in the future")
    return expires_at
