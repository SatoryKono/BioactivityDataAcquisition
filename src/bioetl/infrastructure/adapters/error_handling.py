"""Unified error handling for BioETL adapters.

Provides standardized error classification, logging, and wrapping
for all DataSourcePort adapters (RULES.md §4.1).

Error Categories (§4.1):
- CRITICAL: Auth failures (401, 403) - fail immediately
- RECOVERABLE: Rate limits (429), timeouts (5xx) - retry with backoff
- DATA_QUALITY: Validation errors - log and skip record

Retry Strategy (§4.3):
- Max retries: 3
- Backoff: exponential with base 2.0
- Jitter: 0.1-0.5s random

Log Format (§10.4.2):
Structured JSON via LoggerPort with consistent fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    CriticalError,
    ExternalServiceError,
    RateLimitExceededError,
    ServiceUnavailableError,
)
from bioetl.domain.types import ErrorType

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort


class ErrorCategory(str, Enum):
    """Error category for adapter error handling (RULES.md §4.1).

    Determines pipeline behavior:
    - CRITICAL: Fail pipeline immediately (auth failures)
    - RECOVERABLE: Retry with exponential backoff (rate limits, timeouts)
    - DATA_QUALITY: Log and skip record (validation errors)
    """

    CRITICAL = "CRITICAL"
    """Critical error - fail pipeline immediately (e.g., auth failure)."""

    RECOVERABLE = "RECOVERABLE"
    """Recoverable error - retry with backoff (e.g., rate limit, timeout)."""

    DATA_QUALITY = "DATA_QUALITY"
    """Data quality error - log and skip record (e.g., validation error)."""


# HTTP status code to error category mapping
_HTTP_STATUS_CATEGORIES: dict[int, ErrorCategory] = {
    # Authentication errors - CRITICAL
    401: ErrorCategory.CRITICAL,
    403: ErrorCategory.CRITICAL,
    # Rate limit - RECOVERABLE
    429: ErrorCategory.RECOVERABLE,
    # Server errors - RECOVERABLE
    500: ErrorCategory.RECOVERABLE,
    502: ErrorCategory.RECOVERABLE,
    503: ErrorCategory.RECOVERABLE,
    504: ErrorCategory.RECOVERABLE,
    # Client errors (except auth) - DATA_QUALITY
    400: ErrorCategory.DATA_QUALITY,
    404: ErrorCategory.DATA_QUALITY,
    422: ErrorCategory.DATA_QUALITY,
}


@dataclass
class AdapterErrorContext:
    """Context for adapter error handling.

    Contains all relevant information about the error for logging and metrics.

    Attributes:
        provider: Name of the data provider (e.g., 'chembl', 'uniprot').
        operation: Operation that failed (e.g., 'fetch', 'health_check').
        status_code: HTTP status code if applicable.
        retry_count: Number of retry attempts so far.
        circuit_breaker_state: Current circuit breaker state if available.
        error_type: Classified error type from ErrorClassifier.
        error_category: High-level error category (CRITICAL/RECOVERABLE/DATA_QUALITY).
        retry_after: Seconds to wait before retry (from Retry-After header).
    """

    provider: str
    operation: str
    status_code: int | None = None
    retry_count: int = 0
    circuit_breaker_state: str | None = None
    error_type: ErrorType | None = None
    error_category: ErrorCategory | None = None
    retry_after: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ErrorService:
    """Unified error service for all adapters.

    Provides consistent error classification, logging, and exception wrapping
    across all DataSourcePort implementations.

    Note:
        Renamed from ErrorHandler to ErrorService to align with glossary.md
        Ubiquitous Language (avoid "Handler", use "Service").

    Usage:
        >>> service = ErrorService(logger)
        >>> try:
        ...     response = await client.get(url)
        ... except httpx.HTTPStatusError as e:
        ...     category = service.classify_http_error(e.response.status_code)
        ...     service.log_error("chembl", "fetch", e, {"status_code": e.response.status_code})
        ...     raise service.wrap_error(e, "chembl")

    Attributes:
        logger: LoggerPort instance for structured logging.
        classifier: ErrorClassifier for domain error classification.
    """

    def __init__(
        self,
        logger: LoggerPort,
        classifier: ErrorClassifier | None = None,
    ) -> None:
        """Initialize ErrorService.

        Args:
            logger: LoggerPort instance for structured logging.
            classifier: Optional ErrorClassifier. Defaults to new instance.
        """
        self._logger = logger
        self._classifier = classifier or ErrorClassifier()

    def classify_http_error(
        self,
        status_code: int,
        response: Response | None = None,
    ) -> ErrorCategory:
        """Classify HTTP error by status code.

        Args:
            status_code: HTTP status code.
            response: Optional HTTP response for additional context.

        Returns:
            ErrorCategory based on status code.

        Examples:
            >>> handler.classify_http_error(401)
            ErrorCategory.CRITICAL
            >>> handler.classify_http_error(429)
            ErrorCategory.RECOVERABLE
            >>> handler.classify_http_error(400)
            ErrorCategory.DATA_QUALITY
        """
        if status_code in _HTTP_STATUS_CATEGORIES:
            return _HTTP_STATUS_CATEGORIES[status_code]

        # Default classification based on status code ranges
        if 400 <= status_code < 500:
            return ErrorCategory.DATA_QUALITY
        if status_code >= 500:
            return ErrorCategory.RECOVERABLE

        # Unknown status code - treat as recoverable
        return ErrorCategory.RECOVERABLE

    def classify_exception(self, error: Exception) -> ErrorCategory:
        """Classify exception into error category.

        Uses ErrorClassifier to determine ErrorType, then maps to ErrorCategory.

        Args:
            error: The exception to classify.

        Returns:
            ErrorCategory based on exception type.
        """
        error_type = self._classifier.classify(error)

        if error_type.is_critical():
            return ErrorCategory.CRITICAL
        if error_type.is_recoverable():
            return ErrorCategory.RECOVERABLE
        if error_type.is_data_quality():
            return ErrorCategory.DATA_QUALITY

        # Default to recoverable for unknown types
        return ErrorCategory.RECOVERABLE

    def get_error_type(self, error: Exception) -> ErrorType:
        """Get ErrorType for an exception.

        Args:
            error: The exception to classify.

        Returns:
            ErrorType from ErrorClassifier.
        """
        return self._classifier.classify(error)

    def log_error(
        self,
        provider: str,
        operation: str,
        error: Exception,
        context: dict[str, Any] | None = None,
    ) -> AdapterErrorContext:
        """Log error with unified format.

        Logs error with full context as structured JSON (RULES.md §10.4.2).

        Args:
            provider: Name of the data provider.
            operation: Operation that failed.
            error: The exception that occurred.
            context: Additional context (status_code, retry_count, etc.).

        Returns:
            AdapterErrorContext with all error details.
        """
        context = context or {}

        # Classify error
        error_type = self._classifier.classify(error)
        status_code = context.get("status_code")

        if status_code is not None:
            error_category = self.classify_http_error(status_code)
        else:
            error_category = self.classify_exception(error)

        # Build context object
        error_context = AdapterErrorContext(
            provider=provider,
            operation=operation,
            status_code=status_code,
            retry_count=context.get("retry_count", 0),
            circuit_breaker_state=context.get("circuit_breaker_state"),
            error_type=error_type,
            error_category=error_category,
            retry_after=context.get("retry_after"),
            extra={k: v for k, v in context.items()
                   if k not in {"status_code", "retry_count", "circuit_breaker_state", "retry_after"}},
        )

        # Log with unified format
        self._logger.error(
            "external_api_error",
            provider=provider,
            operation=operation,
            error_category=error_category.value,
            error_type=error_type.value,
            is_critical=error_type.is_critical(),
            is_recoverable=error_type.is_recoverable(),
            status_code=status_code,
            retry_count=error_context.retry_count,
            circuit_breaker_state=error_context.circuit_breaker_state,
            retry_after=error_context.retry_after,
            error=str(error),
            error_class=type(error).__name__,
            **error_context.extra,
        )

        return error_context

    def should_retry(self, error: Exception) -> bool:
        """Determine if error should be retried.

        Args:
            error: The exception to check.

        Returns:
            True if error is recoverable and should be retried.
        """
        error_type = self._classifier.classify(error)
        return error_type.is_recoverable()

    def should_retry_status(self, status_code: int) -> bool:
        """Determine if HTTP status code should be retried.

        Args:
            status_code: HTTP status code.

        Returns:
            True if status code indicates recoverable error.
        """
        category = self.classify_http_error(status_code)
        return category == ErrorCategory.RECOVERABLE

    def get_retry_after(self, response: Response) -> float | None:
        """Extract Retry-After header value from response.

        Args:
            response: HTTP response object.

        Returns:
            Retry-After value in seconds, or None if not present.
        """
        retry_after = response.headers.get("Retry-After")
        if retry_after is None:
            return None

        try:
            # Try parsing as integer seconds
            return float(retry_after)
        except ValueError:
            # Could be HTTP-date format, return default
            return 60.0

    def wrap_error(
        self,
        error: Exception,
        provider: str,
        status_code: int | None = None,
        retry_after: float | None = None,
    ) -> ExternalServiceError:
        """Wrap exception in appropriate ExternalServiceError.

        Translates provider-specific or HTTP errors into domain-level
        ExternalServiceError hierarchy for consistent handling.

        Args:
            error: The original exception.
            provider: Name of the data provider.
            status_code: HTTP status code if applicable.
            retry_after: Retry-After value in seconds.

        Returns:
            Appropriate ExternalServiceError subclass.

        Raises:
            CriticalError: For authentication failures (no return).
        """
        message = str(error)

        # Handle based on status code if available
        if status_code is not None:
            return self._wrap_by_status_code(
                message=message,
                provider=provider,
                status_code=status_code,
                retry_after=retry_after,
                original_error=error,
            )

        # Handle based on exception type
        error_type = self._classifier.classify(error)

        if error_type.is_critical():
            raise CriticalError(
                f"Critical {provider} error ({error_type.value}): {message}"
            ) from error

        if error_type == ErrorType.RATE_LIMIT:
            return RateLimitExceededError(
                message=message,
                service_name=provider,
                retry_after=retry_after or 60.0,
            )

        if error_type == ErrorType.TIMEOUT:
            return ServiceUnavailableError(
                message=message,
                service_name=provider,
                retry_after=retry_after,
            )

        # Default to generic ExternalServiceError
        return ExternalServiceError(
            message=message,
            service_name=provider,
            status_code=status_code,
            retry_after=retry_after,
        )

    def _wrap_by_status_code(
        self,
        message: str,
        provider: str,
        status_code: int,
        retry_after: float | None,
        original_error: Exception,
    ) -> ExternalServiceError:
        """Wrap error based on HTTP status code.

        Args:
            message: Error message.
            provider: Provider name.
            status_code: HTTP status code.
            retry_after: Retry-After value.
            original_error: Original exception.

        Returns:
            Appropriate ExternalServiceError subclass.

        Raises:
            CriticalError: For 401/403 (authentication failures).
        """
        # Authentication errors - raise CriticalError
        if status_code in (401, 403):
            raise CriticalError(
                f"{provider} authentication failed (HTTP {status_code}): {message}"
            ) from original_error

        # Rate limit
        if status_code == 429:
            return RateLimitExceededError(
                message=message,
                service_name=provider,
                retry_after=retry_after or 60.0,
            )

        # Server errors
        if status_code >= 500:
            return ServiceUnavailableError(
                message=message,
                service_name=provider,
                status_code=status_code,
                retry_after=retry_after,
            )

        # Default to generic error
        return ExternalServiceError(
            message=message,
            service_name=provider,
            status_code=status_code,
            retry_after=retry_after,
        )

    def handle_error(
        self,
        error: Exception,
        provider: str,
        operation: str,
        context: dict[str, Any] | None = None,
    ) -> ExternalServiceError:
        """Handle error: log and wrap in one step.

        Convenience method combining log_error and wrap_error.

        Args:
            error: The exception that occurred.
            provider: Name of the data provider.
            operation: Operation that failed.
            context: Additional context.

        Returns:
            Wrapped ExternalServiceError.

        Raises:
            CriticalError: For critical errors.
        """
        context = context or {}
        error_context = self.log_error(provider, operation, error, context)

        return self.wrap_error(
            error=error,
            provider=provider,
            status_code=error_context.status_code,
            retry_after=error_context.retry_after,
        )


__all__ = [
    "AdapterErrorContext",
    "ErrorCategory",
    "ErrorService",
]
