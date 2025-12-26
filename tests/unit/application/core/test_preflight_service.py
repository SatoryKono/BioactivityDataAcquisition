"""Unit tests for the PreflightService class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.preflight_service import PreflightService
from bioetl.domain.config import PipelineConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions import InfrastructureError
from bioetl.domain.types import (
    ComponentHealthResult,
    HealthReport,
    HealthStatus,
    RunType,
)


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


@pytest.fixture
def mock_metrics():
    """Create a mock metrics port."""
    metrics = MagicMock()
    metrics.set_gauge = MagicMock()
    metrics.observe_histogram = MagicMock()
    return metrics


@pytest.fixture
def pipeline_config():
    """Create a pipeline config."""
    return PipelineConfig(
        pipeline_name="test_preflight_pipeline",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="test_silver",
    )


@pytest.fixture
def mock_context(mock_logger):
    """Create a mock pipeline context."""
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock()
    services.storage = MagicMock()
    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    services.logger = MagicMock()
    services.logger.info = MagicMock()
    services.logger.warning = MagicMock()
    services.logger.error = MagicMock()
    return services


@pytest.fixture
def preflight_service(pipeline_config, mock_context, mock_logger, mock_metrics):
    """Create a PreflightService instance."""
    return PreflightService(
        config=pipeline_config,
        context=mock_context,
        logger=mock_logger,
        metrics=mock_metrics,
    )


@pytest.mark.unit
class TestPreflightServiceInit:
    """Tests for PreflightService initialization."""

    def test_initialization(
        self, pipeline_config, mock_context, mock_logger, mock_metrics
    ):
        """Test preflight service initializes correctly."""
        service = PreflightService(
            config=pipeline_config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        assert service._config == pipeline_config
        assert service._context == mock_context
        assert service._logger == mock_logger
        assert service._metrics == mock_metrics


@pytest.mark.unit
class TestPreflightServiceValidation:
    """Tests for PreflightService.validate_infrastructure method."""

    @pytest.mark.asyncio
    async def test_validate_infrastructure_success(
        self, preflight_service, mock_services
    ):
        """Test validate_infrastructure with healthy components."""
        report = await preflight_service.validate_infrastructure(mock_services)

        assert report.is_healthy
        assert len(report.results) == 2  # storage + data_source

    @pytest.mark.asyncio
    async def test_validate_infrastructure_logs_start(
        self, preflight_service, mock_services, mock_logger
    ):
        """Test validate_infrastructure logs start message."""
        await preflight_service.validate_infrastructure(mock_services)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Validating infrastructure health" in call for call in calls)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_logs_completion(
        self, preflight_service, mock_services, mock_logger
    ):
        """Test validate_infrastructure logs completion message."""
        await preflight_service.validate_infrastructure(mock_services)

        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("health check completed" in call for call in calls)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_per_component_metrics(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records per-component metrics."""
        await preflight_service.validate_infrastructure(mock_services)

        # Should have set_gauge calls for each component
        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "pipeline_health_check_passed"
        ]
        assert len(gauge_calls) == 2  # storage + data_source

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_overall_validation_metric(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records overall validation metric."""
        await preflight_service.validate_infrastructure(mock_services)

        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "infrastructure_validated"
        ]
        assert len(gauge_calls) == 1
        # Should be 1.0 for healthy
        assert gauge_calls[0][0][1] == 1.0

    @pytest.mark.asyncio
    async def test_validate_infrastructure_records_duration_metric(
        self, preflight_service, mock_services, mock_metrics
    ):
        """Test validate_infrastructure records duration histogram."""
        await preflight_service.validate_infrastructure(mock_services)

        # Look for the overall duration metric (with pipeline label)
        histogram_calls = [
            call
            for call in mock_metrics.observe_histogram.call_args_list
            if call[0][0] == "health_check_duration_seconds"
            and "pipeline" in call[0][2]  # Overall duration has pipeline label
        ]
        assert len(histogram_calls) == 1

    @pytest.mark.asyncio
    async def test_validate_infrastructure_raises_on_unhealthy(
        self, preflight_service
    ):
        """Test validate_infrastructure raises InfrastructureError on unhealthy."""
        unhealthy_services = MagicMock()
        unhealthy_services.storage = MagicMock()
        unhealthy_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.UNHEALTHY
        )
        unhealthy_services.data_source = MagicMock()
        unhealthy_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        unhealthy_services.logger = MagicMock()

        with pytest.raises(InfrastructureError, match="Health check failed"):
            await preflight_service.validate_infrastructure(unhealthy_services)

    @pytest.mark.asyncio
    async def test_validate_infrastructure_passes_with_degraded(
        self, preflight_service
    ):
        """Test validate_infrastructure passes with degraded status."""
        degraded_services = MagicMock()
        degraded_services.storage = MagicMock()
        degraded_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.DEGRADED
        )
        degraded_services.data_source = MagicMock()
        degraded_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        degraded_services.logger = MagicMock()

        # Should not raise - degraded is acceptable
        report = await preflight_service.validate_infrastructure(degraded_services)
        assert report.is_healthy


@pytest.mark.unit
class TestPreflightServiceMetrics:
    """Tests for PreflightService metric recording."""

    @pytest.mark.asyncio
    async def test_records_failed_validation_metric(
        self, pipeline_config, mock_context, mock_logger, mock_metrics
    ):
        """Test records 0.0 for failed validation."""
        service = PreflightService(
            config=pipeline_config,
            context=mock_context,
            logger=mock_logger,
            metrics=mock_metrics,
        )

        unhealthy_services = MagicMock()
        unhealthy_services.storage = MagicMock()
        unhealthy_services.storage.health_check = AsyncMock(
            return_value=HealthStatus.UNHEALTHY
        )
        unhealthy_services.data_source = MagicMock()
        unhealthy_services.data_source.health_check = AsyncMock(
            return_value=HealthStatus.HEALTHY
        )
        unhealthy_services.logger = MagicMock()

        with pytest.raises(InfrastructureError):
            await service.validate_infrastructure(unhealthy_services)

        # Check that infrastructure_validated was set to 0.0
        gauge_calls = [
            call
            for call in mock_metrics.set_gauge.call_args_list
            if call[0][0] == "infrastructure_validated"
        ]
        assert len(gauge_calls) == 1
        assert gauge_calls[0][0][1] == 0.0
