"""Retry loop helpers for RetryingDataSourceDecorator operations."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
    iter_delegated_fetch,
)
from bioetl.infrastructure.adapters.decorators._retry_support import (
    calculate_and_wait_retry_delay,
    log_retry_attempt,
    raise_retry_exhausted,
    record_retry_metrics,
    retryable_exception_types,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.domain.resilience import RetryConfig

__all__ = [
    "retry_fetch_records",
    "retry_health_check",
]


async def retry_fetch_records(
    *,
    data_source: DataSourcePort,
    retry_config: RetryConfig,
    logger: LoggerPort | None,
    metrics: MetricsPort | None,
    provider_name: str,
    request: DataSourceFetchRequest,
) -> AsyncIterator[JsonDict]:
    """Yield fetch records with full-generator retry on transient failures.

    Retries only when no records have been emitted yet. After the first yield,
    failures propagate so consumers never see restarted partial streams.
    """
    last_error: Exception | None = None
    retries = 0
    emitted_any = False

    for attempt in range(retry_config.max_attempts):
        try:
            async for record in iter_delegated_fetch(data_source, request):
                emitted_any = True
                yield record
            record_retry_metrics(
                metrics,
                provider_name=provider_name,
                operation="fetch",
                retries=retries,
            )
            return

        except CircuitBreakerOpenError:
            raise
        except retryable_exception_types(retry_config) as exc:
            # Never restart a stream that already produced records.
            if emitted_any:
                raise
            last_error = exc
            if retry_config.is_last_attempt(attempt):
                break
            wait_seconds = await calculate_and_wait_retry_delay(
                retry_config,
                attempt=attempt,
                url=f"fetch:{request.entity_type}",
            )
            log_retry_attempt(
                logger,
                provider_name=provider_name,
                retry_config=retry_config,
                operation="fetch",
                attempt=attempt,
                wait_seconds=wait_seconds,
                error=exc,
            )
            retries += 1

    raise_retry_exhausted(
        metrics=metrics,
        provider_name=provider_name,
        operation="fetch",
        retries=retries,
        target=request.entity_type,
        max_attempts=retry_config.max_attempts,
        last_error=last_error,
    )


async def retry_health_check(
    *,
    health_check_fn: Callable[[], Awaitable[HealthStatus]],
    retry_config: RetryConfig,
    logger: LoggerPort | None,
    metrics: MetricsPort | None,
    provider_name: str,
) -> HealthStatus:
    """Run health_check with exponential-backoff retry on transient failures."""
    last_error: Exception | None = None
    retries = 0

    for attempt in range(retry_config.max_attempts):
        try:
            result = await health_check_fn()
            record_retry_metrics(
                metrics,
                provider_name=provider_name,
                operation="health_check",
                retries=retries,
            )
            return result

        except CircuitBreakerOpenError:
            raise
        except retryable_exception_types(retry_config) as exc:
            last_error = exc

            if retry_config.is_last_attempt(attempt):
                break

            wait_seconds = await calculate_and_wait_retry_delay(
                retry_config,
                attempt=attempt,
                url="health_check",
            )
            log_retry_attempt(
                logger,
                provider_name=provider_name,
                retry_config=retry_config,
                operation="health_check",
                attempt=attempt,
                wait_seconds=wait_seconds,
                error=exc,
            )
            retries += 1

    raise_retry_exhausted(
        metrics=metrics,
        provider_name=provider_name,
        operation="health_check",
        retries=retries,
        target="health_check",
        max_attempts=retry_config.max_attempts,
        last_error=last_error,
    )
