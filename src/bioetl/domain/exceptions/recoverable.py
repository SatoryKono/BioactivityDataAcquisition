"""Recoverable exceptions that can be retried.

These errors are typically transient and may succeed on retry.
Examples: network timeouts, rate limits, temporary service unavailability.
"""

from __future__ import annotations

import warnings

from bioetl.domain.exceptions.base import RecoverableError
from bioetl.domain.exceptions.external_service import ExternalServiceError
from bioetl.domain.types import ErrorType


class RateLimitError(RecoverableError):
    """Raised when API rate limit is exceeded.

    The request should be retried after the specified delay.
    """

    error_type = ErrorType.RATE_LIMIT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Rate limit exceeded for {provider}. Retry after {retry_after}s"
        )


class RetryExhaustedError(RecoverableError):
    """Raised when all retry attempts are exhausted.

    This indicates that a transient error persisted across all retry attempts.
    """

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


class CircuitBreakerOpenError(RecoverableError):
    """Raised when circuit breaker is open and blocking requests.

    This indicates that the service has failed repeatedly and the circuit breaker
    has opened to prevent further requests.
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker open for {provider}. Retry after {retry_after}s"
        )


class ApiError(RecoverableError):
    """Raised when external API returns an error.

    This is a generic API error that may be retryable depending on the status code.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        msg = message
        if status_code:
            msg = f"[{status_code}] {message}"
        super().__init__(msg)


class ChemblApiError(ExternalServiceError):
    """Raised when ChEMBL API returns an error.

    .. deprecated::
        Use infrastructure.adapters.chembl.exceptions.ChemblApiError instead.
        This class remains for backward compatibility and will emit a
        DeprecationWarning when instantiated.

        Application layer should catch ExternalServiceError instead.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize ChemblApiError with deprecation warning.

        Args:
            message: Error message.
            status_code: Optional HTTP status code.
        """
        warnings.warn(
            "ChemblApiError in domain.exceptions is deprecated. "
            "Use infrastructure.adapters.chembl.exceptions.ChemblApiError "
            "or catch ExternalServiceError instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(message, service_name="chembl", status_code=status_code)


class CrossRefApiError(ExternalServiceError):
    """Raised when CrossRef API returns an error.

    .. deprecated::
        Use infrastructure.adapters.crossref.exceptions.CrossRefApiError instead.
        This class remains for backward compatibility and will emit a
        DeprecationWarning when instantiated.

        Application layer should catch ExternalServiceError instead.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize CrossRefApiError with deprecation warning.

        Args:
            message: Error message.
            status_code: Optional HTTP status code.
        """
        warnings.warn(
            "CrossRefApiError in domain.exceptions is deprecated. "
            "Use infrastructure.adapters.crossref.exceptions.CrossRefApiError "
            "or catch ExternalServiceError instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(message, service_name="crossref", status_code=status_code)


class TimeoutError(RecoverableError):
    """Raised when request times out (502, 504, gateway errors).

    The request may be retried after a delay.
    """

    error_type = ErrorType.TIMEOUT

    def __init__(self, message: str, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds
        msg = message
        if timeout_seconds:
            msg += f" (timeout: {timeout_seconds}s)"
        super().__init__(msg)


class NetworkError(RecoverableError):
    """Raised when network connectivity issues occur.

    This is a generic network error that may be retried.
    """

    error_type = ErrorType.NETWORK_ERROR

    def __init__(self, message: str, cause: Exception | None = None) -> None:
        self.cause = cause
        super().__init__(message)
