"""Unit tests for the PostrunService class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun_service import (
    PostrunResult,
    PostrunService,
    VacuumResult,
)
from bioetl.application.services.data_quality_service import DataQualityService
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.dq_result import DQResult, DQStatus


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
    metrics.increment_counter = MagicMock()
    return metrics


@pytest.fixture
def pipeline_config():
    """Create a pipeline config."""
    return PipelineConfig(
        pipeline_name="test_postrun_pipeline",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="test_silver",
    )


@pytest.fixture
def runtime_config():
    """Create a runtime config."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        limit=None,
    )


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = MagicMock()
    executor.records_fetched = 100
    executor.records_bronze = 100
    executor.records_silver = 95
    executor.records_gold = 90
    executor.records_quarantined = 5
    return executor


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock lifecycle service."""
    from bioetl.application.services.medallion_lifecycle import VacuumResult

    service = MagicMock()
    service.vacuum = AsyncMock(return_value=10)
    service.finalize_run = AsyncMock(
        return_value=VacuumResult(
            silver_files_removed=10, gold_files_removed=5, skipped=False
        )
    )
    return service


@pytest.fixture
def mock_dq_service():
    """Create a mock DataQualityService."""
    service = MagicMock(spec=DataQualityService)
    service.evaluate = AsyncMock(
        return_value=DQResult(
            error_rate=0.05,
            status=DQStatus.PASSED,
            anomalies=(),
            has_critical=False,
            check_duration_ms=10.0,
        )
    )
    return service


@pytest.fixture
def postrun_service(
    pipeline_config,
    runtime_config,
    mock_dq_service,
    mock_lifecycle_service,
    mock_metrics,
    mock_logger,
):
    """Create a PostrunService instance."""
    return PostrunService(
        config=pipeline_config,
        runtime=runtime_config,
        dq_service=mock_dq_service,
        lifecycle_service=mock_lifecycle_service,
        metrics=mock_metrics,
        logger=mock_logger,
    )


@pytest.mark.unit
class TestPostrunServiceInit:
    """Tests for PostrunService initialization."""

    def test_initialization(
        self,
        pipeline_config,
        runtime_config,
        mock_dq_service,
        mock_lifecycle_service,
        mock_metrics,
        mock_logger,
    ):
        """Test postrun service initializes correctly."""
        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            metrics=mock_metrics,
            logger=mock_logger,
        )

        assert service._config == pipeline_config
        assert service._runtime == runtime_config
        assert service._dq_service == mock_dq_service
        assert service._lifecycle_service == mock_lifecycle_service
        assert service._metrics == mock_metrics
        assert service._logger == mock_logger


@pytest.mark.unit
class TestPostrunServiceRun:
    """Tests for PostrunService.run method."""

    @pytest.mark.asyncio
    async def test_run_returns_postrun_result(
        self, postrun_service, mock_executor, mock_dq_service, mock_lifecycle_service
    ):
        """Test run method returns PostrunResult with DQ and VACUUM results."""
        result = await postrun_service.run(mock_executor)

        assert isinstance(result, PostrunResult)
        assert isinstance(result.dq, DQResult)
        assert isinstance(result.vacuum, VacuumResult)

        mock_dq_service.evaluate.assert_called_once()
        mock_lifecycle_service.finalize_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_propagates_dq_error(
        self, postrun_service, mock_executor, mock_dq_service
    ):
        """Test run method propagates DataQualityThresholdError from DQ service."""
        mock_dq_service.evaluate = AsyncMock(
            side_effect=DataQualityThresholdError(error_rate=0.25, threshold=0.20)
        )

        with pytest.raises(DataQualityThresholdError):
            await postrun_service.run(mock_executor)


@pytest.mark.unit
class TestPostrunServiceDQChecks:
    """Tests for PostrunService.run_dq_checks method."""

    @pytest.mark.asyncio
    async def test_dq_checks_delegates_to_dq_service(
        self, postrun_service, mock_executor, mock_dq_service
    ):
        """Test run_dq_checks delegates to DataQualityService."""
        result = await postrun_service.run_dq_checks(mock_executor)

        assert isinstance(result, DQResult)
        mock_dq_service.evaluate.assert_called_once()

        # Verify metrics dict was passed
        call_args = mock_dq_service.evaluate.call_args
        metrics_dict = call_args[0][0]
        assert "error_rate" in metrics_dict
        assert "record_count" in metrics_dict

    @pytest.mark.asyncio
    async def test_dq_checks_collects_batch_metrics(
        self, postrun_service, mock_executor, mock_dq_service
    ):
        """Test run_dq_checks collects correct batch metrics."""
        await postrun_service.run_dq_checks(mock_executor)

        call_args = mock_dq_service.evaluate.call_args
        metrics_dict = call_args[0][0]

        assert metrics_dict["record_count"] == 100.0
        assert metrics_dict["bronze_count"] == 100.0
        assert metrics_dict["silver_count"] == 95.0
        assert metrics_dict["gold_count"] == 90.0
        assert metrics_dict["quarantined_count"] == 5.0
        assert metrics_dict["error_rate"] == 0.05
        assert metrics_dict["silver_yield"] == 0.95
        assert metrics_dict["gold_yield"] == 0.90


@pytest.mark.unit
class TestPostrunServiceVacuum:
    """Tests for PostrunService.run_vacuum_if_enabled method.

    Note: run_vacuum_if_enabled now delegates to MedallionLifecycleService.finalize_run().
    These tests verify the delegation behavior.
    """

    @pytest.mark.asyncio
    async def test_vacuum_delegates_to_finalize_run(
        self,
        pipeline_config,
        mock_dq_service,
        mock_logger,
        mock_lifecycle_service,
        mock_metrics,
    ):
        """Test run_vacuum_if_enabled delegates to lifecycle service."""
        from bioetl.application.services.medallion_lifecycle import VacuumResult

        mock_lifecycle_service.finalize_run = AsyncMock(
            return_value=VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )
        )

        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            vacuum_after_run=False,
            dry_run=False,
        )

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            metrics=mock_metrics,
            logger=mock_logger,
        )

        result = await service.run_vacuum_if_enabled()

        # Verify delegation
        mock_lifecycle_service.finalize_run.assert_called_once_with(
            config=pipeline_config,
            runtime=runtime,
            metrics=mock_metrics,
        )
        assert result.skipped is True

    @pytest.mark.asyncio
    async def test_vacuum_returns_finalize_run_result(
        self,
        pipeline_config,
        mock_dq_service,
        mock_logger,
        mock_lifecycle_service,
        mock_metrics,
    ):
        """Test run_vacuum_if_enabled returns finalize_run result."""
        from bioetl.application.services.medallion_lifecycle import VacuumResult

        expected_result = VacuumResult(
            silver_files_removed=10, gold_files_removed=5, skipped=False
        )
        mock_lifecycle_service.finalize_run = AsyncMock(return_value=expected_result)

        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            vacuum_after_run=True,
            dry_run=False,
        )

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime,
            dq_service=mock_dq_service,
            lifecycle_service=mock_lifecycle_service,
            metrics=mock_metrics,
            logger=mock_logger,
        )

        result = await service.run_vacuum_if_enabled()

        assert result == expected_result
        assert result.silver_files_removed == 10
        assert result.gold_files_removed == 5
        assert result.skipped is False


@pytest.mark.unit
class TestPostrunServiceCleanup:
    """Tests for PostrunService.cleanup method."""

    @pytest.mark.asyncio
    async def test_cleanup_with_tracer(self, postrun_service):
        """Test cleanup closes tracer."""
        mock_tracer = MagicMock()
        mock_tracer.close = MagicMock()

        await postrun_service.cleanup(mock_tracer)

        mock_tracer.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_without_tracer(self, postrun_service):
        """Test cleanup handles None tracer."""
        # Should not raise
        await postrun_service.cleanup(None)

    @pytest.mark.asyncio
    async def test_cleanup_handles_tracer_error(self, postrun_service, mock_logger):
        """Test cleanup handles tracer close error gracefully."""
        mock_tracer = MagicMock()
        mock_tracer.close = MagicMock(side_effect=Exception("Close failed"))

        # Should not raise
        await postrun_service.cleanup(mock_tracer)

        mock_logger.warning.assert_called()


@pytest.mark.unit
class TestPostrunServiceBatchMetrics:
    """Tests for PostrunService._collect_batch_metrics method."""

    def test_collect_batch_metrics(self, postrun_service, mock_executor):
        """Test batch metrics collection."""
        metrics = postrun_service._collect_batch_metrics(mock_executor)

        assert metrics["record_count"] == 100.0
        assert metrics["bronze_count"] == 100.0
        assert metrics["silver_count"] == 95.0
        assert metrics["gold_count"] == 90.0
        assert metrics["quarantined_count"] == 5.0
        assert metrics["error_rate"] == 0.05
        assert metrics["silver_yield"] == 0.95
        assert metrics["gold_yield"] == 0.90

    def test_collect_batch_metrics_handles_zero_records(self, postrun_service):
        """Test batch metrics collection with zero records."""
        zero_executor = MagicMock()
        zero_executor.records_fetched = 0
        zero_executor.records_bronze = 0
        zero_executor.records_silver = 0
        zero_executor.records_gold = 0
        zero_executor.records_quarantined = 0

        metrics = postrun_service._collect_batch_metrics(zero_executor)

        # Should use max(1, total) to avoid division by zero
        assert metrics["record_count"] == 0.0
        assert metrics["error_rate"] == 0.0


@pytest.mark.unit
class TestPostrunResult:
    """Tests for PostrunResult dataclass."""

    def test_postrun_result_creation(self):
        """Test PostrunResult creation."""
        dq_result = DQResult(
            error_rate=0.05,
            status=DQStatus.PASSED,
        )
        vacuum_result = VacuumResult(
            silver_files_removed=10,
            gold_files_removed=5,
            skipped=False,
        )

        result = PostrunResult(dq=dq_result, vacuum=vacuum_result)

        assert result.dq == dq_result
        assert result.vacuum == vacuum_result


@pytest.mark.unit
class TestVacuumResult:
    """Tests for VacuumResult dataclass."""

    def test_vacuum_result_creation(self):
        """Test VacuumResult creation."""
        result = VacuumResult(
            silver_files_removed=10,
            gold_files_removed=5,
            skipped=False,
        )

        assert result.silver_files_removed == 10
        assert result.gold_files_removed == 5
        assert result.skipped is False


@pytest.mark.unit
class TestPostrunServiceIntegrationWithDataQualityService:
    """Integration tests for PostrunService with real DataQualityService."""

    @pytest.mark.asyncio
    async def test_full_flow_with_real_dq_service(
        self,
        pipeline_config,
        runtime_config,
        mock_lifecycle_service,
        mock_metrics,
        mock_logger,
        mock_executor,
    ):
        """Test full flow using real DataQualityService (no dq_monitor)."""
        # Create real DataQualityService
        dq_service = DataQualityService(
            dq_monitor=None,
            config=pipeline_config.dq,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name=pipeline_config.pipeline_name,
        )

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            dq_service=dq_service,
            lifecycle_service=mock_lifecycle_service,
            metrics=mock_metrics,
            logger=mock_logger,
        )

        result = await service.run(mock_executor)

        assert isinstance(result, PostrunResult)
        # 5% error rate exactly equals soft threshold (5%), so status is WARNING
        assert result.dq.status == DQStatus.WARNING
        assert result.dq.error_rate == 0.05
        assert result.vacuum.skipped is False

    @pytest.mark.asyncio
    async def test_hard_threshold_raised_with_real_dq_service(
        self,
        pipeline_config,
        runtime_config,
        mock_lifecycle_service,
        mock_metrics,
        mock_logger,
    ):
        """Test hard threshold error with real DataQualityService."""
        # Create executor with 25% error rate
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 75
        executor.records_gold = 70
        executor.records_quarantined = 25

        # Create real DataQualityService
        dq_service = DataQualityService(
            dq_monitor=None,
            config=pipeline_config.dq,
            logger=mock_logger,
            metrics=mock_metrics,
            pipeline_name=pipeline_config.pipeline_name,
        )

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            dq_service=dq_service,
            lifecycle_service=mock_lifecycle_service,
            metrics=mock_metrics,
            logger=mock_logger,
        )

        with pytest.raises(DataQualityThresholdError) as exc_info:
            await service.run(executor)

        assert exc_info.value.error_rate == 0.25
        assert exc_info.value.threshold == 0.20
