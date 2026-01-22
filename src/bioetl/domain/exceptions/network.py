"""Network and external service exceptions.

These errors involve network connectivity, timeouts, and external API interactions.
Most are recoverable (transient).
"""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.types import ErrorType


class NetworkError(RecoverableError):
    """Base class for network-related errors (transient connectivity issues)."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)


class TimeoutError(NetworkError):
    """Raised when a network request times out."""

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str = "Network request timed out",
        timeout_seconds: float | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        if timeout_seconds:
            message += f" (timeout={timeout_seconds}s)"
        super().__init__(message)


class ConnectionError(NetworkError):
    """Raised when a network connection fails (host unreachable, connection reset, etc.)."""

    error_type = ErrorType.NETWORK_ERROR


class RateLimitError(NetworkError):
    """Raised when an internal API rate limit is exceeded, indicating the caller should slow down."""

    error_type = ErrorType.RATE_LIMIT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {provider}. Retry after {retry_after}s"
        )


class RetryExhaustedError(NetworkError):
    """Raised when all retry attempts for a network operation have been exhausted without success."""

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self, url: str, attempts: int, last_error: Exception | None = None
    ) -> None:
        self.url = url
        self.attempts = attempts
        self.last_error = last_error
        msg = f"Exhausted {attempts} retry attempts for {url}"
        if last_error:
            msg += f": {last_error}"
        super().__init__(msg)


class CircuitBreakerOpenError(NetworkError):
    """Raised when the circuit breaker is open, blocking requests due to repeated failures."""

    error_type = ErrorType.TIMEOUT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {provider}. Retry after {retry_after}s"
        )


class ExternalServiceError(NetworkError):
    """Base class for errors arising from external service calls.

    Adapters should translate provider-specific errors into these exceptions.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.service_name = service_name
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(message)


class ServiceUnavailableError(ExternalServiceError):
    """Raised when an external service is unavailable or returns a server error (e.g., 503 or timeout)."""

    error_type = ErrorType.TIMEOUT

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
            retry_after=retry_after,
        )


class RateLimitExceededError(ExternalServiceError):
    """Raised when an external service returns 429 Too Many Requests."""

    error_type = ErrorType.RATE_LIMIT

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        retry_after: float = 60.0,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=429,
            retry_after=retry_after,
        )


class ServiceAuthenticationError(ExternalServiceError):
    """Raised when authentication with an external service fails (e.g., invalid or expired credentials)."""

    error_type = ErrorType.AUTH_FAILURE

    def __init__(
        self,
        message: str,
        service_name: str | None = None,
        status_code: int | None = None,
    ) -> None:
        super().__init__(
            message,
            service_name=service_name,
            status_code=status_code,
        )


class ApiError(RecoverableError):
    """Raised when external API returns an error.

    Generic API error, kept for backward compatibility.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"[{status_code}] {message}"
        super().__init__(msg)
