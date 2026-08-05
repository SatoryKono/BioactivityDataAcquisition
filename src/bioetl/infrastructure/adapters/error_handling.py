"""Unified error classification/logging/wrapping helpers for adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import (
    ExternalServiceError,
)
from bioetl.domain.ports import ErrorClassifierPort
from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters._error_handler_ops import (
    decide_should_retry,
    decide_should_retry_status,
    log_adapter_error,
    wrap_adapter_error,
)
from bioetl.infrastructure.adapters._error_handling_support import (
    AdapterErrorContext,
    extract_retry_after,
    safe_optional_str,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import (
    AdapterErrorClassifier,
    ErrorCategory,
)
from bioetl.infrastructure.errors import (
    DomainInfraExceptionMapper,
)

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
        """Classify HTTP error status code into retryability categories."""
        _ = response
        return self._adapter_classifier.classify_http_status(status_code)

    def classify_exception(self, error: Exception) -> ErrorCategory:
        """Classify exception into error category."""
        return self._adapter_classifier.classify_exception(error)

    def get_error_type(self, error: Exception) -> ErrorType:
        """Get ErrorType for an exception."""
        return self._classifier.classify(error)

    def log_error(
        self,
        provider: str,
        operation: str,
        error: Exception,
        context: JsonDict | None = None,  # Any: untyped API JSON record
    ) -> AdapterErrorContext:
        """Log error with unified structured context."""
        return log_adapter_error(
            logger=self._logger,
            metrics=self._metrics,
            adapter_classifier=self._adapter_classifier,
            error_type=self.get_error_type(error),
            provider=provider,
            operation=operation,
            error=error,
            context=context or {},
        )

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
        """Determine if error should be retried."""
        return decide_should_retry(
            logger=self._logger,
            error_type=self.get_error_type(error),
            error=error,
        )

    def should_retry_status(self, status_code: int) -> bool:
        """Determine if HTTP status code should be retried."""
        return decide_should_retry_status(
            logger=self._logger,
            category=self.classify_http_error(status_code),
            status_code=status_code,
        )

    def get_retry_after(self, response: Response) -> float | None:
        """Extract Retry-After header value from response."""
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
        """Wrap exception in appropriate ExternalServiceError."""
        return wrap_adapter_error(
            error_mapper=self._error_mapper,
            error=error,
            error_type=self.get_error_type(error),
            provider=provider,
            status_code=status_code,
            retry_after=retry_after,
            entity=entity,
            pipeline=pipeline,
            operation=operation,
        )

    def handle_error(
        self,
        error: Exception,
        provider: str,
        operation: str,
        context: JsonDict | None = None,  # Any: untyped API JSON record
    ) -> ExternalServiceError:
        """Handle error: log and wrap in one step."""
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
