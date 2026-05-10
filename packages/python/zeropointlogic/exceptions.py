"""Exception classes for ZPL Engine SDK."""


class ZPLError(Exception):
    """Base exception for all ZPL SDK errors."""

    def __init__(self, message: str, status_code: int | None = None, response_data: dict | None = None):
        """
        Initialize ZPL error.

        Args:
            message: Error message
            status_code: HTTP status code if applicable
            response_data: Full response data from server
        """
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.status_code:
            return f"{self.message} (HTTP {self.status_code})"
        return self.message


class ZPLAuthError(ZPLError):
    """Raised when authentication fails (401 Unauthorized)."""

    pass


class ZPLQuotaError(ZPLError):
    """Raised when API quota is exceeded (402 Payment Required)."""

    def __init__(self, message: str, tokens_remaining: int = 0, **kwargs):
        """
        Initialize quota error.

        Args:
            message: Error message
            tokens_remaining: Number of tokens remaining
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.tokens_remaining = tokens_remaining


class ZPLRateLimitError(ZPLError):
    """Raised when rate limit is exceeded (429 Too Many Requests)."""

    def __init__(self, message: str, retry_after: int | None = None, **kwargs):
        """
        Initialize rate limit error.

        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class ZPLValidationError(ZPLError):
    """Raised when input validation fails (400 Bad Request)."""

    def __init__(self, message: str, field: str | None = None, **kwargs):
        """
        Initialize validation error.

        Args:
            message: Error message
            field: Field that failed validation
            **kwargs: Additional arguments for base class
        """
        super().__init__(message, **kwargs)
        self.field = field


class ZPLNetworkError(ZPLError):
    """Raised when network/connection errors occur."""

    pass
