"""Tests for BaseSyncAdapter health_check logging and metrics."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

from bioetl.domain.types import HealthStatus
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class ConcreteSyncAdapter(BaseSyncAdapter):
    """Concrete implementation of BaseSyncAdapter for testing."""

    provider_name: str = "test_provider"

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict]:
        """Fetch implementation for testing."""
        yield {"id": 1}


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.warning = MagicMock()
    logger.info = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.increment_counter = MagicMock()
    return metrics


@pytest.fixture
def adapter_with_mocks(mock_logger, mock_metrics):
    """Create adapter with mock logger and metrics."""
    adapter = ConcreteSyncAdapter(
        rate=10.0,
        logger=mock_logger,
        metrics=mock_metrics,
    )
    yield adapter
    adapter.thread_pool.shutdown(wait=False)


@pytest.fixture
def adapter_failing_probe(mock_logger, mock_metrics):
    """Create adapter with failing health probe."""

    class FailingAdapter(ConcreteSyncAdapter):
        async def _probe_health(self) -> HealthStatus:
            raise ConnectionError("Connection refused")

    adapter = FailingAdapter(
        rate=10.0,
        logger=mock_logger,
        metrics=mock_metrics,
    )
    yield adapter
    adapter.thread_pool.shutdown(wait=False)


class TestHealthCheckLogging:
    """Tests for health_check logging on failure."""

    async def test_health_check_logs_warning_on_exception(
        self, adapter_failing_probe, mock_logger
    ):
        """Verify warning is logged when health check fails."""
        await adapter_failing_probe.health_check()

        mock_logger.warning.assert_called_once()
        call_kwargs = mock_logger.warning.call_args[1]

        assert call_kwargs["provider"] == "test_provider"
        assert "Connection refused" in call_kwargs["error"]
        assert call_kwargs["error_type"] == "ConnectionError"

    async def test_health_check_logs_event_name(
        self, adapter_failing_probe, mock_logger
    ):
        """Verify correct event name is logged."""
        await adapter_failing_probe.health_check()

        call_args = mock_logger.warning.call_args[0]
        assert call_args[0] == "health_check_failed"

    async def test_health_check_no_logging_on_success(
        self, adapter_with_mocks, mock_logger
    ):
        """Verify no warning logged when health check succeeds."""
        # Default _probe_health returns fallback status without exception
        await adapter_with_mocks.health_check()

        mock_logger.warning.assert_not_called()


class TestHealthCheckMetrics:
    """Tests for health_check metrics on failure."""

    async def test_health_check_increments_counter_on_exception(
        self, adapter_failing_probe, mock_metrics
    ):
        """Verify counter is incremented when health check fails."""
        await adapter_failing_probe.health_check()

        mock_metrics.increment_counter.assert_called_once_with(
            "health_check_failures_total",
            1,
            {"provider": "test_provider"},
        )

    async def test_health_check_no_metrics_on_success(
        self, adapter_with_mocks, mock_metrics
    ):
        """Verify no counter increment when health check succeeds."""
        await adapter_with_mocks.health_check()

        mock_metrics.increment_counter.assert_not_called()

    async def test_health_check_returns_fallback_status_on_failure(
        self, adapter_failing_probe
    ):
        """Verify health check returns fallback status on exception."""
        status = await adapter_failing_probe.health_check()

        # With fresh circuit breaker (0 failures), fallback returns HEALTHY
        assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)


class TestMetricsDefaultToNoOp:
    """Tests for default NoOp metrics behavior."""

    async def test_adapter_works_without_explicit_metrics(self, mock_logger):
        """Verify adapter works when no metrics port is provided."""

        class FailingAdapter(ConcreteSyncAdapter):
            async def _probe_health(self) -> HealthStatus:
                raise RuntimeError("Test error")

        adapter = FailingAdapter(rate=10.0, logger=mock_logger)
        try:
            # Should not raise - NoOpMetrics handles the call silently
            status = await adapter.health_check()
            assert status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
        finally:
            adapter.thread_pool.shutdown(wait=False)
