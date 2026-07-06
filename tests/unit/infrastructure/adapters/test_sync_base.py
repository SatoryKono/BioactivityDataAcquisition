"""Tests for BaseSyncAdapter health_check logging.

Tests verify that health_check uses HealthCheckMixin for unified
observability across BaseHttpAdapter and BaseSyncAdapter.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.common import SyncAdapterDependencyContext
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreakerGuard
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter


pytestmark = pytest.mark.unit


class StubSyncAdapter(BaseSyncAdapter):
    """Concrete adapter for testing BaseSyncAdapter."""

    provider_name: str = "test_provider"

    def __init__(
        self,
        logger: Any,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
        error_handler: Any | None = None,
        metrics: Any = None,
        dependency_context: SyncAdapterDependencyContext | None = None,
        fail_probe: bool = False,
        probe_error: Exception | None = None,
        probe_status: HealthStatus = HealthStatus.HEALTHY,
        health_endpoint: str = "/health",
        owns_thread_pool: bool = False,
    ) -> None:
        super().__init__(
            logger=logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            error_handler=error_handler or MagicMock(),
            metrics=metrics,
            dependency_context=dependency_context,
            owns_thread_pool=owns_thread_pool,
        )
        self._fail_probe = fail_probe
        self._probe_error = probe_error or Exception("Probe failed")
        self._probe_status = probe_status
        self._health_endpoint = health_endpoint

    async def _probe_health(self) -> HealthStatus:
        """Test implementation that can be configured to fail."""
        if self._fail_probe:
            raise self._probe_error
        return self._probe_status

    def _get_health_endpoint(self) -> str:
        """Return test health endpoint."""
        return self._health_endpoint

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
    return TokenBucketRateLimiter(rate=100.0, capacity=200, provider="test")


@pytest.fixture
def circuit_breaker():
    """Create a circuit breaker for testing."""
    return CircuitBreakerGuard(
        provider="test", failure_threshold=5, recovery_timeout=300
    )


@pytest.fixture
def thread_pool():
    """Create a thread pool for testing."""
    pool = ThreadPoolExecutor(max_workers=2)
    yield pool
    pool.shutdown(wait=False)


class TestHealthCheckLogging:
    """Tests for health_check logging behavior via HealthCheckMixin."""

    def test_init_uses_injected_error_handler(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that constructor preserves the injected error handler."""
        error_handler = MagicMock()
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            error_handler=error_handler,
            metrics=mock_metrics,
        )

        assert adapter._error_handler is error_handler

    def test_init_uses_dependency_context_over_named_args(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Sync dependency context should be authoritative when supplied."""
        dependency_context = SyncAdapterDependencyContext(
            metrics=mock_metrics,
            error_handler=MagicMock(name="context_error_handler"),
            request_collector=MagicMock(name="request_collector"),
        )

        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=MagicMock(name="legacy_metrics"),
            error_handler=MagicMock(name="legacy_error_handler"),
            dependency_context=dependency_context,
        )

        assert adapter.metrics is mock_metrics
        assert adapter._error_handler is dependency_context.error_handler

    async def test_health_check_logging__warning_on_exception__dd4feee7(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
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

        # Verify warning was logged with correct parameters (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["error_type"] == "ConnectionError"
        assert call_kwargs["error_message"] == "Connection refused"
        assert call_kwargs["endpoint"] == "/health"
        assert "latency_seconds" in call_kwargs

        # Fallback status should be returned
        assert status in (
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
        )

    async def test_health_check_logging__metric_on_exception__356cd42d(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
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

        # Verify failure metric was incremented (via HealthCheckMixin)
        calls = mock_metrics.increment_counter.call_args_list
        failure_call = next(
            (c for c in calls if c[0][0] == "bioetl_health_check_failures_total"),
            None,
        )
        assert failure_call is not None
        assert failure_call[0][1] == 1
        assert failure_call[0][2] == {"provider": "test_provider"}

    async def test_health_check_logging__success_on_success__fd2d492f(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check logs debug and increments success metric on success."""
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

        # Debug log should be emitted (via HealthCheckMixin)
        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["status"] == HealthStatus.HEALTHY.value
        assert "latency_seconds" in call_kwargs

        # Success metric should be incremented
        calls = mock_metrics.increment_counter.call_args_list
        success_call = next(
            (c for c in calls if c[0][0] == "bioetl_health_check_success_total"),
            None,
        )
        assert success_call is not None
        assert success_call[0][2] == {"provider": "test_provider"}

        assert status == HealthStatus.HEALTHY

    async def test_health_check_logging__on_degraded_result__b40d6255(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that DEGRADED probe results are counted separately from healthy success."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            probe_status=HealthStatus.DEGRADED,
        )

        status = await adapter.health_check()

        degraded_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_degraded_total"
            ),
            None,
        )
        success_call = next(
            (
                c
                for c in mock_metrics.increment_counter.call_args_list
                if c[0][0] == "bioetl_health_check_success_total"
            ),
            None,
        )

        assert degraded_call is not None
        assert degraded_call[0][2] == {"provider": "test_provider"}
        assert success_call is None
        mock_logger.warning.assert_called_once()
        assert status == HealthStatus.DEGRADED

    async def test_health_check_logging__latency_histogram__17e8150a(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Test that health_check records latency histogram for both success and failure."""
        # Test success case
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
            metrics=mock_metrics,
            fail_probe=False,
        )

        await adapter.health_check()

        # Verify histogram was observed (via HealthCheckMixin)
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "bioetl_health_check_latency_seconds"
        assert isinstance(call_args[0][1], float)  # latency value
        assert call_args[0][2] == {"provider": "test_provider"}

    async def test_health_check_logging__metrics_by_default__495d07d4(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
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

    async def test_health_check_logging__correct_error_type__89421ae1(
        self,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
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

        # Verify error_type is the exception class name (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "TimeoutError"
        assert call_kwargs["error_message"] == "Request timed out"

    async def test_close_does_not_shutdown_injected_thread_pool(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
        thread_pool: ThreadPoolExecutor,
    ) -> None:
        """Injected executors remain caller-owned by default."""
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=thread_pool,
        )

        await adapter.close()

        assert thread_pool._shutdown is False
        assert thread_pool.submit(lambda: "ok").result() == "ok"

    async def test_close_shuts_down_owned_thread_pool(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
    ) -> None:
        """Owned executors are still cleaned up by the adapter."""
        owned_pool = ThreadPoolExecutor(max_workers=1)
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=owned_pool,
            owns_thread_pool=True,
        )

        await adapter.close()

        assert owned_pool._shutdown is True

    async def test_close_shuts_down_owned_pool_directly(
        self,
        mock_logger: MagicMock,
        rate_limiter: TokenBucketRateLimiter,
        circuit_breaker: CircuitBreakerGuard,
    ) -> None:
        """Async close should shut down owned pools without spawning default executors."""
        owned_pool = ThreadPoolExecutor(max_workers=1)
        adapter = StubSyncAdapter(
            logger=mock_logger,
            rate_limiter=rate_limiter,
            circuit_breaker=circuit_breaker,
            thread_pool=owned_pool,
            owns_thread_pool=True,
        )

        with patch.object(
            owned_pool, "shutdown", wraps=owned_pool.shutdown
        ) as mock_shutdown:
            await adapter.close()

        mock_shutdown.assert_called_once_with(wait=True)
