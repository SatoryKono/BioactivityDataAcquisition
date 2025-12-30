"""CrossRef-specific exceptions.

These exceptions are internal to the CrossRef adapter and should be
translated to domain-level ExternalServiceError on adapter boundary.

Application layer should catch ExternalServiceError, not these exceptions.
"""

from __future__ import annotations

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType


class CrossRefApiError(ExternalServiceError):
    """CrossRef API error.

    Internal exception for CrossRef adapter. On adapter boundary, this
    should be translated to domain ExternalServiceError or its subclasses.

    Note:
        This is the canonical location for CrossRefApiError.
        The version in domain.exceptions is deprecated.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        doi: str | None = None,
        operation: str | None = None,
    ) -> None:
        """Initialize CrossRefApiError.

        Args:
            message: Error description.
            status_code: HTTP status code if applicable.
            doi: DOI being fetched if applicable.
            operation: Operation that failed (e.g., "fetch", "search").
        """
        self.doi = doi
        self.operation = operation
        super().__init__(
            message,
            service_name="crossref",
            status_code=status_code,
        )


class CrossRefRateLimitError(CrossRefApiError):
    """CrossRef rate limit exceeded.

    Raised when CrossRef API returns 429 Too Many Requests.

    Note:
        CrossRef provides higher rate limits (50 req/sec) when using
        the "polite pool" with a mailto parameter.
    """

    error_type = ErrorType.RATE_LIMIT

    def __init__(self, retry_after: float = 60.0) -> None:
        """Initialize CrossRefRateLimitError.

        Args:
            retry_after: Seconds to wait before retry.
        """
        super().__init__(
            f"CrossRef rate limit exceeded. Retry after {retry_after}s",
            status_code=429,
        )
        self.retry_after = retry_after


class CrossRefServiceUnavailableError(CrossRefApiError):
    """CrossRef service unavailable.

    Raised when CrossRef API returns 5xx errors or connection fails.
    """

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str = "CrossRef service unavailable",
        status_code: int | None = None,
    ) -> None:
        """Initialize CrossRefServiceUnavailableError.

        Args:
            message: Error description.
            status_code: HTTP status code (typically 5xx).
        """
        super().__init__(message, status_code=status_code)


class CrossRefNotFoundError(CrossRefApiError):
    """CrossRef resource not found.

    Raised when a DOI is not found in CrossRef (404).
    This is typically not an error - just indicates the DOI
    is not registered with CrossRef.
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(self, doi: str) -> None:
        """Initialize CrossRefNotFoundError.

        Args:
            doi: The DOI that was not found.
        """
        super().__init__(
            f"DOI not found in CrossRef: {doi}",
            status_code=404,
            doi=doi,
        )


__all__ = [
    "CrossRefApiError",
    "CrossRefNotFoundError",
    "CrossRefRateLimitError",
    "CrossRefServiceUnavailableError",
]
