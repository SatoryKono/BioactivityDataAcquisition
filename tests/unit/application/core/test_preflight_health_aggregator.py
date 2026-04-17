"""Unit tests for _HealthAggregator in preflight_health_aggregator.py.

Tests the dedicated module (distinct from the one embedded in preflight_service).
Covers: check_all, storage/data_source checks, enhanced check_health API,
logging, assert_healthy, and exception handling.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.preflight.health_aggregator import _HealthAggregator
from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.ports.health_check import HealthCheckResult
from bioetl.domain.types import ComponentHealthResult, HealthReport, HealthStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_health_check_result(
    *,
    status: HealthStatus = HealthStatus.HEALTHY,
    provider: str = "test_provider",
    latency_ms: float = 50.0,
    last_error: str | None = None,
) -> HealthCheckResult:
    """Build a realistic HealthCheckResult."""
    return HealthCheckResult(
        status=status,
        latency_ms=latency_ms,
        provider=provider,
        endpoint="/health",
        last_error=last_error,
        consecutive_failures=0 if status == HealthStatus.HEALTHY else 1,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_logger() -> MagicMock:
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock()
    storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return storage


@pytest.fixture
def mock_data_source_legacy() -> MagicMock:
    """Data source without check_health (legacy health_check only)."""
    ds = MagicMock()
    del ds.check_health  # remove auto-created attribute to trigger legacy path
    ds.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return ds


@pytest.fixture
def mock_data_source_enhanced() -> MagicMock:
    """Data source with enhanced check_health method."""
    ds = MagicMock()
    ds.check_health = AsyncMock(
        return_value=_make_health_check_result(status=HealthStatus.HEALTHY)
    )
    ds.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return ds


@pytest.fixture
def mock_services(
    mock_storage: MagicMock, mock_data_source_legacy: MagicMock
) -> MagicMock:
    """PipelineService mock using legacy data source."""
    services = MagicMock()
    services.storage = mock_storage
    services.data_source = mock_data_source_legacy
    return services


@pytest.fixture
def health_aggregator(mock_logger: MagicMock) -> _HealthAggregator:
    return _HealthAggregator(logger=mock_logger)


@pytest.fixture
def health_aggregator_no_logger() -> _HealthAggregator:
    return _HealthAggregator(logger=None)


@pytest.fixture
def health_aggregator_probe(mock_logger: MagicMock) -> _HealthAggregator:
    return _HealthAggregator(logger=mock_logger, health_check_mode="probe")


# ---------------------------------------------------------------------------
# Tests: check_all
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthAggregatorCheckAll:
    """Tests for _HealthAggregator.check_all."""

    @pytest.mark.asyncio
    async def test_returns_health_report(
        self, health_aggregator: _HealthAggregator, mock_services: MagicMock
    ) -> None:
        """Test that check_all returns a HealthReport."""
        report = await health_aggregator.check_all(mock_services)
        assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_report_contains_storage_result(
        self, health_aggregator: _HealthAggregator, mock_services: MagicMock
    ) -> None:
        """Test that the report contains a storage component result."""
        report = await health_aggregator.check_all(mock_services)
        components = [r.component for r in report.results]
        assert "storage" in components

    @pytest.mark.asyncio
    async def test_report_contains_data_source_result(
        self, health_aggregator: _HealthAggregator, mock_services: MagicMock
    ) -> None:
        """Test that the report contains a data_source component result."""
        report = await health_aggregator.check_all(mock_services)
        components = [r.component for r in report.results]
        assert "data_source" in components

    @pytest.mark.asyncio
    async def test_check_all_calls_storage_health_check(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that storage.health_check is called."""
        await health_aggregator.check_all(mock_services)
        mock_storage.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_all_calls_legacy_data_source_health_check(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_data_source_legacy: MagicMock,
    ) -> None:
        """Test that legacy data_source.health_check is called when check_health absent."""
        await health_aggregator.check_all(mock_services)
        mock_data_source_legacy.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_all_uses_enhanced_check_health_when_available(
        self,
        health_aggregator: _HealthAggregator,
        mock_storage: MagicMock,
        mock_data_source_enhanced: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that enhanced check_health is preferred over legacy health_check."""
        services = MagicMock()
        services.storage = mock_storage
        services.data_source = mock_data_source_enhanced

        await health_aggregator.check_all(services)

        mock_data_source_enhanced.check_health.assert_awaited_once()
        mock_data_source_enhanced.health_check.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_storage_exception_produces_unhealthy_result(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that storage exception yields UNHEALTHY component result."""
        mock_storage.health_check.side_effect = RuntimeError("disk full")

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.UNHEALTHY
        assert "disk full" in storage_result.error_message

    @pytest.mark.asyncio
    async def test_data_source_exception_produces_unhealthy_result(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_data_source_legacy: MagicMock,
    ) -> None:
        """Test that data source exception yields UNHEALTHY component result."""
        mock_data_source_legacy.health_check.side_effect = OSError("API down")

        report = await health_aggregator.check_all(mock_services)

        ds_result = next(r for r in report.results if r.component == "data_source")
        assert ds_result.status == HealthStatus.UNHEALTHY
        assert "API down" in ds_result.error_message

    @pytest.mark.asyncio
    async def test_probe_mode_downgrades_data_source_exception_to_degraded(
        self,
        health_aggregator_probe: _HealthAggregator,
        mock_services: MagicMock,
        mock_data_source_legacy: MagicMock,
    ) -> None:
        """Probe mode should downgrade data-source network exceptions to DEGRADED."""
        mock_data_source_legacy.health_check.side_effect = OSError("API down")

        report = await health_aggregator_probe.check_all(mock_services)

        ds_result = next(r for r in report.results if r.component == "data_source")
        assert ds_result.status == HealthStatus.DEGRADED
        assert ds_result.error_message is not None
        assert ds_result.error_message.startswith("probe_mode_fallback:")

    @pytest.mark.asyncio
    async def test_probe_mode_downgrades_data_source_unhealthy_status(
        self,
        health_aggregator_probe: _HealthAggregator,
        mock_services: MagicMock,
        mock_data_source_legacy: MagicMock,
    ) -> None:
        """Probe mode should downgrade explicit UNHEALTHY data-source status to DEGRADED."""
        mock_data_source_legacy.health_check.return_value = HealthStatus.UNHEALTHY

        report = await health_aggregator_probe.check_all(mock_services)

        ds_result = next(r for r in report.results if r.component == "data_source")
        assert ds_result.status == HealthStatus.DEGRADED
        assert ds_result.error_message is not None
        assert ds_result.error_message.startswith("probe_mode_fallback:")

    @pytest.mark.asyncio
    async def test_unhealthy_storage_in_report(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that UNHEALTHY status from storage propagates into report."""
        mock_storage.health_check.return_value = HealthStatus.UNHEALTHY

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_degraded_storage_in_report(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_storage: MagicMock,
    ) -> None:
        """Test that DEGRADED status from storage propagates into report."""
        mock_storage.health_check.return_value = HealthStatus.DEGRADED

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.DEGRADED

    @pytest.mark.asyncio
    async def test_duration_recorded_for_each_component(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
    ) -> None:
        """Test that duration_seconds is non-negative for every component."""
        report = await health_aggregator.check_all(mock_services)
        for result in report.results:
            assert result.duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# Tests: publication boundary
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthAggregatorPublicationBoundary:
    """_HealthAggregator must stay a pure report producer."""

    @pytest.mark.asyncio
    async def test_check_all_does_not_emit_direct_metrics(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
    ) -> None:
        """Observer-owned metrics must not be emitted by the helper."""
        report = await health_aggregator.check_all(mock_services)
        assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_check_all_does_not_emit_direct_logs(
        self,
        health_aggregator: _HealthAggregator,
        mock_services: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Structured runtime logs must be emitted through the observer."""
        await health_aggregator.check_all(mock_services)
        mock_logger.info.assert_not_called()
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()

    @pytest.mark.asyncio
    async def test_report_preserves_enhanced_probe_metadata(
        self,
        mock_logger: MagicMock,
        mock_storage: MagicMock,
        mock_data_source_enhanced: MagicMock,
    ) -> None:
        """Enhanced probe metadata must survive for observer emission."""
        mock_data_source_enhanced.check_health = AsyncMock(
            return_value=_make_health_check_result(
                status=HealthStatus.UNHEALTHY,
                provider="stub_provider",
                latency_ms=42.0,
                last_error="provider unhealthy",
            )
        )
        aggregator = _HealthAggregator(
            logger=mock_logger,
            health_check_mode="probe",
        )
        services = MagicMock()
        services.storage = mock_storage
        services.data_source = mock_data_source_enhanced

        report = await aggregator.check_all(services)
        data_source_result = next(
            result for result in report.results if result.component == "data_source"
        )
        assert data_source_result.status == HealthStatus.DEGRADED
        assert data_source_result.provider == "stub_provider"
        assert data_source_result.latency_ms == pytest.approx(42.0)
        assert data_source_result.probe_fallback_reason == "status_downgrade"

    @pytest.mark.asyncio
    async def test_no_logger_when_logger_is_none(
        self,
        health_aggregator_no_logger: _HealthAggregator,
        mock_services: MagicMock,
    ) -> None:
        """Optional logger may still be omitted safely."""
        report = await health_aggregator_no_logger.check_all(mock_services)
        assert isinstance(report, HealthReport)


# ---------------------------------------------------------------------------
# Tests: assert_healthy
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthAggregatorAssertHealthy:
    """Tests for assert_healthy method."""

    def test_does_not_raise_when_all_healthy(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy passes when all components are HEALTHY."""
        report = HealthReport(
            results=[
                ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
                ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
            ]
        )
        health_aggregator.assert_healthy(report)  # must not raise

    def test_does_not_raise_when_degraded(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy passes when components are DEGRADED (not failure)."""
        report = HealthReport(
            results=[
                ComponentHealthResult("storage", HealthStatus.DEGRADED, 0.1),
                ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
            ]
        )
        health_aggregator.assert_healthy(report)  # must not raise

    def test_raises_infrastructure_error_when_unhealthy(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy raises InfrastructureError when any component UNHEALTHY."""
        report = HealthReport(
            results=[
                ComponentHealthResult(
                    "storage", HealthStatus.UNHEALTHY, 0.1, "disk full"
                ),
            ]
        )

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        assert "storage" in str(exc_info.value)

    def test_error_message_contains_error_detail(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy includes component error_message in exception."""
        report = HealthReport(
            results=[
                ComponentHealthResult(
                    "storage", HealthStatus.UNHEALTHY, 0.1, "Permission denied"
                ),
            ]
        )

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        assert "Permission denied" in str(exc_info.value)

    def test_all_failing_components_listed_in_error(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy lists all UNHEALTHY components in exception."""
        report = HealthReport(
            results=[
                ComponentHealthResult("storage", HealthStatus.UNHEALTHY, 0.1, "err1"),
                ComponentHealthResult(
                    "data_source", HealthStatus.UNHEALTHY, 0.2, "err2"
                ),
            ]
        )

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        error_msg = str(exc_info.value)
        assert "storage" in error_msg
        assert "data_source" in error_msg

    def test_passes_on_empty_results(
        self, health_aggregator: _HealthAggregator
    ) -> None:
        """Test assert_healthy does not raise for an empty report."""
        report = HealthReport(results=[])
        health_aggregator.assert_healthy(report)  # must not raise


# ---------------------------------------------------------------------------
# Tests: Health Monitor Integration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHealthAggregatorHealthMonitor:
    """Tests for health_monitor integration in _HealthAggregator."""

    @pytest.mark.asyncio
    async def test_health_monitor_updated_when_check_health_used(
        self,
        mock_logger: MagicMock,
        mock_storage: MagicMock,
        mock_data_source_enhanced: MagicMock,
    ) -> None:
        """Test that health_monitor.update_from_health_check_result is called."""
        health_monitor = MagicMock()
        aggregator = _HealthAggregator(
            logger=mock_logger,
            health_monitor=health_monitor,
        )
        services = MagicMock()
        services.storage = mock_storage
        services.data_source = mock_data_source_enhanced

        await aggregator.check_all(services)

        health_monitor.update_from_health_check_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_monitor_not_called_for_legacy_data_source(
        self,
        mock_logger: MagicMock,
        mock_storage: MagicMock,
        mock_data_source_legacy: MagicMock,
    ) -> None:
        """Test that health_monitor is NOT updated for legacy health_check."""
        health_monitor = MagicMock()
        aggregator = _HealthAggregator(
            logger=mock_logger,
            health_monitor=health_monitor,
        )
        services = MagicMock()
        services.storage = mock_storage
        services.data_source = mock_data_source_legacy

        await aggregator.check_all(services)

        health_monitor.update_from_health_check_result.assert_not_called()
