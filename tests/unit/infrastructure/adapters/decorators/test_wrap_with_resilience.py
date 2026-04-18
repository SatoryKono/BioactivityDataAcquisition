"""Tests for wrap_with_resilience helper function.

Tests cover:
- No decorators when neither config provided
- Only retry decorator when retry_config provided
- Only circuit breaker decorator when circuit_breaker provided
- Both decorators in correct order when both provided
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from typing import Any

import pytest

from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import CircuitBreakerState, HealthStatus
from bioetl.infrastructure.adapters.decorators import (
    CircuitBreakerDataSourceDecorator,
    RetryingDataSourceDecorator,
    wrap_with_resilience,
)


class MockDataSource:
    """Mock data source for testing."""

    def __init__(self, provider_name: str = "test_provider") -> None:
        self._provider_name = provider_name

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
        yield {"id": 1}

    def health_check(self) -> Awaitable[HealthStatus]:
        return asyncio.sleep(0, result=HealthStatus.HEALTHY)

    def aclose(self) -> Awaitable[None]:
        return asyncio.sleep(0)


class MockCircuitBreaker:
    """Mock circuit breaker for testing."""

    def __init__(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0

    def get_state(self) -> CircuitBreakerState:
        return self._state

    def get_failure_count(self) -> int:
        return self._failure_count

    async def call(self, func: Any, *args: Any, **kwargs: Any) -> Any:
        return await func(*args, **kwargs)

    def reset(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0


@pytest.fixture
def mock_data_source() -> MockDataSource:
    """Create a mock data source."""
    return MockDataSource()


@pytest.fixture
def retry_config() -> RetryConfig:
    """Create retry config for tests."""
    return RetryConfig(max_attempts=3)


@pytest.fixture
def mock_circuit_breaker() -> MockCircuitBreaker:
    """Create a mock circuit breaker."""
    return MockCircuitBreaker()


class TestWrapWithResilience:
    """Test wrap_with_resilience helper function."""

    def test_no_decorators_when_no_config(
        self, mock_data_source: MockDataSource
    ) -> None:
        """Test returns original data source when no config provided."""
        result = wrap_with_resilience(data_source=mock_data_source)

        # Should return the original data source
        assert result is mock_data_source

    def test_retry_decorator_only(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
    ) -> None:
        """Test wraps with retry decorator only when retry_config provided."""
        result = wrap_with_resilience(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        assert isinstance(result, RetryingDataSourceDecorator)
        # Inner data source should be the original
        assert result.data_source is mock_data_source

    def test_circuit_breaker_decorator_only(
        self,
        mock_data_source: MockDataSource,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test wraps with CB decorator only when circuit_breaker provided."""
        result = wrap_with_resilience(
            data_source=mock_data_source,
            circuit_breaker=mock_circuit_breaker,
        )

        assert isinstance(result, CircuitBreakerDataSourceDecorator)
        # Inner data source should be the original
        assert result.data_source is mock_data_source

    def test_both_decorators_in_correct_order(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test wraps with both decorators in correct order.

        Expected order (outermost to innermost):
        1. CircuitBreakerDataSourceDecorator
        2. RetryingDataSourceDecorator
        3. Original data source
        """
        result = wrap_with_resilience(
            data_source=mock_data_source,
            retry_config=retry_config,
            circuit_breaker=mock_circuit_breaker,
        )

        # Outermost should be CB decorator
        assert isinstance(result, CircuitBreakerDataSourceDecorator)

        # Inner should be retry decorator
        inner = result.data_source
        assert isinstance(inner, RetryingDataSourceDecorator)

        # Innermost should be the original
        assert inner.data_source is mock_data_source

    def test_provider_name_preserved(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that provider_name is preserved through decorator chain."""
        result = wrap_with_resilience(
            data_source=mock_data_source,
            retry_config=retry_config,
            circuit_breaker=mock_circuit_breaker,
        )

        assert result.provider_name == "test_provider"

    @pytest.mark.asyncio
    async def test_fetch_works_through_decorator_chain(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_circuit_breaker: MockCircuitBreaker,
    ) -> None:
        """Test that fetch works through the decorator chain."""
        result = wrap_with_resilience(
            data_source=mock_data_source,
            retry_config=retry_config,
            circuit_breaker=mock_circuit_breaker,
        )

        async with result:
            records = [r async for r in result.fetch("activity")]

        assert len(records) == 1
        assert records[0] == {"id": 1}
