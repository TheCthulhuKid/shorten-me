"""Errors shared by the modules that validate what clients submit."""


class InvalidInput(ValueError):
    """Raised when a value a client submitted can't be accepted."""
