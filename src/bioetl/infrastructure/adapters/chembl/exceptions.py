"""ChEMBL-specific exceptions.

These exceptions are internal to the ChEMBL adapter and should be
translated to domain-level ExternalServiceError on adapter boundary.

Application layer should catch ExternalServiceError, not these exceptions.
"""

from __future__ import annotations

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType


class ChemblApiError(ExternalServiceError):
    """ChEMBL API error.

    Internal exception for ChEMBL adapter. On adapter boundary, this
    should be translated to domain ExternalServiceError or its subclasses.

    Note:
        This is the canonical location for ChemblApiError.
        The version in domain.exceptions is deprecated.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        entity_type: str | None = None,
        operation: str | None = None,
    ) -> None:
        """Initialize ChemblApiError.

        Args:
            message: Error description.
            status_code: HTTP status code if applicable.
            entity_type: Type of entity being fetched (e.g., "activity").
            operation: Operation that failed (e.g., "fetch", "health_check").
        """
        self.entity_type = entity_type
        self.operation = operation
        super().__init__(
            message,
            service_name="chembl",
            status_code=status_code,
        )


class ChemblRateLimitError(ChemblApiError):
    """ChEMBL rate limit exceeded.

    Raised when ChEMBL API returns 429 Too Many Requests.
    """

    error_type = ErrorType.RATE_LIMIT

    def __init__(self, retry_after: float = 60.0) -> None:
        """Initialize ChemblRateLimitError.

        Args:
            retry_after: Seconds to wait before retry.
        """
        super().__init__(
            f"ChEMBL rate limit exceeded. Retry after {retry_after}s",
            status_code=429,
        )
        self.retry_after = retry_after


class ChemblServiceUnavailableError(ChemblApiError):
    """ChEMBL service unavailable.

    Raised when ChEMBL API returns 5xx errors or connection fails.
    """

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str = "ChEMBL service unavailable",
        status_code: int | None = None,
    ) -> None:
        """Initialize ChemblServiceUnavailableError.

        Args:
            message: Error description.
            status_code: HTTP status code (typically 5xx).
        """
        super().__init__(message, status_code=status_code)


class ChemblAuthError(ChemblApiError):
    """ChEMBL authentication error.

    Raised when ChEMBL API returns 401 or 403.
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(self, status_code: int = 401) -> None:
        """Initialize ChemblAuthError.

        Args:
            status_code: HTTP status code (401 or 403).
        """
        super().__init__(
            f"ChEMBL authentication failed (HTTP {status_code})",
            status_code=status_code,
        )


__all__ = [
    "ChemblApiError",
    "ChemblAuthError",
    "ChemblRateLimitError",
    "ChemblServiceUnavailableError",
]
