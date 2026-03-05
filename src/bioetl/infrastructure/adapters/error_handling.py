"""Unified error classification/logging/wrapping helpers for adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    ExternalServiceError,
)
from bioetl.domain.ports import ErrorClassifierPort, NoOpMetrics
from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters.adapter_error_classifier import (
    AdapterErrorClassifier,
    ErrorCategory,
)
from bioetl.infrastructure.adapters.adapter_error_mapper import (
    AdapterErrorMapper,
    DomainErrorMappingInput,
)

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort, MetricsPort


_ERROR_CONTEXT_RESERVED_KEYS = frozenset(
    {
        "status_code",
        "retry_count",
        "circuit_breaker_state",
        "retry_after",
    }
)


@dataclass
class AdapterErrorContext:
    """Structured context carried through adapter error handling flow."""

    provider: str
    operation: str
    status_code: int | None = None
    retry_count: int = 0
    circuit_breaker_state: str | None = None
    error_type: ErrorType | None = None
    error_category: ErrorCategory | None = None
    retry_after: float | None = None
    extra: JsonDict = field(default_factory=dict)  # Any: untyped API JSON record


class ErrorService:
    """Adapter-facing service for classification, logging, and error wrapping."""

    def __init__(
        self,
        logger: LoggerPort,
        classifier: ErrorClassifierPort | None = None,
        metrics: MetricsPort | None = None,
        adapter_classifier: AdapterErrorClassifier | None = None,
        error_mapper: AdapterErrorMapper | None = None,
    ) -> None:
        """Initialize service with logging, optional classifier, and metrics."""
        self._logger = logger
        self._classifier = classifier or ErrorClassifier()
        self._adapter_classifier = adapter_classifier or AdapterErrorClassifier(
            classifier=self._classifier,
            logger=self._logger,
        )
        self._error_mapper = error_mapper or AdapterErrorMapper(logger=self._logger)
        self._metrics = metrics if metrics is not None else NoOpMetrics()

    def classify_http_error(
        self,
        status_code: int,
        response: Response | None = None,
    ) -> ErrorCategory:
        """Classify HTTP error status code into retryability categories."""
        _ = response
        return self._adapter_classifier.classify_http_status(status_code)

    def classify_exception(self, error: Exception) -> ErrorCategory:
        """Classify exception into error category.

        Uses ErrorClassifier to determine ErrorType, then maps to ErrorCategory.

        Args:
            error: The exception to classify.

        Returns:
            ErrorCategory based on exception type.
        """
        return self._adapter_classifier.classify_exception(error)

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
        context: JsonDict | None = None,  # Any: untyped API JSON record
    ) -> AdapterErrorContext:
        """Log error with unified structured context."""
        context = context or {}
        error_type = self.get_error_type(error)
        status_code = context.get("status_code")
        error_category = self._resolve_error_category(
            error=error, status_code=status_code
        )
        error_context = self._build_error_context(
            provider=provider,
            operation=operation,
            context=context,
            error_type=error_type,
            error_category=error_category,
            status_code=status_code,
        )
        self._emit_error_telemetry(
            provider=provider,
            operation=operation,
            error=error,
            error_type=error_type,
            error_category=error_category,
            error_context=error_context,
            status_code=status_code,
        )
        return error_context

    def _resolve_error_category(
        self,
        *,
        error: Exception,
        status_code: int | None,
    ) -> ErrorCategory:
        """Resolve error category from HTTP status code or exception type."""
        return self._adapter_classifier.classify(
            error=error,
            status_code=status_code,
        )

    def _build_error_context(
        self,
        *,
        provider: str,
        operation: str,
        context: JsonDict,  # Any: untyped API JSON record
        error_type: ErrorType,
        error_category: ErrorCategory,
        status_code: int | None,
    ) -> AdapterErrorContext:
        """Build strongly typed adapter error context payload."""
        return AdapterErrorContext(
            provider=provider,
            operation=operation,
            status_code=status_code,
            retry_count=context.get("retry_count", 0),
            circuit_breaker_state=context.get("circuit_breaker_state"),
            error_type=error_type,
            error_category=error_category,
            retry_after=context.get("retry_after"),
            extra={
                k: v
                for k, v in context.items()
                if k not in _ERROR_CONTEXT_RESERVED_KEYS
            },
        )

    def _emit_error_telemetry(
        self,
        *,
        provider: str,
        operation: str,
        error: Exception,
        error_type: ErrorType,
        error_category: ErrorCategory,
        error_context: AdapterErrorContext,
        status_code: int | None,
    ) -> None:
        """Emit error log and taxonomy counter in unified format."""
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
        self._metrics.increment_counter(
            "adapter_error_taxonomy_total",
            1,
            {
                "provider": provider,
                "operation": operation,
                "error_category": error_category.value,
                "error_type": error_type.value,
            },
        )

    def should_retry(self, error: Exception) -> bool:
        """Determine if error should be retried.

        Args:
            error: The exception to check.

        Returns:
            True if error is recoverable and should be retried.
        """
        error_type = self.get_error_type(error)
        should_retry = error_type.is_recoverable()
        self._logger.debug(
            "retry_decision",
            error_type=error_type.value,
            error_class=type(error).__name__,
            should_retry=should_retry,
            decision_source="exception_type",
        )
        return should_retry

    def should_retry_status(self, status_code: int) -> bool:
        """Determine if HTTP status code should be retried.

        Args:
            status_code: HTTP status code.

        Returns:
            True if status code indicates recoverable error.
        """
        category = self.classify_http_error(status_code)
        should_retry = category == ErrorCategory.RECOVERABLE
        self._logger.debug(
            "retry_decision",
            status_code=status_code,
            category=category.value,
            should_retry=should_retry,
            decision_source="http_status",
        )
        return should_retry

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
        """Wrap exception in appropriate ExternalServiceError."""
        error_type = self.get_error_type(error)
        return self._error_mapper.map_to_domain_error(
            DomainErrorMappingInput(
                error=error,
                provider=provider,
                error_type=error_type,
                status_code=status_code,
                retry_after=retry_after,
            )
        )

    def handle_error(
        self,
        error: Exception,
        provider: str,
        operation: str,
        context: JsonDict | None = None,  # Any: untyped API JSON record
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
