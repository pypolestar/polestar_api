class PolestarApiException(Exception):
    """Base class for exceptions in this module."""


class PolestarAuthException(Exception):
    """Base class for exceptions in Auth module."""

    error_code: int = None
    message: str = None

    def __init__(self, message, error_code) -> None:
        super().__init__(message)
        self.error_code = error_code


class PolestarNotAuthorizedException(Exception):
    """Exception for unauthorized call."""


class PolestarNoDataException(Exception):
    """Exception for no data."""
