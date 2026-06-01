"""Tests for RetryingDataSourceDecorator.

Tests cover:
- Basic delegation to wrapped data source
- Retry behavior on recoverable errors
- No retry on non-recoverable errors
- Retry exhaustion handling
- Circuit breaker errors propagate immediately
- Metrics and logging integration
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Awaitable
from typing import Any
from unittest.mock import MagicMock

import pytest

from tests.async_utils import collect_async_iterator

from bioetl.domain.exceptions import (
    CircuitBreakerOpenError,
    NetworkError,
    RetryExhaustedError,
)
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.decorators.retry import RetryingDataSourceDecorator


pytestmark = pytest.mark.unit

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
        self._fetch_error: Exception | None = None
        self._health_check_error: Exception | None = None
        self._fail_on_calls: list[int] = []  # 0-indexed call numbers to fail on

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
        del limit, query, filter_ids, filter_field, offset
        self._fetch_call_count += 1

        # Check if we should fail on this call
        if self._fetch_call_count - 1 in self._fail_on_calls:
            if self._fetch_error:
                raise self._fetch_error

        # Otherwise, yield records
        for record in self._records:
            yield record

    def health_check(self) -> Awaitable[HealthStatus]:
        self._health_check_call_count += 1

        # Check if we should fail on this call
        if self._health_check_call_count - 1 in self._fail_on_calls:
            if self._health_check_error:

                async def _raise_error() -> HealthStatus:
                    raise self._health_check_error

                return _raise_error()

        return asyncio.sleep(0, result=self._health_status)

    def aclose(self) -> Awaitable[None]:
        return asyncio.sleep(0)

    def set_fetch_error(self, error: Exception, fail_on_calls: list[int]) -> None:
        """Configure fetch to fail on specific calls (0-indexed)."""
        self._fetch_error = error
        self._fail_on_calls = fail_on_calls

    def set_health_check_error(
        self, error: Exception, fail_on_calls: list[int]
    ) -> None:
        """Configure health_check to fail on specific calls (0-indexed)."""
        self._health_check_error = error
        self._fail_on_calls = fail_on_calls


@pytest.fixture
def mock_data_source() -> MockDataSource:
    """Create a mock data source with test data."""
    return MockDataSource(
        provider_name="test_provider",
        records=[{"id": 1, "name": "test1"}, {"id": 2, "name": "test2"}],
    )


@pytest.fixture
def retry_config() -> RetryConfig:
    """Create retry config for tests with minimal delays."""
    return RetryConfig(
        max_attempts=3,
        base_delay=0.01,  # Very short for testing
        max_delay=0.1,
    )


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_metrics() -> MagicMock:
    """Create a mock metrics."""
    return MagicMock()


class TestRetryingDataSourceDecoratorBasics:
    """Test basic delegation and property access."""

    def test_decorator_basics__name_delegated__85740a6a(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that provider_name is delegated to wrapped data source."""
        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )
        assert decorator.provider_name == "test_provider"

    @pytest.mark.asyncio
    async def test_adapters_decorators_retry_decorator_164__db0c222e(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that context manager methods are delegated."""
        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )
        async with decorator as ds:
            assert ds is decorator

    @pytest.mark.asyncio
    async def test_adapters_decorators_retry_decorator_176__4f14108c(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that aclose is delegated."""
        mock_data_source.aclose = MagicMock(return_value=asyncio.sleep(0))  # type: ignore[method-assign]
        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )
        await decorator.aclose()
        mock_data_source.aclose.assert_called_once_with()


class TestRetryingDataSourceDecoratorFetch:
    """Test fetch retry behavior."""

    @pytest.mark.asyncio
    async def test_fetch_success_no_retry(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test successful fetch without needing retry."""
        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        async with decorator:
            records = await collect_async_iterator(decorator.fetch("activity"))

        assert len(records) == 2
        assert mock_data_source._fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_retry_on_recoverable_error(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that fetch retries on recoverable error."""
        # Fail on first call, succeed on second
        mock_data_source.set_fetch_error(
            NetworkError("Connection reset"),
            fail_on_calls=[0],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        async with decorator:
            records = await collect_async_iterator(decorator.fetch("activity"))

        assert len(records) == 2
        assert mock_data_source._fetch_call_count == 2  # Retried once

    @pytest.mark.asyncio
    async def test_fetch_retry_exhausted(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that fetch raises RetryExhaustedError after all retries."""
        # Fail on all calls
        mock_data_source.set_fetch_error(
            NetworkError("Connection reset"),
            fail_on_calls=[0, 1, 2],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        async with decorator:
            with pytest.raises(RetryExhaustedError) as exc_info:
                _ = await collect_async_iterator(decorator.fetch("activity"))

        assert mock_data_source._fetch_call_count == 3
        assert exc_info.value.attempts == 3
        assert "test_provider:activity" in exc_info.value.url

    @pytest.mark.asyncio
    async def test_fetch_no_retry_on_circuit_breaker_error(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that CircuitBreakerOpenError is not retried."""
        mock_data_source.set_fetch_error(
            CircuitBreakerOpenError("test_provider", 60.0),
            fail_on_calls=[0],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        async with decorator:
            with pytest.raises(CircuitBreakerOpenError):
                _ = await collect_async_iterator(decorator.fetch("activity"))

        # Should not retry CB errors
        assert mock_data_source._fetch_call_count == 1

    @pytest.mark.asyncio
    async def test_fetch_no_retry_on_non_recoverable_error(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test that non-recoverable errors are not retried."""
        mock_data_source.set_fetch_error(
            ValueError("Invalid argument"),
            fail_on_calls=[0],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        async with decorator:
            with pytest.raises(ValueError, match="Invalid argument"):
                _ = await collect_async_iterator(decorator.fetch("activity"))

        assert mock_data_source._fetch_call_count == 1


class TestRetryingDataSourceDecoratorHealthCheck:
    """Test health_check retry behavior."""

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test successful health check."""
        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        result = await decorator.health_check()

        assert result == HealthStatus.HEALTHY
        assert mock_data_source._health_check_call_count == 1

    @pytest.mark.asyncio
    async def test_health_check_retry_on_error(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test health check retries on error."""
        mock_data_source.set_health_check_error(
            NetworkError("Connection timeout"),
            fail_on_calls=[0],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        result = await decorator.health_check()

        assert result == HealthStatus.HEALTHY
        assert mock_data_source._health_check_call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_retry_exhausted(
        self, mock_data_source: MockDataSource, retry_config: RetryConfig
    ) -> None:
        """Test health check exhausts retries."""
        mock_data_source.set_health_check_error(
            NetworkError("Connection timeout"),
            fail_on_calls=[0, 1, 2],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
        )

        with pytest.raises(RetryExhaustedError):
            await decorator.health_check()

        assert mock_data_source._health_check_call_count == 3


class TestRetryingDataSourceDecoratorLogging:
    """Test logging integration."""

    @pytest.mark.asyncio
    async def test_retry_logged(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_logger: MagicMock,
    ) -> None:
        """Test that retries are logged."""
        mock_data_source.set_fetch_error(
            NetworkError("Connection reset"),
            fail_on_calls=[0],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
            logger=mock_logger,
        )

        async with decorator:
            _ = await collect_async_iterator(decorator.fetch("activity"))

        # Verify warning was logged
        mock_logger.warning.assert_called()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["operation"] == "fetch"
        assert call_kwargs["attempt"] == 1
        assert call_kwargs["max_attempts"] == 3


class TestRetryingDataSourceDecoratorMetrics:
    """Test metrics integration."""

    @pytest.mark.asyncio
    async def test_retry_metrics_recorded(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that retry metrics are recorded."""
        mock_data_source.set_fetch_error(
            NetworkError("Connection reset"),
            fail_on_calls=[0, 1],  # Fail twice, succeed on third
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
            metrics=mock_metrics,
        )

        async with decorator:
            _ = await collect_async_iterator(decorator.fetch("activity"))

        # Verify metrics were recorded
        mock_metrics.increment_counter.assert_called()
        calls = mock_metrics.increment_counter.call_args_list

        # Should have retry counter call
        retry_call = [c for c in calls if c[0][0] == "bioetl_data_source_retries_total"]
        assert len(retry_call) == 1
        assert retry_call[0][0][1] == 2  # 2 retries

    @pytest.mark.asyncio
    async def test_exhaustion_metrics_recorded(
        self,
        mock_data_source: MockDataSource,
        retry_config: RetryConfig,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that retry exhaustion metrics are recorded."""
        mock_data_source.set_fetch_error(
            NetworkError("Connection reset"),
            fail_on_calls=[0, 1, 2],
        )

        decorator = RetryingDataSourceDecorator(
            data_source=mock_data_source,
            retry_config=retry_config,
            metrics=mock_metrics,
        )

        async with decorator:
            with pytest.raises(RetryExhaustedError):
                _ = await collect_async_iterator(decorator.fetch("activity"))

        # Verify exhaustion metric was recorded
        calls = mock_metrics.increment_counter.call_args_list
        exhaustion_call = [
            c for c in calls if c[0][0] == "bioetl_data_source_retry_exhausted_total"
        ]
        assert len(exhaustion_call) == 1
