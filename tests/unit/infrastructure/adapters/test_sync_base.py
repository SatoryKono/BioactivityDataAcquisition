"""Tests for BaseSyncAdapter health_check logging."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter


class StubSyncAdapter(BaseSyncAdapter):
    """Concrete adapter for testing BaseSyncAdapter."""

    provider_name: str = "test_provider"

    def __init__(
        self,
        logger: Any,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
        metrics: Any = None,
        fail_probe: bool = False,
        probe_error: Exception | None = None,
    ) -> None:
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=metrics,
        )
        self._fail_probe = fail_probe
        self._probe_error = probe_error or Exception("Probe failed")

    async def _probe_health(self) -> HealthStatus:
        """Test implementation that can be configured to fail."""
        if self._fail_probe:
            raise self._probe_error
        return HealthStatus.HEALTHY

    async def fetch(
        self,
        entity: str,
        query: str | None = None,
        limit: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Not used in these tests."""
        yield {}  # pragma: no cover


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock()


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port for testing."""
    return MagicMock()


@pytest.fixture
def rate_limiter():
    """Create a rate limiter for testing."""
    return TokenBucket(rate=100.0, capacity=200, provider="test")


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreaker(provider="test", failure_threshold=5, recovery_timeout=300)


@pytest.fixture
def thread_pool():
    """Create a thread pool for testing."""
    pool = ThreadPoolExecutor(max_workers=2)
    yield pool
    pool.shutdown(wait=False)


class TestHealthCheckLogging:
    """Tests for health_check logging behavior."""

    async def test_health_check_logs_warning_on_exception(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check logs warning when _probe_health raises."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=ConnectionError("Connection refused"),
        )

        status = await adapter.health_check()

        # Verify warning was logged with correct parameters
        mock_logger.warning.assert_called_once_with(
            "health_check_failed",
            provider="test_provider",
            error="Connection refused",
            error_type="ConnectionError",
        )
        # Fallback status should be returned
        assert status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )

    async def test_health_check_increments_failure_metric_on_exception(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check increments failure metric when _probe_health raises."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            fail_probe=True,
        )

        await adapter.health_check()

        # Verify metric was incremented
        mock_metrics.increment_counter.assert_called_once_with(
            "health_check_failures_total",
            1,
            {"provider": "test_provider"},
        )

    async def test_health_check_no_logging_on_success(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check does not log warning on success."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            fail_probe=False,
        )

        status = await adapter.health_check()

        # No warning should be logged on success
        mock_logger.warning.assert_not_called()
        mock_metrics.increment_counter.assert_not_called()
        assert status == HealthStatus.HEALTHY

    async def test_health_check_uses_noop_metrics_by_default(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check works without explicit metrics (uses NoOpMetrics)."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            fail_probe=True,
        )

        # Should not raise even without explicit metrics
        status = await adapter.health_check()

        # Should still log warning
        mock_logger.warning.assert_called_once()
        assert status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )

    async def test_health_check_logs_correct_error_type(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucket,
        circuit_breaker: CircuitBreaker,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check logs the correct error type name."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=TimeoutError("Request timed out"),
        )

        await adapter.health_check()

        # Verify error_type is the exception class name
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "TimeoutError"
        assert call_kwargs["error"] == "Request timed out"
