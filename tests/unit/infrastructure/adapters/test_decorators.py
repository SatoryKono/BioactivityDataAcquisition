"""Unit tests for Resilience Decorators."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bioetl.infrastructure.adapters.decorators import (
    RetryDataSourceDecorator,
    CircuitBreakerDataSourceDecorator,
)
from bioetl.domain.ports import DataSourcePort, CircuitBreakerPort
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.exceptions import CircuitBreakerOpenError, RetryExhaustedError

@pytest.fixture
def mock_data_source():
    ds = MagicMock(spec=DataSourcePort)
    ds.provider_name = "test_provider"
    ds.health_check = AsyncMock()
    ds.aclose = AsyncMock()
    # Mock fetch as returning an async iterator
    async def _fetch(*args, **kwargs):
        yield {"id": 1}
    ds.fetch.side_effect = _fetch
    return ds

@pytest.fixture
def retry_config():
    return RetryConfig(max_attempts=3, base_delay=0.1, jitter_range=(0,0))

@pytest.fixture
def mock_circuit_breaker():
    cb = MagicMock(spec=CircuitBreakerPort)
    cb.call = AsyncMock()
    return cb

class TestRetryDataSourceDecorator:
    @pytest.mark.asyncio
    async def test_health_check_retries(self, mock_data_source, retry_config):
        """Test health_check retries on failure."""
        decorator = RetryDataSourceDecorator(mock_data_source, retry_config)

        # Fail twice, then succeed
        mock_data_source.health_check.side_effect = [
            ConnectionError("Fail 1"),
            ConnectionError("Fail 2"),
            "OK"
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await decorator.health_check()

        assert result == "OK"
        assert mock_data_source.health_check.call_count == 3

    @pytest.mark.asyncio
    async def test_health_check_exhausts_retries(self, mock_data_source, retry_config):
        """Test health_check raises last error after exhaustion."""
        decorator = RetryDataSourceDecorator(mock_data_source, retry_config)
        mock_data_source.health_check.side_effect = ConnectionError("Persistent Fail")

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConnectionError, match="Persistent Fail"):
                await decorator.health_check()

        assert mock_data_source.health_check.call_count == 3

    @pytest.mark.asyncio
    async def test_fetch_retries_on_immediate_failure(self, mock_data_source, retry_config):
        """Test fetch retries if the generator raises immediately (or during iteration)."""
        decorator = RetryDataSourceDecorator(mock_data_source, retry_config)

        # We need to simulate the wrapped fetch failing during iteration
        # Since fetch returns an iterator, the decorator wraps it.
        # The logic inside decorator is: try to iterate, if fail, sleep and retry (call fetch again).

        # Mock fetch to return an iterator that raises
        async def _fetch_fail(*args, **kwargs):
            raise ConnectionError("Fail fetch")
            yield # unreachable

        async def _fetch_ok(*args, **kwargs):
            yield {"id": 1}

        # Side effect on the mock's fetch method
        # First call returns failing iterator (or raises immediately if implementation supports it)
        # Second call returns success

        # The decorator calls self._wrapped.fetch()

        # Setup mock to return different iterators
        mock_data_source.fetch.side_effect = [_fetch_fail(), _fetch_ok()]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            results = []
            async for record in decorator.fetch("test_entity"):
                results.append(record)

        assert len(results) == 1
        assert results[0]["id"] == 1
        # Should have called fetch twice
        assert mock_data_source.fetch.call_count == 2


class TestCircuitBreakerDataSourceDecorator:
    @pytest.mark.asyncio
    async def test_health_check_uses_circuit_breaker(self, mock_data_source, mock_circuit_breaker):
        """Test health_check is wrapped in circuit breaker."""
        decorator = CircuitBreakerDataSourceDecorator(mock_data_source, mock_circuit_breaker)
        mock_data_source.health_check.return_value = "OK"
        mock_circuit_breaker.call.return_value = "OK"

        await decorator.health_check()

        mock_circuit_breaker.call.assert_called_once_with(mock_data_source.health_check)
