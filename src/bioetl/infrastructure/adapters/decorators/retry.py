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

from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus, JsonDict
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
    close_delegated_data_source,
    delegated_provider_name,
    enter_delegated_data_source,
    exit_delegated_data_source,
)
from bioetl.infrastructure.adapters.decorators._retry_operations import (
    retry_fetch_records,
    retry_health_check,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort

__all__ = ["RetryingDataSourceDecorator"]


@dataclass
class RetryingDataSourceDecorator:
    """Decorator that adds retry logic to any DataSourcePort.

    Implements DataSourcePort protocol by delegating to wrapped data source
    while adding retry behavior for transient failures.

    The decorator handles retries for:
    - `fetch()`: Retries the entire async generator on failure (not individual yields)
    - `health_check()`: Retries health checks with exponential backoff

    Note on fetch() retry semantics:
    - Retries only when no records have been yielded yet
    - Once any record is emitted, failures propagate without restart
    - For paginated APIs, the adapter should handle resumption internally

    Attributes:
        data_source: The wrapped DataSourcePort implementation.
        retry_config: Configuration for retry behavior.
        logger: Optional logger for retry events.
        metrics: Optional metrics for retry tracking.
    """

    data_source: DataSourcePort
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    logger: LoggerPort | None = None
    metrics: MetricsPort | None = None

    @property
    def provider_name(self) -> str:
        """Delegate to wrapped data source."""
        return delegated_provider_name(self.data_source)

    async def __aenter__(self) -> Self:
        """Enter async context by delegating to wrapped data source."""
        await enter_delegated_data_source(self.data_source)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context by delegating to wrapped data source."""
        await exit_delegated_data_source(
            self.data_source,
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
        request = DataSourceFetchRequest(
            entity_type,
            limit,
            query,
            filter_ids,
            filter_field,
            offset,
        )
        async for record in retry_fetch_records(
            data_source=self.data_source,
            retry_config=self.retry_config,
            logger=self.logger,
            metrics=self.metrics,
            provider_name=self.provider_name,
            request=request,
        ):
            yield record

    async def health_check(self) -> HealthStatus:
        """Check health with retry logic."""
        return await retry_health_check(
            health_check_fn=self.data_source.health_check,
            retry_config=self.retry_config,
            logger=self.logger,
            metrics=self.metrics,
            provider_name=self.provider_name,
        )

    async def aclose(self) -> None:
        """Close the wrapped data source."""
        await close_delegated_data_source(self.data_source)
