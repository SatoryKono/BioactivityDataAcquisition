"""Network exceptions for connectivity and external service errors.

These errors are typically transient and may succeed on retry. They cover:
- Network connectivity issues (timeouts, connection errors)
- Rate limiting from external services
- Circuit breaker protection
- External API errors

Category: NetworkErrors - network communication and external service errors
(connection issues, timeouts, rate limit exceedances, circuit breaker opening,
and retry exhaustion).

All exceptions in this module inherit from RecoverableError, indicating that
retry with exponential backoff is appropriate (per RULES.md §3.1.3).
"""

from __future__ import annotations

from typing import Any, cast

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType

__all__ = [
    "ApiError",
    "CircuitBreakerOpenError",
    "DataValidationError",
    "ExternalServiceError",
    "NetworkError",
    "RateLimitError",
    "RateLimitExceededError",
    "RetryExhaustedError",
    "ServiceAuthenticationError",
    "ServiceUnavailableError",
    "TimeoutError",
]


# =============================================================================
# Base Network Exceptions
# =============================================================================


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


class TimeoutError(RecoverableError):
    """Raised when request times out (502, 504, gateway errors).

    The request may be retried after a delay with exponential backoff.

    Attributes:
        timeout_seconds: Optional timeout duration that was exceeded.

    Example:
        >>> raise TimeoutError("Request to ChEMBL API timed out", timeout_seconds=30.0)
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, message: str, timeout_seconds: float | None = None) -> None:
        """Initialize TimeoutError.

        Args:
            message: Description of the timeout.
            timeout_seconds: Optional timeout duration that was exceeded.
        """
        self.timeout_seconds = timeout_seconds
        msg = message
        if timeout_seconds:
            msg += f" (timeout: {timeout_seconds}s)"
        super().__init__(msg)


class CircuitBreakerOpenError(RecoverableError):
    """Raised when circuit breaker is open and blocking requests.

    This indicates that the service has failed repeatedly and the circuit breaker
    has opened to prevent further requests. See ADR-007 for circuit breaker details.

    Attributes:
        provider: Name of the provider whose circuit breaker is open.
        retry_after: Seconds to wait before circuit breaker may close.

    Example:
        >>> raise CircuitBreakerOpenError("pubchem", retry_after=300.0)
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, provider: str, retry_after: float) -> None:
        """Initialize CircuitBreakerOpenError.

        Args:
            provider: Name of the provider whose circuit breaker is open.
            retry_after: Seconds to wait before circuit breaker may close.
        """
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {provider}. Retry after {retry_after}s"
        )


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
            msg += f": {last_error}"
        super().__init__(msg)


class ApiError(RecoverableError):
    """Raised when external API returns an error.

    This is a generic API error that may be retryable depending on the status code.
    For more specific external service errors, see ExternalServiceError hierarchy.

    Attributes:
        message: Error message from the API.
        status_code: Optional HTTP status code.

    Example:
        >>> raise ApiError("Invalid request parameters", status_code=400)
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize ApiError.

        Args:
            message: Error message from the API.
            status_code: Optional HTTP status code.
        """
        self.message = message
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"[{status_code}] {message}"
        super().__init__(msg)


# =============================================================================
# External Service Exceptions (RULES.md §7.2)
# =============================================================================
#
# These exceptions provide abstract error types for external data sources.
# Domain/application layers should catch these abstract exceptions, not
# provider-specific ones. Infrastructure adapters MUST translate provider-specific
# errors into this hierarchy at the adapter boundary.


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

    Example:
        >>> raise ServiceUnavailableError(
        ...     "ChEMBL API returned 503",
        ...     service_name="chembl",
        ...     status_code=503,
        ...     retry_after=60.0
        ... )
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


class RateLimitError(ExternalServiceError):
    """Raised when provider-side rate limit is exceeded."""

    error_type = ErrorType.RATE_LIMIT

    def __init__(
        self,
        provider: str | None = None,
        retry_after: float = 60.0,
        *,
        message: str | None = None,
        service_name: str | None = None,
    ) -> None:
        """Initialize unified RateLimitError."""
        if message is None and service_name is None:
            if provider is None:
                raise ValueError("provider is required for RateLimitError")
            self.provider = provider
            self.retry_after = retry_after
            RecoverableError.__init__(
                self,
                f"Rate limit exceeded for {provider}. Retry after {retry_after}s",
            )
            return

        resolved_service = service_name if service_name is not None else provider
        resolved_message = (
            message
            if message is not None
            else (provider if provider is not None else "Rate limit exceeded")
        )
        provider_name = resolved_service if resolved_service is not None else "unknown"
        self.provider = provider_name
        super().__init__(
            resolved_message,
            service_name=resolved_service,
            status_code=429,
            retry_after=retry_after,
        )


RateLimitExceededError = RateLimitError


class ServiceAuthenticationError(ExternalServiceError):
    """Raised when external service authentication fails.

    Caused by HTTP 401 Unauthorized or 403 Forbidden.

    Note:
        This is a RECOVERABLE error in the external service hierarchy
        because it may be caused by expired tokens that can be refreshed.
        For truly critical auth failures, see AuthFailureError in internal module.

    Example:
        >>> raise ServiceAuthenticationError(
        ...     "UniProt API key expired",
        ...     service_name="uniprot",
        ...     status_code=401
        ... )
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


def DataValidationError(
    message: str,
    service_name: str | None = None,
    field: str | None = None,
    value: str | None = None,
) -> ExternalServiceError:
    """Compatibility constructor for legacy DataValidationError."""
    error = ExternalServiceError(message, service_name=service_name)
    error = cast(
        ExternalServiceError,
        error.with_context(
            field=field,
            value=value,
        ),
    )
    cast(Any, error).error_type = ErrorType.INVALID_DATA
    return error
