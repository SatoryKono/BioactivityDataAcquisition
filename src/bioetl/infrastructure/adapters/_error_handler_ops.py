"""Retry-decision, logging, and wrap helpers for AdapterErrorHandler."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters._error_handling_support import (
    AdapterErrorContext,
    build_adapter_error_context,
    emit_error_telemetry,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import ErrorCategory
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)
from bioetl.infrastructure.errors.exception_mapper import InfrastructureSourceError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.adapter_error_classifier import (
        AdapterErrorClassifier,
    )

__all__ = [
    "decide_should_retry",
    "decide_should_retry_status",
    "log_adapter_error",
    "wrap_adapter_error",
]


def log_adapter_error(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    adapter_classifier: AdapterErrorClassifier,
    error_type: ErrorType,
    provider: str,
    operation: str,
    error: Exception,
    context: JsonDict,
) -> AdapterErrorContext:
    """Log error with unified structured context and return error context."""
    status_code = context.get("status_code")
    error_category = adapter_classifier.classify(
        error=error,
        status_code=status_code,
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
        logger=logger,
        metrics=metrics,
        provider=provider,
        operation=operation,
        error=error,
        error_type=error_type,
        error_category=error_category,
        error_context=error_context,
        status_code=status_code,
    )
    return error_context


def decide_should_retry(
    *,
    logger: LoggerPort,
    error_type: ErrorType,
    error: Exception,
) -> bool:
    """Determine if error should be retried from exception taxonomy."""
    should_retry = error_type.is_recoverable()
    logger.debug(
        "retry_decision",
        error_type=error_type.value,
        error_class=type(error).__name__,
        should_retry=should_retry,
        decision_source="exception_type",
    )
    return bool(should_retry)


def decide_should_retry_status(
    *,
    logger: LoggerPort,
    category: ErrorCategory,
    status_code: int,
) -> bool:
    """Determine if HTTP status code should be retried."""
    should_retry = category == ErrorCategory.RECOVERABLE
    logger.debug(
        "retry_decision",
        status_code=status_code,
        category=category.value,
        should_retry=should_retry,
        decision_source="http_status",
    )
    return bool(should_retry)


def wrap_adapter_error(
    *,
    error_mapper: DomainInfraExceptionMapper,
    error: Exception,
    error_type: ErrorType,
    provider: str,
    status_code: int | None = None,
    retry_after: float | None = None,
    entity: str | None = None,
    pipeline: str | None = None,
    operation: str | None = None,
) -> ExternalServiceError:
    """Wrap exception in appropriate ExternalServiceError."""
    return error_mapper.map_to_domain_error(
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
