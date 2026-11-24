"""Validate the custom aliases that clients choose for their links."""

import re

from shorten_me.codec import is_code
from shorten_me.errors import InvalidInput

MAX_ALIAS_LENGTH = 32
ALIAS_PATTERN = re.compile(rf"[A-Za-z0-9_-]{{3,{MAX_ALIAS_LENGTH}}}")
# FastAPI serves these paths itself, so an alias with these names could never be followed.
RESERVED_ALIASES = frozenset({"docs", "redoc"})


class InvalidAlias(InvalidInput):
    """Raised when a string can't be used as a custom alias."""


def validate_alias(alias: str) -> None:
    """Raise `InvalidAlias` unless the alias is well formed and can never be a generated code."""
    if not ALIAS_PATTERN.fullmatch(alias):
        raise InvalidAlias(f"alias must be 3 to {MAX_ALIAS_LENGTH} letters, digits, - or _")
    if alias in RESERVED_ALIASES:
        raise InvalidAlias(f"alias {alias!r} is reserved")
    if is_code(alias):
        raise InvalidAlias(
            "alias could clash with a generated code; add a -, _ or one of 0 1 I l o O"
        )
