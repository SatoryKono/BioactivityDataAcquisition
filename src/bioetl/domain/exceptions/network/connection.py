"""Connection and retry network exceptions.

Covers general network connectivity failures and retry exhaustion.

All exceptions inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType

__all__ = [
    "NetworkError",
    "RetryExhaustedError",
]


class NetworkError(RecoverableError):
    """Base class for network connectivity errors.

    This is a generic network error that may be retried.
    Covers connection failures, DNS issues, and general connectivity problems.

    Attributes:
        cause: Optional underlying exception that caused the network error.

    Example:
        >>> raise NetworkError("Connection refused", cause=original_exception)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        """Initialize NetworkError.

        Args:
            message: Description of the network error.
            cause: Optional underlying exception.
        """
        self.cause = cause
        super().__init__(message)


class RetryExhaustedError(RecoverableError):
    """Raised when all retry attempts are exhausted.

    This indicates that a transient error persisted across all retry attempts.
    Further retries at the same operation are unlikely to succeed without
    external intervention.

    Attributes:
        url: URL or operation identifier that failed.
        attempts: Number of retry attempts made.
        last_error: Optional last exception from the final attempt.

    Example:
        >>> raise RetryExhaustedError(
        ...     "https://api.chembl.org/data",
        ...     attempts=3,
        ...     last_error=TimeoutError("Connection timed out")
        ... )
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self, url: str, attempts: int, last_error: Exception | None = None
    ) -> None:
        """Initialize RetryExhaustedError.

        Args:
            url: URL or operation identifier that failed.
            attempts: Number of retry attempts made.
            last_error: Optional last exception from the final attempt.
        """
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        msg = f"Exhausted {attempts} retry attempts for {url}"
        if last_error:
            error_desc = str(last_error) or type(last_error).__name__
            msg += f": {error_desc}"
        super().__init__(msg)
