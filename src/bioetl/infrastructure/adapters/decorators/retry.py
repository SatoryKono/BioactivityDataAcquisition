"""Retrying Data Source Decorator.

Implements the Decorator Pattern for DataSourcePort to add retry logic.
Separates retry concerns from the core adapter logic per ADR-016.

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

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
    RecoverableError,
    RetryExhaustedError,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus

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

    @property
    def provider_name(self) -> str:
        """Delegate to wrapped data source."""
        return self.data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context by delegating to wrapped data source."""
        await self.data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context by delegating to wrapped data source."""
        await self.data_source.__aexit__(exc_type, exc_val, exc_tb)

    def _is_retryable(self, exc: Exception) -> bool:
        """Check if exception should trigger a retry.

        Retryable conditions:
        - RecoverableError (except CircuitBreakerOpenError which should propagate)
        - Connection/timeout errors
        - Configured retryable exceptions

        Non-retryable:
        - CircuitBreakerOpenError (CB decorator handles this)
        - Critical errors (auth failures, schema errors)
        - Data quality errors (should skip record, not retry)
        """
        # Circuit breaker errors should propagate immediately
        if isinstance(exc, CircuitBreakerOpenError):
            return False

        # RecoverableError hierarchy (except CB errors)
        if isinstance(exc, RecoverableError):
            return True

        # Check configured retryable exceptions
        return self.retry_config.is_retryable_exception(exc)

    async def _calculate_and_wait(self, attempt: int, url: str = "") -> float:
        """Calculate delay and wait before retry.

        Returns:
            The actual wait time in seconds.
        """
        delay = self.retry_config.calculate_delay(attempt, url)
        await asyncio.sleep(delay)
        return delay

    def _log_retry(
        self,
        operation: str,
        attempt: int,
        wait_seconds: float,
        error: Exception,
    ) -> None:
        """Log retry attempt with structured fields."""
        if not self.logger:
            return

        self.logger.warning(
            "data_source_retry",
            stage="fetch",
            operation=operation,
            attempt=attempt + 1,
            max_attempts=self.retry_config.max_attempts,
            wait_seconds=round(wait_seconds, 3),
            error_type=type(error).__name__,
            error_message=str(error),
            provider=self.provider_name,
        )

    def _record_retry_metrics(self, operation: str, retries: int) -> None:
        """Record retry metrics."""
        if not self.metrics or retries == 0:
            return

        self.metrics.increment_counter(
            "data_source_retries_total",
            retries,
            {
                "provider": self.provider_name,
                "operation": operation,
            },
        )

    def _record_exhaustion_metrics(self, operation: str) -> None:
        """Record retry exhaustion metrics."""
        if not self.metrics:
            return

        self.metrics.increment_counter(
            "data_source_retry_exhausted_total",
            1,
            {
                "provider": self.provider_name,
                "operation": operation,
            },
        )

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch records with retry logic.

        Retries the entire fetch operation on recoverable errors.
        If a failure occurs during iteration, the fetch restarts from the beginning.

        Args:
            entity_type: Type of entity to fetch.
            limit: Maximum number of records to fetch.
            query: Optional search query.
            filter_ids: Optional IDs to filter by.
            filter_field: Optional field to filter on.

        Yields:
            Dictionary records from the data source.

        Raises:
            RetryExhaustedError: If all retry attempts fail.
            CircuitBreakerOpenError: If circuit breaker is open (propagates immediately).
        """
        last_error: Exception | None = None
        retries = 0

        for attempt in range(self.retry_config.max_attempts):
            try:
                # Collect records from the async generator
                # We need to materialize to detect errors during iteration
                async for record in self.data_source.fetch(
                    entity_type=entity_type,
                    limit=limit,
                    query=query,
                    filter_ids=filter_ids,
                    filter_field=filter_field,
                ):
                    yield record

                # Success - record metrics and return
                self._record_retry_metrics("fetch", retries)
                return

            except Exception as exc:
                last_error = exc

                if not self._is_retryable(exc):
                    raise

                if self.retry_config.is_last_attempt(attempt):
                    break

                # Calculate delay and wait
                wait_seconds = await self._calculate_and_wait(
                    attempt, f"fetch:{entity_type}"
                )
                self._log_retry("fetch", attempt, wait_seconds, exc)
                retries += 1

        # All retries exhausted
        self._record_retry_metrics("fetch", retries)
        self._record_exhaustion_metrics("fetch")
        raise RetryExhaustedError(
            url=f"{self.provider_name}:{entity_type}",
            attempts=self.retry_config.max_attempts,
            last_error=last_error,
        )

    async def health_check(self) -> HealthStatus:
        """Check health with retry logic.

        Retries health check on transient failures.

        Returns:
            Health status from the wrapped data source.

        Raises:
            RetryExhaustedError: If all retry attempts fail.
        """
        last_error: Exception | None = None
        retries = 0

        for attempt in range(self.retry_config.max_attempts):
            try:
                result = await self.data_source.health_check()
                self._record_retry_metrics("health_check", retries)
                return result

            except Exception as exc:
                last_error = exc

                if not self._is_retryable(exc):
                    raise

                if self.retry_config.is_last_attempt(attempt):
                    break

                wait_seconds = await self._calculate_and_wait(attempt, "health_check")
                self._log_retry("health_check", attempt, wait_seconds, exc)
                retries += 1

        # All retries exhausted
        self._record_retry_metrics("health_check", retries)
        self._record_exhaustion_metrics("health_check")
        raise RetryExhaustedError(
            url=f"{self.provider_name}:health_check",
            attempts=self.retry_config.max_attempts,
            last_error=last_error,
        )

    async def aclose(self) -> None:
        """Close the wrapped data source."""
        await self.data_source.aclose()
