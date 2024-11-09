"""Exceptions for Polestar API."""


class PolestarApiException(Exception):
    """Base class for exceptions in this module."""


class PolestarAuthException(Exception):
    """Base class for exceptions in Auth module."""

    error_code: int | None = None
    message: str | None = None

    def __init__(self, message: str, error_code: int | None = None) -> None:
        """Initialize the Polestar API."""
        super().__init__(message)
        self.error_code = error_code


class PolestarNotAuthorizedException(Exception):
    """Exception for unauthorized call."""


class PolestarNoDataException(Exception):
    """Exception for no data."""
