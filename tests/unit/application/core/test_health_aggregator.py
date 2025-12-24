"""Unit tests for HealthAggregator.

Tests the infrastructure health validation before pipeline execution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.types import ComponentHealthResult, HealthReport, HealthStatus


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.set_gauge = MagicMock()
    metrics.observe_histogram = MagicMock()
    return metrics


@pytest.fixture
def mock_storage():
    """Create a mock storage port."""
    storage = MagicMock()
    storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return storage


@pytest.fixture
def mock_data_source():
    """Create a mock data source port."""
    data_source = MagicMock()
    data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    return data_source


@pytest.fixture
def mock_services(mock_storage, mock_data_source, mock_logger):
    """Create a mock PipelineServices."""
    services = MagicMock()
    services.storage = mock_storage
    services.data_source = mock_data_source
    services.logger = mock_logger
    return services


@pytest.fixture
def health_aggregator(mock_metrics, mock_logger):
    """Create a HealthAggregator instance."""
    return HealthAggregator(metrics=mock_metrics, logger=mock_logger)


@pytest.fixture
def health_aggregator_no_metrics(mock_logger):
    """Create a HealthAggregator without metrics."""
    return HealthAggregator(metrics=None, logger=mock_logger)


@pytest.mark.unit
class TestComponentHealthResult:
    """Test ComponentHealthResult dataclass."""

    def test_creation_with_all_fields(self):
        """Test ComponentHealthResult creation with all fields."""
        result = ComponentHealthResult(
            component="storage",
            status=HealthStatus.HEALTHY,
            duration_seconds=0.5,
            error_message=None,
        )

        assert result.component == "storage"
        assert result.status == HealthStatus.HEALTHY
        assert result.duration_seconds == 0.5
        assert result.error_message is None

    def test_creation_with_error(self):
        """Test ComponentHealthResult creation with error."""
        result = ComponentHealthResult(
            component="data_source",
            status=HealthStatus.UNHEALTHY,
            duration_seconds=1.0,
            error_message="Connection refused",
        )

        assert result.status == HealthStatus.UNHEALTHY
        assert result.error_message == "Connection refused"


@pytest.mark.unit
class TestHealthReport:
    """Test HealthReport dataclass."""

    def test_is_healthy_with_all_healthy(self):
        """Test is_healthy returns True when all components healthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.is_healthy is True

    def test_is_healthy_with_degraded(self):
        """Test is_healthy returns True when some components degraded."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.DEGRADED, 0.2),
        ]
        report = HealthReport(results=results)

        # DEGRADED is not considered a failure for is_healthy
        assert report.is_healthy is True

    def test_is_healthy_with_unhealthy(self):
        """Test is_healthy returns False when any component unhealthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.UNHEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.is_healthy is False

    def test_overall_status_healthy(self):
        """Test overall_status returns HEALTHY when all healthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.overall_status == HealthStatus.HEALTHY

    def test_overall_status_degraded(self):
        """Test overall_status returns DEGRADED when worst is degraded."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.DEGRADED, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.overall_status == HealthStatus.DEGRADED

    def test_overall_status_unhealthy(self):
        """Test overall_status returns UNHEALTHY when any unhealthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.DEGRADED, 0.1),
            ComponentHealthResult("data_source", HealthStatus.UNHEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.overall_status == HealthStatus.UNHEALTHY

    def test_overall_status_empty_results(self):
        """Test overall_status returns HEALTHY for empty results."""
        report = HealthReport(results=[])

        assert report.overall_status == HealthStatus.HEALTHY

    def test_get_failures_returns_unhealthy_only(self):
        """Test get_failures returns only UNHEALTHY components."""
        results = [
            ComponentHealthResult("storage", HealthStatus.UNHEALTHY, 0.1, "disk full"),
            ComponentHealthResult("data_source", HealthStatus.DEGRADED, 0.2),
            ComponentHealthResult("other", HealthStatus.HEALTHY, 0.3),
        ]
        report = HealthReport(results=results)

        failures = report.get_failures()

        assert len(failures) == 1
        assert failures[0].component == "storage"

    def test_get_failures_empty_when_all_healthy(self):
        """Test get_failures returns empty list when all healthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        assert report.get_failures() == []


@pytest.mark.unit
class TestHealthAggregatorCheckAll:
    """Test HealthAggregator.check_all method."""

    @pytest.mark.asyncio
    async def test_check_all_returns_health_report(
        self, health_aggregator, mock_services
    ):
        """Test check_all returns a HealthReport."""
        report = await health_aggregator.check_all(mock_services)

        assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_check_all_checks_storage(
        self, health_aggregator, mock_services, mock_storage
    ):
        """Test check_all checks storage health."""
        await health_aggregator.check_all(mock_services)

        mock_storage.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_all_checks_data_source(
        self, health_aggregator, mock_services, mock_data_source
    ):
        """Test check_all checks data source health."""
        await health_aggregator.check_all(mock_services)

        mock_data_source.health_check.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_check_all_returns_both_components(
        self, health_aggregator, mock_services
    ):
        """Test check_all returns results for both components."""
        report = await health_aggregator.check_all(mock_services)

        component_names = [r.component for r in report.results]
        assert "storage" in component_names
        assert "data_source" in component_names

    @pytest.mark.asyncio
    async def test_check_all_with_healthy_storage(
        self, health_aggregator, mock_services, mock_storage
    ):
        """Test check_all with healthy storage."""
        mock_storage.health_check.return_value = HealthStatus.HEALTHY

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_all_with_unhealthy_storage(
        self, health_aggregator, mock_services, mock_storage
    ):
        """Test check_all with unhealthy storage."""
        mock_storage.health_check.return_value = HealthStatus.UNHEALTHY

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_all_handles_storage_exception(
        self, health_aggregator, mock_services, mock_storage
    ):
        """Test check_all handles storage health check exception."""
        mock_storage.health_check.side_effect = RuntimeError("Storage unavailable")

        report = await health_aggregator.check_all(mock_services)

        storage_result = next(r for r in report.results if r.component == "storage")
        assert storage_result.status == HealthStatus.UNHEALTHY
        assert "Storage unavailable" in storage_result.error_message

    @pytest.mark.asyncio
    async def test_check_all_handles_data_source_exception(
        self, health_aggregator, mock_services, mock_data_source
    ):
        """Test check_all handles data source health check exception."""
        mock_data_source.health_check.side_effect = RuntimeError("API unreachable")

        report = await health_aggregator.check_all(mock_services)

        ds_result = next(r for r in report.results if r.component == "data_source")
        assert ds_result.status == HealthStatus.UNHEALTHY
        assert "API unreachable" in ds_result.error_message

    @pytest.mark.asyncio
    async def test_check_all_records_duration(
        self, health_aggregator, mock_services
    ):
        """Test check_all records duration for each component."""
        report = await health_aggregator.check_all(mock_services)

        for result in report.results:
            assert result.duration_seconds >= 0


@pytest.mark.unit
class TestHealthAggregatorMetrics:
    """Test HealthAggregator metrics recording."""

    @pytest.mark.asyncio
    async def test_records_health_status_gauge(
        self, health_aggregator, mock_services, mock_metrics
    ):
        """Test check_all records health_check_status gauge."""
        await health_aggregator.check_all(mock_services)

        # Should be called twice (storage and data_source)
        assert mock_metrics.set_gauge.call_count == 2

    @pytest.mark.asyncio
    async def test_records_duration_histogram(
        self, health_aggregator, mock_services, mock_metrics
    ):
        """Test check_all records health_check_duration_seconds histogram."""
        await health_aggregator.check_all(mock_services)

        # Should be called twice (storage and data_source)
        assert mock_metrics.observe_histogram.call_count == 2

    @pytest.mark.asyncio
    async def test_gauge_labels_contain_component(
        self, health_aggregator, mock_services, mock_metrics
    ):
        """Test gauge metric includes component label."""
        await health_aggregator.check_all(mock_services)

        # Check that component labels were used
        calls = mock_metrics.set_gauge.call_args_list
        components = [call[0][2]["component"] for call in calls]
        assert "storage" in components
        assert "data_source" in components

    @pytest.mark.asyncio
    async def test_gauge_value_matches_status(
        self, health_aggregator, mock_services, mock_metrics, mock_storage
    ):
        """Test gauge value matches HealthStatus.to_metric_value()."""
        mock_storage.health_check.return_value = HealthStatus.DEGRADED

        await health_aggregator.check_all(mock_services)

        # Find the storage call
        calls = mock_metrics.set_gauge.call_args_list
        storage_call = next(c for c in calls if c[0][2]["component"] == "storage")
        # DEGRADED = 1
        assert storage_call[0][1] == float(HealthStatus.DEGRADED.to_metric_value())

    @pytest.mark.asyncio
    async def test_no_metrics_when_none(
        self, health_aggregator_no_metrics, mock_services
    ):
        """Test no metrics recorded when metrics port is None."""
        # Should not raise exception
        report = await health_aggregator_no_metrics.check_all(mock_services)

        assert isinstance(report, HealthReport)


@pytest.mark.unit
class TestHealthAggregatorLogging:
    """Test HealthAggregator logging behavior."""

    @pytest.mark.asyncio
    async def test_logs_healthy_status(
        self, health_aggregator, mock_services, mock_logger
    ):
        """Test logs info for healthy components."""
        await health_aggregator.check_all(mock_services)

        # Should log info for healthy components
        assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_logs_degraded_status(
        self, health_aggregator, mock_services, mock_logger, mock_storage
    ):
        """Test logs warning for degraded components."""
        mock_storage.health_check.return_value = HealthStatus.DEGRADED

        await health_aggregator.check_all(mock_services)

        # Should log warning for degraded
        assert mock_logger.warning.called

    @pytest.mark.asyncio
    async def test_logs_unhealthy_status(
        self, health_aggregator, mock_services, mock_logger, mock_storage
    ):
        """Test logs error for unhealthy components."""
        mock_storage.health_check.return_value = HealthStatus.UNHEALTHY

        await health_aggregator.check_all(mock_services)

        # Should log error for unhealthy
        assert mock_logger.error.called

    @pytest.mark.asyncio
    async def test_logs_include_component_name(
        self, health_aggregator, mock_services, mock_logger
    ):
        """Test log entries include component name."""
        await health_aggregator.check_all(mock_services)

        # Check that info was called with component in kwargs
        calls = mock_logger.info.call_args_list
        for call in calls:
            if "component" in call[1]:
                assert call[1]["component"] in ["storage", "data_source"]


@pytest.mark.unit
class TestHealthAggregatorAssertHealthy:
    """Test HealthAggregator.assert_healthy method."""

    def test_assert_healthy_passes_when_all_healthy(self, health_aggregator):
        """Test assert_healthy does not raise when all healthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.HEALTHY, 0.1),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        # Should not raise
        health_aggregator.assert_healthy(report)

    def test_assert_healthy_passes_when_degraded(self, health_aggregator):
        """Test assert_healthy does not raise when degraded."""
        results = [
            ComponentHealthResult("storage", HealthStatus.DEGRADED, 0.1),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        # Should not raise for DEGRADED
        health_aggregator.assert_healthy(report)

    def test_assert_healthy_raises_when_unhealthy(self, health_aggregator):
        """Test assert_healthy raises InfrastructureError when unhealthy."""
        results = [
            ComponentHealthResult("storage", HealthStatus.UNHEALTHY, 0.1, "disk full"),
            ComponentHealthResult("data_source", HealthStatus.HEALTHY, 0.2),
        ]
        report = HealthReport(results=results)

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        assert "storage" in str(exc_info.value)

    def test_assert_healthy_raises_with_error_message(self, health_aggregator):
        """Test assert_healthy includes error message in exception."""
        results = [
            ComponentHealthResult(
                "storage", HealthStatus.UNHEALTHY, 0.1, "Permission denied"
            ),
        ]
        report = HealthReport(results=results)

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        assert "Permission denied" in str(exc_info.value)

    def test_assert_healthy_lists_all_failures(self, health_aggregator):
        """Test assert_healthy lists all failed components."""
        results = [
            ComponentHealthResult("storage", HealthStatus.UNHEALTHY, 0.1, "error1"),
            ComponentHealthResult("data_source", HealthStatus.UNHEALTHY, 0.2, "error2"),
        ]
        report = HealthReport(results=results)

        with pytest.raises(InfrastructureError) as exc_info:
            health_aggregator.assert_healthy(report)

        error_msg = str(exc_info.value)
        assert "storage" in error_msg
        assert "data_source" in error_msg


@pytest.mark.unit
class TestHealthAggregatorIntegration:
    """Integration tests for HealthAggregator with realistic scenarios."""

    @pytest.mark.asyncio
    async def test_healthy_infrastructure_scenario(
        self, health_aggregator, mock_services, mock_storage, mock_data_source
    ):
        """Test typical healthy infrastructure scenario."""
        mock_storage.health_check.return_value = HealthStatus.HEALTHY
        mock_data_source.health_check.return_value = HealthStatus.HEALTHY

        report = await health_aggregator.check_all(mock_services)

        assert report.is_healthy is True
        assert report.overall_status == HealthStatus.HEALTHY

        # Should not raise
        health_aggregator.assert_healthy(report)

    @pytest.mark.asyncio
    async def test_degraded_data_source_scenario(
        self, health_aggregator, mock_services, mock_storage, mock_data_source
    ):
        """Test scenario with degraded data source (rate limiting)."""
        mock_storage.health_check.return_value = HealthStatus.HEALTHY
        mock_data_source.health_check.return_value = HealthStatus.DEGRADED

        report = await health_aggregator.check_all(mock_services)

        assert report.is_healthy is True  # DEGRADED is not a failure
        assert report.overall_status == HealthStatus.DEGRADED

        # Should not raise (pipeline can continue with degraded performance)
        health_aggregator.assert_healthy(report)

    @pytest.mark.asyncio
    async def test_unhealthy_storage_fails_fast(
        self, health_aggregator, mock_services, mock_storage, mock_data_source
    ):
        """Test that unhealthy storage causes fail-fast."""
        mock_storage.health_check.return_value = HealthStatus.UNHEALTHY
        mock_data_source.health_check.return_value = HealthStatus.HEALTHY

        report = await health_aggregator.check_all(mock_services)

        assert report.is_healthy is False

        with pytest.raises(InfrastructureError):
            health_aggregator.assert_healthy(report)

    @pytest.mark.asyncio
    async def test_api_timeout_scenario(
        self, health_aggregator, mock_services, mock_storage, mock_data_source
    ):
        """Test scenario where API health check times out."""
        mock_storage.health_check.return_value = HealthStatus.HEALTHY

        async def slow_health_check():
            raise TimeoutError("API health check timed out")

        mock_data_source.health_check.side_effect = slow_health_check

        report = await health_aggregator.check_all(mock_services)

        ds_result = next(r for r in report.results if r.component == "data_source")
        assert ds_result.status == HealthStatus.UNHEALTHY
        assert "timed out" in ds_result.error_message
