"""Tests for CircuitBreakerDataSourceDecorator.

Tests cover:
- Basic delegation to wrapped data source
- Circuit breaker fail-fast behavior when open
- Success path when circuit is closed
- Health check returns UNHEALTHY when circuit open
- State and failure count access methods
- Manual reset functionality
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.exceptions import CircuitBreakerOpenError
from bioetl.domain.types import CircuitBreakerState, HealthStatus
from bioetl.infrastructure.adapters.decorators.circuit_breaker import (
    CircuitBreakerDataSourceDecorator,
)


class MockDataSource:
    """Mock data source for testing decorators."""

    def __init__(
        self,
        provider_name: str = "test_provider",
        records: list[dict[str, Any]] | None = None,
        health_status: HealthStatus = HealthStatus.HEALTHY,
    ) -> None:
        self._provider_name = provider_name
        self._records = records or []
        self._health_status = health_status
        self._fetch_call_count = 0
        self._health_check_call_count = 0

    @property
    def provider_name(self) -> str:
        return self._provider_name

    async def __aenter__(self) -> MockDataSource:
        await asyncio.sleep(0)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        del exc_type, exc_val, exc_tb
        await asyncio.sleep(0)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        del entity_type, limit, query, filter_ids, filter_field, offset
        self._fetch_call_count += 1
        for record in self._records:
            yield record

    def health_check(self) -> asyncio.Future[HealthStatus]:
        self._health_check_call_count += 1
        return asyncio.sleep(0, result=self._health_status)

    def aclose(self) -> asyncio.Future[None]:
        return asyncio.sleep(0)


class MockCircuitBreaker:
    """Mock circuit breaker for testing."""

    def __init__(
        self,
        state: CircuitBreakerState = CircuitBreakerState.CLOSED,
        failure_count: int = 0,
    ) -> None:
        self._state = state
        self._failure_count = failure_count
        self._call_count = 0
        self._reset_count = 0
        self.recovery_timeout = 60.0
        self._last_failure_time: float | None = None

    def get_state(self) -> CircuitBreakerState:
        return self._state

    def get_failure_count(self) -> int:
        return self._failure_count

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        self._call_count += 1
        if self._state == CircuitBreakerState.OPEN:
            if self._last_failure_time is None:
                raise CircuitBreakerOpenError("test_provider", self.recovery_timeout)
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed < self.recovery_timeout:
                raise CircuitBreakerOpenError(
                    "test_provider", self.recovery_timeout - elapsed
                )
            self._state = CircuitBreakerState.HALF_OPEN
        return await func(*args, **kwargs)

    def reset(self) -> None:
        self._reset_count += 1
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0

    def set_state(self, state: CircuitBreakerState) -> None:
        """Helper to set state for testing."""
        self._state = state
        if state == CircuitBreakerState.OPEN:
            self._last_failure_time = time.monotonic()
        elif state == CircuitBreakerState.CLOSED:
            self._last_failure_time = None


@pytest.fixture
def mock_data_source() -> MockDataSource:
    """Create a mock data source with test data."""
    return MockDataSource(
        provider_name="test_provider",
        records=[{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
    )


@pytest.fixture
def mock_circuit_breaker() -> MockCircuitBreaker:
    """Create a mock circuit breaker in CLOSED state."""
    return MockCircuitBreaker(state=CircuitBreakerState.CLOSED)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics."""
    return MagicMock()


class TestCircuitBreakerDecoratorBasics:
    """Test basic delegation and property access."""

    def test_provider_name_delegated(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that provider_name is delegated to wrapped data source."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )
        assert decorator.provider_name == "test_provider"

    @pytest.mark.asyncio
    async def test_context_manager_delegated(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that context manager methods are delegated."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )
        async with decorator as ds:
            assert ds is decorator

    @pytest.mark.asyncio
    async def test_aclose_delegated(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that aclose is delegated."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )
        # Should not raise
        await decorator.aclose()


class TestCircuitBreakerDecoratorFetch:
    """Test fetch with circuit breaker protection."""

    @pytest.mark.asyncio
    async def test_fetch_success_when_closed(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test successful fetch when circuit is closed."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        async with decorator:
            records = [r async for r in decorator.fetch("activity")]

        assert len(records) == 2
        assert mock_data_source._fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_fails_fast_when_open(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that fetch fails fast when circuit is open."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        async with decorator:
            with pytest.raises(CircuitBreakerOpenError) as exc_info:
                _ = [r async for r in decorator.fetch("activity")]

        # Data source should NOT be called when circuit is open
        assert mock_data_source._fetch_call_count == 0
        assert exc_info.value.provider == "test_provider"

    @pytest.mark.asyncio
    async def test_fetch_allowed_when_half_open(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that fetch is allowed when circuit is half-open (probe request)."""
        mock_circuit_breaker.set_state(CircuitBreakerState.HALF_OPEN)

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        async with decorator:
            records = [r async for r in decorator.fetch("activity")]

        # Should succeed - half-open allows probe requests
        assert len(records) == 2
        assert mock_data_source._fetch_call_count == 1


class TestCircuitBreakerDecoratorHealthCheck:
    """Test health_check with circuit breaker protection."""

    @pytest.mark.asyncio
    async def test_health_check_success_when_closed(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test health check succeeds when circuit is closed."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        result = await decorator.health_check()

        assert result == HealthStatus.HEALTHY
        assert mock_circuit_breaker._call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_returns_unhealthy_when_open(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test health check returns UNHEALTHY when circuit is open."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        result = await decorator.health_check()

        # Should return UNHEALTHY without calling the data source
        assert result == HealthStatus.UNHEALTHY
        assert mock_data_source._health_check_call_count == 0

    @pytest.mark.asyncio
    async def test_health_check_probes_after_recovery_timeout_elapsed(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Health check should stop short-circuiting once recovery timeout elapsed."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)
        mock_circuit_breaker.recovery_timeout = 0.0
        mock_circuit_breaker._last_failure_time = time.monotonic() - 1.0

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        result = await decorator.health_check()

        assert result == HealthStatus.HEALTHY
        assert mock_data_source._health_check_call_count == 1
        assert mock_circuit_breaker._call_count == 1


class TestCircuitBreakerDecoratorStateAccess:
    """Test circuit breaker state access methods."""

    def test_get_circuit_state(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test get_circuit_state returns current state."""
        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        assert decorator.get_circuit_state() == CircuitBreakerState.CLOSED

        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)
        assert decorator.get_circuit_state() == CircuitBreakerState.OPEN

    def test_get_failure_count(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test get_failure_count returns current failure count."""
        mock_circuit_breaker._failure_count = 3

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        assert decorator.get_failure_count() == 3


class TestCircuitBreakerDecoratorReset:
    """Test circuit breaker reset functionality."""

    def test_reset_circuit(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
        mock_logger: MagicMock,
    ) -> None:
        """Test manual circuit reset."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)
        mock_circuit_breaker._failure_count = 5

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
            logger=mock_logger,
        )

        decorator.reset_circuit()

        assert mock_circuit_breaker._reset_count == 1
        assert decorator.get_circuit_state() == CircuitBreakerState.CLOSED
        assert decorator.get_failure_count() == 0
        mock_logger.info.assert_called_once()


class TestCircuitBreakerDecoratorLogging:
    """Test logging integration."""

    @pytest.mark.asyncio
    async def test_open_circuit_logged(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
        mock_logger: MagicMock,
    ) -> None:
        """Test that open circuit rejection is logged."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
            logger=mock_logger,
        )

        async with decorator:
            with pytest.raises(CircuitBreakerOpenError):
                _ = [r async for r in decorator.fetch("activity")]

        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_args = mock_logger.warning.call_args
        assert call_args[0][0] == "circuit_breaker_rejecting"


class TestCircuitBreakerDecoratorRecoveryTimeout:
    """Tests for RF-002: recovery_timeout propagation to CircuitBreakerOpenError."""

    @pytest.mark.asyncio
    async def test_retry_after_uses_guard_recovery_timeout(
        self,
        mock_data_source: MockDataSource,
    ) -> None:
        """retry_after in CircuitBreakerOpenError should match guard's recovery_timeout."""
        cb = MockCircuitBreaker(state=CircuitBreakerState.OPEN)
        cb.recovery_timeout = 120  # type: ignore[attr-defined]

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=cb,
        )

        async with decorator:
            with pytest.raises(CircuitBreakerOpenError) as exc_info:
                _ = [r async for r in decorator.fetch("activity")]

        assert exc_info.value.retry_after == pytest.approx(120.0)

    @pytest.mark.asyncio
    async def test_retry_after_defaults_when_no_recovery_timeout_attr(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """retry_after should default to 60.0 when guard lacks timeout metadata."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)
        delattr(mock_circuit_breaker, "recovery_timeout")
        mock_circuit_breaker._last_failure_time = None

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        async with decorator:
            with pytest.raises(CircuitBreakerOpenError) as exc_info:
                _ = [r async for r in decorator.fetch("activity")]

        assert exc_info.value.retry_after == pytest.approx(60.0)

    @pytest.mark.asyncio
    async def test_fetch_allows_probe_after_recovery_timeout_elapsed(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Fetch should stop failing fast once recovery timeout elapsed."""
        mock_circuit_breaker.set_state(CircuitBreakerState.OPEN)
        mock_circuit_breaker.recovery_timeout = 0.0
        mock_circuit_breaker._last_failure_time = time.monotonic() - 1.0

        decorator = CircuitBreakerDataSourceDecorator(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        async with decorator:
            records = [r async for r in decorator.fetch("activity")]

        assert len(records) == 2
        assert mock_data_source._fetch_call_count == 1
