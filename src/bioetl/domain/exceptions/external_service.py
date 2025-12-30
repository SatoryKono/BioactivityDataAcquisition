"""External service exceptions for BioETL.

Provides abstract exception hierarchy for errors from external data sources.
Domain layer uses these abstract exceptions without knowing specific providers.

This module follows RULES.md §7.2 - Domain should be independent from implementations.
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType


class ExternalServiceError(RecoverableError):
    """Base exception for all external service errors.

    This is the abstract exception that domain/application layers should catch
    when handling errors from external data sources.

    Infrastructure adapters MUST translate provider-specific errors into this
    hierarchy on the adapter boundary.

    Attributes:
        service_name: Optional name of the service that failed.
        status_code: Optional HTTP status code if applicable.
        retry_after: Optional seconds to wait before retry.

    Example:
        >>> try:
        ...     await adapter.fetch("entity")
        ... except ExternalServiceError as e:
        ...     logger.error("External service failed", service=e.service_name)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize ExternalServiceError.

        Args:
            message: Error description.
            service_name: Name of the external service (e.g., "chembl", "crossref").
            status_code: HTTP status code if applicable.
            retry_after: Seconds to wait before retry if applicable.
        """
        self.service_name = service_name
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class ServiceUnavailableError(ExternalServiceError):
    """Raised when external service is unavailable.

    Typically caused by:
    - HTTP 5xx errors (500, 502, 503, 504)
    - Connection timeouts
    - DNS resolution failures

    The request may be retried after exponential backoff.
    """

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        """Initialize ServiceUnavailableError.

        Args:
            message: Error description.
            service_name: Name of the unavailable service.
            status_code: HTTP status code (typically 5xx).
            retry_after: Seconds to wait before retry.
        """
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            retry_after=retry_after,
        )


class RateLimitExceededError(ExternalServiceError):
    """Raised when external service rate limit is exceeded.

    Caused by HTTP 429 Too Many Requests.
    The request MUST be retried after the specified delay.

    Note:
        This is distinct from domain.exceptions.RateLimitError which is
        for internal rate limiting. This exception is for rate limits
        imposed by external services.
    """

    error_type = ErrorType.RATE_LIMIT

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        retry_after: float = 60.0,
    ) -> None:
        """Initialize RateLimitExceededError.

        Args:
            message: Error description.
            service_name: Name of the service imposing rate limit.
            retry_after: Seconds to wait before retry (from Retry-After header).
        """
        super().__init__(
            message,
            service_name=service_name,
            status_code=429,
            retry_after=retry_after,
        )


class ServiceAuthenticationError(ExternalServiceError):
    """Raised when external service authentication fails.

    Caused by HTTP 401 Unauthorized or 403 Forbidden.

    Note:
        This is a RECOVERABLE error in the external service hierarchy
        because it may be caused by expired tokens that can be refreshed.
        For truly critical auth failures, see domain.exceptions.AuthFailureError.
    """

    error_type = ErrorType.AUTH_FAILURE

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Initialize ServiceAuthenticationError.

        Args:
            message: Error description.
            service_name: Name of the service that rejected auth.
            status_code: HTTP status code (401 or 403).
        """
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
        )


class DataValidationError(ExternalServiceError):
    """Raised when external service returns invalid data.

    Used when data from an external source fails validation but the
    service itself is healthy. This is distinct from DataQualityError
    which is for internal data quality issues.

    Examples:
        - Invalid JSON response
        - Missing required fields in response
        - Unexpected data format
    """

    error_type = ErrorType.INVALID_DATA

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        field: str | None = None,
        value: str | None = None,
    ) -> None:
        """Initialize DataValidationError.

        Args:
            message: Error description.
            service_name: Name of the service that returned invalid data.
            field: Name of the invalid field if applicable.
            value: The invalid value if safe to log.
        """
        self.field = field
        self.value = value
        super().__init__(message, service_name=service_name)
