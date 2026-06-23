"""Unified error classification/logging/wrapping helpers for adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    ExternalServiceError,
)
from bioetl.domain.ports import ErrorClassifierPort
from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters._error_handling_support import (
    AdapterErrorContext,
    build_adapter_error_context,
    emit_error_telemetry,
    extract_retry_after,
    safe_optional_str,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import (
    AdapterErrorClassifier,
    ErrorCategory,
)
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)
from bioetl.infrastructure.errors.exception_mapper import InfrastructureSourceError

if TYPE_CHECKING:
    from httpx import Response

    from bioetl.domain.ports import LoggerPort, MetricsPort


class AdapterErrorHandler:
    """Adapter-facing helper for classification, logging, and error wrapping."""

    def __init__(
        self,
        logger: LoggerPort,
        classifier: ErrorClassifierPort | None = None,
        metrics: MetricsPort | None = None,
        adapter_classifier: AdapterErrorClassifier | None = None,
        error_mapper: DomainInfraExceptionMapper | None = None,
    ) -> None:
        """Initialize handler with logging, optional classifier, and metrics."""
        self._logger = logger
        self._classifier = classifier or ErrorClassifier()
        self._adapter_classifier = adapter_classifier or AdapterErrorClassifier(
            classifier=self._classifier,
            logger=self._logger,
        )
        self._error_mapper = error_mapper or DomainInfraExceptionMapper(
            logger=self._logger
        )
        self._metrics = metrics

    def classify_http_error(
        self,
        status_code: int,
        response: Response | None = None,
    ) -> ErrorCategory:
        """Classify HTTP error status code into retryability categories.

        Returns:
            ErrorCategory indicating whether the HTTP error is critical, recoverable, or a data quality issue.
        """
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
        """Log error with unified structured context.

        Returns:
            AdapterErrorContext with classified error details and telemetry data.
        """
        context = context or {}
        error_type = self.get_error_type(error)
        status_code = context.get("status_code")
        error_category = self._resolve_error_category(
            error=error, status_code=status_code
        )
        error_context = build_adapter_error_context(
            provider=provider,
            operation=operation,
            context=context,
            error_type=error_type,
            error_category=error_category,
            status_code=status_code,
        )
        emit_error_telemetry(
            logger=self._logger,
            metrics=self._metrics,
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
        return bool(should_retry)

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
        return bool(should_retry)

    def get_retry_after(self, response: Response) -> float | None:
        """Extract Retry-After header value from response.

        Args:
            response: HTTP response object.

        Returns:
            Retry-After value in seconds, or None if not present.
        """
        retry_after = extract_retry_after(response)
        if retry_after is None:
            return None
        return float(retry_after)

    def wrap_error(
        self,
        error: Exception,
        provider: str,
        status_code: int | None = None,
        retry_after: float | None = None,
        entity: str | None = None,
        pipeline: str | None = None,
        operation: str | None = None,
    ) -> ExternalServiceError:
        """Wrap exception in appropriate ExternalServiceError.

        Returns:
            ExternalServiceError wrapping the original exception with provider context.
        """
        error_type = self.get_error_type(error)
        return self._error_mapper.map_to_domain_error(
            DomainErrorMappingInput(
                error=cast(InfrastructureSourceError, error),
                provider=provider,
                error_type=error_type,
                status_code=status_code,
                retry_after=retry_after,
                entity=entity,
                pipeline=pipeline,
                operation=operation,
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
            entity=safe_optional_str(context.get("entity")),
            pipeline=safe_optional_str(context.get("pipeline")),
            operation=operation,
        )


__all__ = [
    "AdapterErrorContext",
    "AdapterErrorHandler",
    "ErrorCategory",
]
