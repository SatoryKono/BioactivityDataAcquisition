"""Circuit-breaker decorator for data-source ports."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from types import TracebackType
from typing import TYPE_CHECKING, Self

from bioetl.domain.exceptions import BioETLError, CircuitBreakerOpenError
from bioetl.domain.types import CircuitBreakerState, HealthStatus, JsonDict
from bioetl.infrastructure.adapters.decorators._circuit_breaker_support import (
    log_failure_recorded,
    log_manual_reset,
    raise_if_circuit_open,
)
from bioetl.infrastructure.adapters.decorators._circuit_breaker_support import (
    unhealthy_status_if_circuit_open as unhealthy_status_for_open_circuit,
)
from bioetl.infrastructure.adapters.decorators._data_source_delegation import (
    DataSourceFetchRequest,
    close_delegated_data_source,
    delegated_provider_name,
    enter_delegated_data_source,
    exit_delegated_data_source,
    iter_delegated_fetch,
)
from bioetl.infrastructure.adapters.decorators._fetch_request_builder import (
    build_data_source_fetch_request,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        CircuitBreakerPort,
        DataSourcePort,
        LoggerPort,
        MetricsPort,
    )


@dataclass
class CircuitBreakerDataSourceDecorator:
    """Decorator that adds circuit breaker protection to any DataSourcePort.

    Implements DataSourcePort protocol by delegating to wrapped data source
    while protecting against cascading failures via circuit breaker pattern.

    Circuit Breaker States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failing fast, requests are rejected immediately
    - HALF_OPEN: Testing recovery, limited requests allowed

    The decorator wraps:
    - `fetch()`: Protected by circuit breaker, fails fast if open
    - `health_check()`: Protected by circuit breaker

    Attributes:
        data_source: The wrapped DataSourcePort implementation.
        circuit_breaker: CircuitBreakerPort implementation for state management.
        logger: Optional logger for state transition events.
        metrics: Optional metrics for circuit breaker tracking.

    Example:
        >>> cb = CircuitBreakerGuard(provider="chembl", failure_threshold=5)
        >>> decorated = CircuitBreakerDataSourceDecorator(
        ...     data_source=chembl_adapter,
        ...     circuit_breaker=cb,
        ...     logger=logger,
        ... )
        >>> async with decorated:
        ...     async for record in decorated.fetch("activity", limit=100):
        ...         process(record)  # Handle each record
    """

    data_source: DataSourcePort
    circuit_breaker: CircuitBreakerPort
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

    def _check_circuit_state(self) -> None:
        """Check circuit breaker state and raise if open.

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN.
        """
        raise_if_circuit_open(
            circuit_breaker=self.circuit_breaker,
            provider_name=self.provider_name,
            logger=self.logger,
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
        """Fetch records with circuit breaker protection.

        Delegates to the wrapped data source after checking circuit breaker state.
        If the circuit is OPEN the call fails fast without contacting the upstream.

        Args:
            entity_type: Type of entity to fetch (e.g., "activity", "compound").
            limit: Maximum number of records to return.
            query: Optional search query string.
            filter_ids: Optional list of IDs to filter by.
            filter_field: Field name to apply the ID filter on.
            offset: Number of records to skip before returning results.

        Raises:
            CircuitBreakerOpenError: If the circuit breaker is in OPEN state.

        """
        self._check_circuit_state()
        request = build_data_source_fetch_request(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        )
        async for record in self._iterate_with_error_recording(request):
            yield record

    async def _record_fetch_success(self) -> None:
        """Record a completed fetch success through CircuitBreakerPort.call.

        Async generators cannot be wrapped in ``call()`` end-to-end, so success
        is recorded after a full successful iteration. This is required for
        HALF_OPEN recovery (OPEN -> HALF_OPEN probe -> CLOSED on success).
        """

        async def _mark_success() -> None:
            await asyncio.sleep(0)

        try:
            await self.circuit_breaker.call(_mark_success)
        except CircuitBreakerOpenError:
            # Race: breaker re-opened while fetch completed; do not mask success path.
            return

    async def _iterate_with_error_recording(
        self,
        request: DataSourceFetchRequest,
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Iterate protected fetch and record non-circuit errors."""
        try:
            async for record in iter_delegated_fetch(self.data_source, request):
                yield record
            await self._record_fetch_success()
        except CircuitBreakerOpenError:
            raise
        except BioETLError as exc:
            log_failure_recorded(
                self.logger,
                circuit_breaker=self.circuit_breaker,
                provider_name=self.provider_name,
                error=exc,
            )
            raise

    async def health_check(self) -> HealthStatus:
        """Check health with circuit breaker protection.

        If circuit is open, returns UNHEALTHY without calling the data source.

        Returns:
            Health status from the wrapped data source or UNHEALTHY if circuit open.
        """
        open_circuit_status = unhealthy_status_for_open_circuit(
            circuit_breaker=self.circuit_breaker,
            provider_name=self.provider_name,
            logger=self.logger,
        )
        if open_circuit_status is not None:
            return open_circuit_status

        try:
            result = await self.circuit_breaker.call(self.data_source.health_check)
            return result
        except CircuitBreakerOpenError:
            return HealthStatus.UNHEALTHY

    async def aclose(self) -> None:
        """Close the wrapped data source."""
        await close_delegated_data_source(self.data_source)

    def get_circuit_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state.

        Useful for monitoring and debugging.

        Returns:
            Current CircuitBreakerState.
        """
        return self.circuit_breaker.get_state()

    def get_failure_count(self) -> int:
        """Get current failure count.

        Returns:
            Number of consecutive failures.
        """
        return int(self.circuit_breaker.get_failure_count())

    def reset_circuit(self) -> None:
        """Manually reset circuit breaker to CLOSED state.

        Use with caution - bypasses normal recovery logic.
        """
        self.circuit_breaker.reset()
        log_manual_reset(self.logger, provider_name=self.provider_name)
