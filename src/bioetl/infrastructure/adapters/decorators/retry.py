"""Retrying Data Source Decorator.

Implements the Decorator Pattern for DataSourcePort to add retry logic.
Separates retry concerns from the core adapter logic per ADR-xxx.

This decorator wraps any DataSourcePort implementation and adds:
- Configurable retry attempts with exponential backoff
- Jitter for avoiding thundering herd
- Structured logging of retry attempts
- Metrics for retry counts and exhaustion

Usage:
    from bioetl.infrastructure.adapters.decorators import RetryingDataSourceDecorator
    from bioetl.domain.resilience import RetryConfig

__all__ = ["RetryingDataSourceDecorator"]


    retry_config = RetryConfig(max_attempts=3, multiplier=2.0)
    decorated = RetryingDataSourceDecorator(
        data_source=base_adapter,
        retry_config=retry_config,
        logger=logger,
    )
    async with decorated:
        async for record in decorated.fetch("activity"):
            process(record)
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
    close_delegated_data_source,
    delegated_provider_name,
    enter_delegated_data_source,
    exit_delegated_data_source,
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


@dataclass
class RetryingDataSourceDecorator:
    """Decorator that adds retry logic to any DataSourcePort.

    Implements DataSourcePort protocol by delegating to wrapped data source
    while adding retry behavior for transient failures.

    The decorator handles retries for:
    - `fetch()`: Retries the entire async generator on failure (not individual yields)
    - `health_check()`: Retries health checks with exponential backoff

    Note on fetch() retry semantics:
    - If an error occurs during iteration, the entire fetch is retried from the start
    - This is by design: partial results may be inconsistent
    - For paginated APIs, the adapter should handle resumption internally

    Attributes:
        data_source: The wrapped DataSourcePort implementation.
        retry_config: Configuration for retry behavior.
        logger: Optional logger for retry events.
        metrics: Optional metrics for retry tracking.

    Example:
        >>> config = RetryConfig(max_attempts=3, multiplier=2.0)
        >>> decorated = RetryingDataSourceDecorator(
        ...     data_source=chembl_adapter,
        ...     retry_config=config,
        ...     logger=logger,
        ... )
        >>> async with decorated:
        ...     async for record in decorated.fetch("activity", limit=100):
        ...         process(record)  # Handle each record
    """

    data_source: DataSourcePort
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    logger: LoggerPort | None = None
    metrics: MetricsPort | None = None
    _data_source: DataSourcePort = field(init=False, repr=False)
    _retry_config: RetryConfig = field(init=False, repr=False)
    _logger: LoggerPort | None = field(init=False, repr=False)
    _metrics: MetricsPort | None = field(init=False, repr=False)

    def __post_init__(self) -> None:
        """Create private aliases for delegation pattern compliance."""
        self._data_source = self.data_source
        self._retry_config = self.retry_config
        self._logger = self.logger
        self._metrics = self.metrics

    @property
    def provider_name(self) -> str:
        """Delegate to wrapped data source."""
        return delegated_provider_name(self._data_source)

    async def __aenter__(self) -> Self:
        """Enter async context by delegating to wrapped data source."""
        await enter_delegated_data_source(self._data_source)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context by delegating to wrapped data source."""
        await exit_delegated_data_source(
            self._data_source,
            exc_type,
            exc_val,
            exc_tb,
        )

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Fetch records with retry logic."""
        last_error: Exception | None = None
        retries = 0
        request = DataSourceFetchRequest(
            entity_type,
            limit,
            query,
            filter_ids,
            filter_field,
            offset,
        )

        for attempt in range(self._retry_config.max_attempts):
            try:
                async for record in self._fetch_once(request):
                    yield record
                record_retry_metrics(
                    self._metrics,
                    provider_name=self.provider_name,
                    operation="fetch",
                    retries=retries,
                )
                return

            except CircuitBreakerOpenError:
                raise
            except retryable_exception_types(self._retry_config) as exc:
                last_error = exc
                if self._retry_config.is_last_attempt(attempt):
                    break
                wait_seconds = await calculate_and_wait_retry_delay(
                    self._retry_config,
                    attempt=attempt,
                    url=f"fetch:{entity_type}",
                )
                log_retry_attempt(
                    self._logger,
                    provider_name=self.provider_name,
                    retry_config=self._retry_config,
                    operation="fetch",
                    attempt=attempt,
                    wait_seconds=wait_seconds,
                    error=exc,
                )
                retries += 1

        raise_retry_exhausted(
            metrics=self._metrics,
            provider_name=self.provider_name,
            operation="fetch",
            retries=retries,
            target=request.entity_type,
            max_attempts=self._retry_config.max_attempts,
            last_error=last_error,
        )

    async def _fetch_once(
        self,
        request: DataSourceFetchRequest,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Run one fetch attempt against the wrapped data source."""
        async for record in iter_delegated_fetch(self._data_source, request):
            yield record

    async def health_check(self) -> HealthStatus:
        """Check health with retry logic."""
        last_error: Exception | None = None
        retries = 0

        for attempt in range(self._retry_config.max_attempts):
            try:
                result = await self._data_source.health_check()
                record_retry_metrics(
                    self._metrics,
                    provider_name=self.provider_name,
                    operation="health_check",
                    retries=retries,
                )
                return result

            except CircuitBreakerOpenError:
                raise
            except retryable_exception_types(self._retry_config) as exc:
                last_error = exc

                if self._retry_config.is_last_attempt(attempt):
                    break

                wait_seconds = await calculate_and_wait_retry_delay(
                    self._retry_config,
                    attempt=attempt,
                    url="health_check",
                )
                log_retry_attempt(
                    self._logger,
                    provider_name=self.provider_name,
                    retry_config=self._retry_config,
                    operation="health_check",
                    attempt=attempt,
                    wait_seconds=wait_seconds,
                    error=exc,
                )
                retries += 1

        raise_retry_exhausted(
            metrics=self._metrics,
            provider_name=self.provider_name,
            operation="health_check",
            retries=retries,
            target="health_check",
            max_attempts=self._retry_config.max_attempts,
            last_error=last_error,
        )

    async def aclose(self) -> None:
        """Close the wrapped data source."""
        await close_delegated_data_source(self._data_source)
