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


class ZPLUpgradeRequiredError(ZPLError):
    """Raised when this SDK build is below the engine's configured floor (426).

    The engine returns HTTP 426 Upgrade Required with a structured body
    carrying ``upgrade_command``, ``minimum_version`` and ``current_version``
    when ``ZPL_MIN_VERSION_SDK_PYTHON`` is set above the version reported
    in the ``X-ZPL-Client-Version`` header.

    Unlike the CLI / MCP shims, the SDK is just a library imported into
    someone else's code — it can't reinstall itself. We surface the
    upgrade metadata as instance fields so caller code can either catch
    and prompt the user to bump the dependency, or fail loudly.
    """

    def __init__(
        self,
        message: str,
        upgrade_command: str | None = None,
        minimum_version: str | None = None,
        current_version: str | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.upgrade_command = upgrade_command
        self.minimum_version = minimum_version
        self.current_version = current_version
