"""Retry-decision and wrap/handle helpers for AdapterErrorHandler."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from bioetl.domain.exceptions import ExternalServiceError
from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters._error_handling_support import (
    AdapterErrorContext,
    safe_optional_str,
)
from bioetl.infrastructure.adapters.adapter_error_classifier import ErrorCategory
from bioetl.infrastructure.errors import (
    DomainErrorMappingInput,
    DomainInfraExceptionMapper,
)
from bioetl.infrastructure.errors.exception_mapper import InfrastructureSourceError

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.adapter_error_classifier import (
        AdapterErrorClassifier,
    )

__all__ = [
    "decide_should_retry",
    "decide_should_retry_status",
    "handle_and_wrap_error",
    "wrap_adapter_error",
]


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


def handle_and_wrap_error(
    *,
    log_error_fn: object,
    wrap_error_fn: object,
    error: Exception,
    provider: str,
    operation: str,
    context: JsonDict | None,
) -> ExternalServiceError:
    """Handle error: log and wrap in one step.

    ``log_error_fn`` and ``wrap_error_fn`` are bound methods on AdapterErrorHandler
    (typed as object to avoid circular protocol definitions).
    """
    context = context or {}
    log_error = cast(
        "callable",  # type: ignore[valid-type]
        log_error_fn,
    )
    wrap_error = cast(
        "callable",  # type: ignore[valid-type]
        wrap_error_fn,
    )
    # Prefer Protocol-style duck typing via direct calls.
    error_context = cast(
        AdapterErrorContext,
        log_error(provider, operation, error, context),  # type: ignore[operator]
    )
    return cast(
        ExternalServiceError,
        wrap_error(  # type: ignore[operator]
            error=error,
            provider=provider,
            status_code=error_context.status_code,
            retry_after=error_context.retry_after,
            entity=safe_optional_str(context.get("entity")),
            pipeline=safe_optional_str(context.get("pipeline")),
            operation=operation,
        ),
    )
