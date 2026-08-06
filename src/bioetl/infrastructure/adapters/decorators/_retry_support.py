"""Private support helpers for RetryingDataSourceDecorator."""

from __future__ import annotations

import asyncio
from typing import NoReturn

from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
    RecoverableError,
    RetryExhaustedError,
)
from bioetl.domain.ports import LoggerPort, MetricsPort
from bioetl.domain.resilience import RetryConfig


def is_retryable_exception(exc: Exception, retry_config: RetryConfig) -> bool:
    """Return whether the exception should trigger a retry."""
    if isinstance(exc, CircuitBreakerOpenError):
        return False
    if isinstance(exc, RecoverableError):
        return True
    return bool(retry_config.is_retryable_exception(exc))


def retryable_exception_types(
    retry_config: RetryConfig,
) -> tuple[type[Exception], ...]:
    """Build tuple of retryable exception types for ``except`` clauses.

    When ``RetryConfig.retryable_exceptions`` explicitly includes bare
    ``Exception``, preserve it so classification and the ``except`` clause agree.
    """
    configured = tuple(retry_config.retryable_exceptions)
    if Exception in configured:
        # Explicit opt-in: keep Exception and skip RecoverableError duplication.
        return configured
    return (RecoverableError, *configured)


def _redact_transport_error_message(message: str) -> str:
    """Best-effort redact of secret-like tokens from transport error text."""
    import re

    redacted = re.sub(
        r"(?i)(api[_-]?key|token|secret|password|authorization|bearer)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        message,
    )
    return redacted[:500]


async def calculate_and_wait_retry_delay(
    retry_config: RetryConfig,
    *,
    attempt: int,
    url: str = "",
) -> float:
    """Calculate delay and sleep before the next retry attempt."""
    delay = retry_config.calculate_delay(attempt, url)
    await asyncio.sleep(delay)
    return float(delay)


def log_retry_attempt(
    logger: LoggerPort | None,
    *,
    provider_name: str,
    retry_config: RetryConfig,
    operation: str,
    attempt: int,
    wait_seconds: float,
    error: Exception,
) -> None:
    """Emit structured retry log entry when logger is configured."""
    if logger is None:
        return

    logger.warning(
        "data_source_retry",
        stage="fetch",
        operation=operation,
        attempt=attempt + 1,
        max_attempts=retry_config.max_attempts,
        wait_seconds=round(wait_seconds, 3),
        error_type=type(error).__name__,
        error_message=_redact_transport_error_message(str(error)),
        provider=provider_name,
    )


def record_retry_metrics(
    metrics: MetricsPort | None,
    *,
    provider_name: str,
    operation: str,
    retries: int,
) -> None:
    """Record retry-count metric when retries actually happened."""
    if metrics is None or retries == 0:
        return

    metrics.increment_counter(
        "bioetl_data_source_retries_total",
        retries,
        {
            "provider": provider_name,
            "operation": operation,
        },
    )


def record_exhaustion_metrics(
    metrics: MetricsPort | None,
    *,
    provider_name: str,
    operation: str,
) -> None:
    """Record retry exhaustion metric when all attempts failed."""
    if metrics is None:
        return

    metrics.increment_counter(
        "bioetl_data_source_retry_exhausted_total",
        1,
        {
            "provider": provider_name,
            "operation": operation,
        },
    )


def build_retry_exhausted_error(
    *,
    provider_name: str,
    target: str,
    max_attempts: int,
    last_error: Exception | None,
) -> RetryExhaustedError:
    """Build RetryExhaustedError with the canonical decorator message shape."""
    return RetryExhaustedError(
        url=f"{provider_name}:{target}",
        attempts=max_attempts,
        last_error=last_error,
    )


def raise_retry_exhausted(
    *,
    metrics: MetricsPort | None,
    provider_name: str,
    operation: str,
    retries: int,
    target: str,
    max_attempts: int,
    last_error: Exception | None,
) -> NoReturn:
    """Record exhaustion bookkeeping and raise the canonical retry error."""
    record_retry_metrics(
        metrics,
        provider_name=provider_name,
        operation=operation,
        retries=retries,
    )
    record_exhaustion_metrics(
        metrics,
        provider_name=provider_name,
        operation=operation,
    )
    raise build_retry_exhausted_error(
        provider_name=provider_name,
        target=target,
        max_attempts=max_attempts,
        last_error=last_error,
    )
