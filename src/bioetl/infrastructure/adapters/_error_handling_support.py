"""Internal structured-context and telemetry helpers for adapter errors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.types import ErrorType, JsonDict
from bioetl.infrastructure.adapters.adapter_error_classifier import ErrorCategory

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


def build_adapter_error_context(
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
            k: v for k, v in context.items() if k not in _ERROR_CONTEXT_RESERVED_KEYS
        },
    )


def emit_error_telemetry(
    *,
    logger: LoggerPort,
    metrics: MetricsPort | None,
    provider: str,
    operation: str,
    error: Exception,
    error_type: ErrorType,
    error_category: ErrorCategory,
    error_context: AdapterErrorContext,
    status_code: int | None,
) -> None:
    """Emit error log and taxonomy counter in unified format."""
    logger.error(
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
    if metrics is not None:
        metrics.increment_counter(
            "bioetl_adapter_error_taxonomy_total",
            1,
            {
                "provider": provider,
                "operation": operation,
                "error_category": error_category.value,
                "error_type": error_type.value,
            },
        )


def extract_retry_after(response: Response) -> float | None:
    """Extract Retry-After header value from response."""
    retry_after = response.headers.get("Retry-After")
    if retry_after is None:
        return None

    try:
        return float(retry_after)
    except ValueError:
        return 60.0


def safe_optional_str(value: object) -> str | None:
    """Return a string value or None for non-string/blank values."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None
