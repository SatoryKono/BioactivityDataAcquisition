"""Unified error handling for BioETL adapters.

Provides standardized error classification, logging, and wrapping
for all DataSourcePort adapters. Implements RULES.md §4.1 error categories.

Error Categories (§4.1):
- CRITICAL: Fail pipeline immediately (401, 403, auth failures)
- RECOVERABLE: Retry with exponential backoff (429, 5xx, timeouts)
- DATA_QUALITY: Log and skip record (validation errors)

Usage:
    >>> handler = AdapterErrorHandler(logger, provider="chembl")
    >>> try:
    ...     response = await http_client.get(url)
    >>> except Exception as e:
    ...     handler.handle_error(e, operation="fetch_activities")
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    AuthFailureError,
    NetworkError,
    RateLimitError,
    TimeoutError,
)
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker


class ErrorCategory(str, Enum):
    """Error category for adapter error handling (RULES.md §4.1).

    Determines pipeline behavior on error:
    - CRITICAL: Fail pipeline immediately
    - RECOVERABLE: Retry with exponential backoff
    - DATA_QUALITY: Log and skip record (quarantine)
    """

    CRITICAL = "CRITICAL"
    """Fail pipeline immediately. Examples: 401, 403, auth failures."""

    RECOVERABLE = "RECOVERABLE"
    """Retry with exponential backoff. Examples: 429, 5xx, timeouts."""

    DATA_QUALITY = "DATA_QUALITY"
    """Log and skip record. Examples: validation errors, malformed data."""


# HTTP status code to category mapping
_HTTP_STATUS_CATEGORIES: dict[int, ErrorCategory] = {
    # Authentication errors (CRITICAL)
    401: ErrorCategory.CRITICAL,
    403: ErrorCategory.CRITICAL,
    # Rate limit (RECOVERABLE)
    429: ErrorCategory.RECOVERABLE,
    # Server errors (RECOVERABLE)
    500: ErrorCategory.RECOVERABLE,
    502: ErrorCategory.RECOVERABLE,
    503: ErrorCategory.RECOVERABLE,
    504: ErrorCategory.RECOVERABLE,
}


def classify_http_status(status_code: int) -> ErrorCategory:
    """Classify HTTP status code into error category.

    Args:
        status_code: HTTP response status code.

    Returns:
        ErrorCategory based on status code.
        - 401, 403 → CRITICAL (auth failures)
        - 429 → RECOVERABLE (rate limit)
        - 5xx → RECOVERABLE (server errors)
        - 4xx (other) → DATA_QUALITY (client errors, bad requests)
    """
    if status_code in _HTTP_STATUS_CATEGORIES:
        return _HTTP_STATUS_CATEGORIES[status_code]

    # Default classification by range
    if 400 <= status_code < 500:
        return ErrorCategory.DATA_QUALITY
    if status_code >= 500:
        return ErrorCategory.RECOVERABLE

    # Success codes shouldn't be classified as errors
    return ErrorCategory.DATA_QUALITY


def extract_retry_after(response: Response) -> float | None:
    """Extract Retry-After value from response headers.

    Args:
        response: HTTP response object.

    Returns:
        Retry-After value in seconds, or None if not present.
    """
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None

    try:
        return float(retry_after)
    except ValueError:
        # Retry-After might be a date string, ignore for now
        return None


class AdapterErrorHandler:
    """Unified error handler for DataSourcePort adapters.

    Provides standardized error classification, logging, and exception wrapping.
    All adapters MUST use this handler to ensure consistent behavior.

    Attributes:
        logger: LoggerPort for structured logging.
        provider: Provider name for log context.
        error_classifier: Domain error classifier.

    Example:
        >>> handler = AdapterErrorHandler(logger, provider="chembl")
        >>> # In adapter fetch method:
        >>> try:
        ...     response = await self.http_client.get(url)
        >>> except Exception as e:
        ...     handler.handle_error(e, "fetch_activities")
    """

    def __init__(
        self,
        logger: LoggerPort,
        provider: str,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        """Initialize error handler.

        Args:
            logger: LoggerPort for structured logging.
            provider: Provider name (e.g., "chembl", "uniprot").
            circuit_breaker: Optional circuit breaker for state reporting.
        """
        self._logger = logger
        self._provider = provider
        self._circuit_breaker = circuit_breaker
        self._error_classifier = ErrorClassifier()

    @property
    def provider(self) -> str:
        """Get provider name."""
        return self._provider

    def classify_error(self, error: Exception) -> ErrorCategory:
        """Classify exception into error category.

        Uses domain ErrorClassifier to determine error type, then maps
        to ErrorCategory for adapter-level handling.

        Args:
            error: Exception to classify.

        Returns:
            ErrorCategory for the exception.
        """
        error_type = self._error_classifier.classify(error)
        return self._error_type_to_category(error_type)

    def classify_http_error(
        self, status_code: int, response: Response | None = None
    ) -> ErrorCategory:
        """Classify HTTP error by status code.

        Args:
            status_code: HTTP response status code.
            response: Optional response object for additional context.

        Returns:
            ErrorCategory based on status code.
        """
        return classify_http_status(status_code)

    def should_retry(self, error: Exception) -> bool:
        """Check if error should trigger a retry.

        Args:
            error: Exception to check.

        Returns:
            True if error is recoverable and should be retried.
        """
        category = self.classify_error(error)
        return category == ErrorCategory.RECOVERABLE

    def log_error(
        self,
        operation: str,
        error: Exception,
        *,
        status_code: int | None = None,
        retry_count: int | None = None,
        **extra_context: Any,
    ) -> None:
        """Log error with unified structured format.

        Logs error in JSON format suitable for parsing and monitoring.
        Includes provider context, error classification, and circuit breaker state.

        Args:
            operation: Operation that failed (e.g., "fetch_activities").
            error: Exception that occurred.
            status_code: Optional HTTP status code.
            retry_count: Optional retry attempt number.
            **extra_context: Additional context to include in log.
        """
        error_type = self._error_classifier.classify(error)
        category = self._error_type_to_category(error_type)

        # Build log context
        log_context: dict[str, Any] = {
            "provider": self._provider,
            "operation": operation,
            "error_category": category.value,
            "error_type": error_type.value,
            "error_message": str(error),
            "error_class": type(error).__name__,
        }

        if status_code is not None:
            log_context["status_code"] = status_code

        if retry_count is not None:
            log_context["retry_count"] = retry_count

        # Add circuit breaker state if available
        if self._circuit_breaker is not None:
            try:
                log_context["circuit_breaker_state"] = (
                    self._circuit_breaker.get_state().value
                )
                log_context["circuit_breaker_failures"] = (
                    self._circuit_breaker.get_failure_count()
                )
            except Exception:
                pass

        # Add extra context
        log_context.update(extra_context)

        # Log at appropriate level based on category
        if category == ErrorCategory.CRITICAL:
            self._logger.error("external_api_error", **log_context)
        else:
            self._logger.warning("external_api_error", **log_context)

    def wrap_error(
        self,
        error: Exception,
        operation: str,
        *,
        status_code: int | None = None,
        response: Response | None = None,
    ) -> Exception:
        """Wrap error in appropriate domain exception.

        Converts generic exceptions to domain exceptions based on classification.
        Used for consistent exception types across all adapters.

        Args:
            error: Original exception.
            operation: Operation context for error message.
            status_code: HTTP status code if available.
            response: HTTP response if available.

        Returns:
            Wrapped domain exception.
        """
        # Determine status code from response if not provided
        if status_code is None and response is not None:
            status_code = response.status_code

        # If already a domain exception, return as-is
        from bioetl.domain.exceptions import BioETLError

        if isinstance(error, BioETLError):
            return error

        # Wrap based on status code or error classification
        if status_code is not None:
            return self._wrap_http_error(error, status_code, response)

        # Classify and wrap
        category = self.classify_error(error)
        return self._wrap_by_category(error, category)

    def handle_error(
        self,
        error: Exception,
        operation: str,
        *,
        status_code: int | None = None,
        response: Response | None = None,
        retry_count: int | None = None,
        **extra_context: Any,
    ) -> NoReturn:
        """Handle error with logging and re-raise as wrapped exception.

        This is the main entry point for adapter error handling.
        Logs the error with full context, then raises wrapped exception.

        Args:
            error: Exception that occurred.
            operation: Operation that failed.
            status_code: Optional HTTP status code.
            response: Optional HTTP response.
            retry_count: Optional retry attempt number.
            **extra_context: Additional context for logging.

        Raises:
            AuthFailureError: For 401/403 errors (CRITICAL).
            RateLimitError: For 429 errors (RECOVERABLE).
            TimeoutError: For 502/504 errors (RECOVERABLE).
            NetworkError: For other server errors (RECOVERABLE).
        """
        # Determine status code
        effective_status_code = status_code
        if effective_status_code is None and response is not None:
            effective_status_code = response.status_code

        # Log the error
        self.log_error(
            operation,
            error,
            status_code=effective_status_code,
            retry_count=retry_count,
            **extra_context,
        )

        # Wrap and raise
        wrapped = self.wrap_error(
            error, operation, status_code=effective_status_code, response=response
        )
        raise wrapped from error

    def _error_type_to_category(self, error_type: ErrorType) -> ErrorCategory:
        """Map ErrorType to ErrorCategory."""
        if error_type.is_critical():
            return ErrorCategory.CRITICAL
        if error_type.is_recoverable():
            return ErrorCategory.RECOVERABLE
        return ErrorCategory.DATA_QUALITY

    def _wrap_http_error(
        self,
        error: Exception,
        status_code: int,
        response: Response | None,
    ) -> Exception:
        """Wrap HTTP error based on status code."""
        # Authentication errors (401, 403)
        if status_code in (401, 403):
            return AuthFailureError(
                provider=self._provider,
                status_code=status_code,
            )

        # Rate limit (429)
        if status_code == 429:
            retry_after = 60.0  # Default retry after
            if response is not None:
                extracted = extract_retry_after(response)
                if extracted is not None:
                    retry_after = extracted
            return RateLimitError(
                provider=self._provider,
                retry_after=retry_after,
            )

        # Gateway errors (502, 504)
        if status_code in (502, 504):
            return TimeoutError(
                f"{self._provider} gateway error: {status_code}",
                timeout_seconds=None,
            )

        # Other server errors (5xx)
        if status_code >= 500:
            return NetworkError(
                f"{self._provider} server error: {status_code}",
                cause=error,
            )

        # Client errors (4xx) - return as-is or wrap in NetworkError
        return NetworkError(
            f"{self._provider} client error: {status_code}",
            cause=error,
        )

    def _wrap_by_category(
        self, error: Exception, category: ErrorCategory
    ) -> Exception:
        """Wrap error based on category."""
        if category == ErrorCategory.CRITICAL:
            return AuthFailureError(
                provider=self._provider,
                status_code=None,
            )

        # Default to NetworkError for recoverable/unknown
        return NetworkError(
            f"{self._provider} error: {error}",
            cause=error,
        )
