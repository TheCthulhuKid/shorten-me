"""Convert between link ids and short codes.

The alphabet leaves out ambiguous characters (0, 1, I, l, o, O) and is shuffled so that
consecutive ids don't produce visibly consecutive codes.
"""

ALPHABET = "DpYvf5uRng8kKAbrZXUH23cPdhzqam9xQB4ywjGEVtWiFMTJCse6LS7N"
BASE = len(ALPHABET)
MAX_LINK_ID = 2**63 - 1
_DIGITS = {char: value for value, char in enumerate(ALPHABET)}


class InvalidShortCode(ValueError):
    """Raised when a string is not a short code that `encode` could have produced."""


def encode(link_id: int) -> str:
    """Return the short code for a link id between 1 and `MAX_LINK_ID`."""
    if link_id < 1 or link_id > MAX_LINK_ID:
        raise ValueError(f"link id must be between 1 and {MAX_LINK_ID}, got {link_id}")
    code = ""
    while link_id:
        link_id, digit = divmod(link_id, BASE)
        code = ALPHABET[digit] + code
    return code


def decode(code: str) -> int:
    """Return the link id for a short code, rejecting codes `encode` never produces."""
    if not code or code[0] == ALPHABET[0]:
        raise InvalidShortCode(code)
    link_id = 0
    for char in code:
        if char not in _DIGITS:
            raise InvalidShortCode(code)
        link_id = link_id * BASE + _DIGITS[char]
        if link_id > MAX_LINK_ID:
            raise InvalidShortCode(code)
    return link_id
