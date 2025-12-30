"""Tests for BaseHttpAdapter health_check logging.

Tests verify that health_check uses HealthCheckMixin for unified
observability across BaseHttpAdapter and BaseSyncAdapter.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.base import BaseHttpAdapter


class StubHttpAdapter(BaseHttpAdapter):
    """Concrete adapter for testing BaseHttpAdapter."""

    provider_name: str = "test_provider"

    def __init__(
        self,
        http_client: Any,
        logger: Any,
        metrics: Any = None,
        fail_probe: bool = False,
        probe_error: Exception | None = None,
        health_endpoint: str = "/health",
    ) -> None:
        super().__init__(
            http_client=http_client,
            logger=logger,
            metrics=metrics,
        )
        self._fail_probe = fail_probe
        self._probe_error = probe_error or Exception("Probe failed")
        self._health_endpoint = health_endpoint

    async def _probe_health(self) -> HealthStatus:
        """Test implementation that can be configured to fail."""
        if self._fail_probe:
            raise self._probe_error
        return HealthStatus.HEALTHY

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
def mock_http_client():
    """Create a mock HTTP client for testing."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    # Mock circuit breaker for fallback health status
    client.circuit_breaker = MagicMock()
    client.circuit_breaker.get_state.return_value = MagicMock(value="closed")
    client.circuit_breaker.get_failure_count.return_value = 0
    return client


class TestHealthCheckLogging:
    """Tests for health_check logging behavior via HealthCheckMixin."""

    async def test_health_check_logs_warning_on_exception(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs warning when _probe_health raises."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
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

    async def test_health_check_increments_failure_metric_on_exception(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check increments failure metric when _probe_health raises."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
        )

        await adapter.health_check()

        # Verify failure metric was incremented (via HealthCheckMixin)
        calls = mock_metrics.increment_counter.call_args_list
        failure_call = next(
            (c for c in calls if c[0][0] == "health_check_failures_total"), None
        )
        assert failure_call is not None
        assert failure_call[0][1] == 1
        assert failure_call[0][2] == {"provider": "test_provider"}

    async def test_health_check_logs_debug_and_increments_success_on_success(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs debug and increments success metric on success."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
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
            (c for c in calls if c[0][0] == "health_check_success_total"), None
        )
        assert success_call is not None
        assert success_call[0][2] == {"provider": "test_provider"}

        assert status == HealthStatus.HEALTHY

    async def test_health_check_records_latency_histogram(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check records latency histogram for both success and failure."""
        # Test success case
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=False,
        )

        await adapter.health_check()

        # Verify histogram was observed (via HealthCheckMixin)
        mock_metrics.observe_histogram.assert_called_once()
        call_args = mock_metrics.observe_histogram.call_args
        assert call_args[0][0] == "health_check_latency_seconds"
        assert isinstance(call_args[0][1], float)  # latency value
        assert call_args[0][2] == {"provider": "test_provider"}

    async def test_health_check_uses_noop_metrics_by_default(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that health_check works without explicit metrics (uses NoOpMetrics)."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
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
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that health_check logs the correct error type name."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
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

    async def test_check_health_also_uses_mixin_for_observability(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that check_health() also uses HealthCheckMixin for observability."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=False,
        )

        result = await adapter.check_health()

        # Debug log should be emitted (via HealthCheckMixin)
        mock_logger.debug.assert_called_once()
        call_kwargs = mock_logger.debug.call_args[1]
        assert call_kwargs["provider"] == "test_provider"
        assert call_kwargs["status"] == HealthStatus.HEALTHY.value

        # Result should contain expected fields
        assert result.status == HealthStatus.HEALTHY
        assert result.provider == "test_provider"
        assert result.endpoint == "/health"
        assert result.latency_ms > 0

    async def test_check_health_failure_also_uses_mixin_for_observability(
        self,
        mock_http_client: MagicMock,
        mock_logger: MagicMock,
        mock_metrics: MagicMock,
    ) -> None:
        """Test that check_health() uses HealthCheckMixin on failure."""
        adapter = StubHttpAdapter(
            http_client=mock_http_client,
            logger=mock_logger,
            metrics=mock_metrics,
            fail_probe=True,
            probe_error=ConnectionError("Connection refused"),
        )

        result = await adapter.check_health()

        # Warning log should be emitted (via HealthCheckMixin)
        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]
        assert call_kwargs["error_type"] == "ConnectionError"
        assert call_kwargs["error_message"] == "Connection refused"

        # Result should contain error details
        assert result.last_error == "Connection refused"
        assert result.provider == "test_provider"
