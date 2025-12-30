"""Unit tests for the PostrunService class."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.postrun_service import (
    DQResult,
    PostrunService,
    VacuumResult,
)
from bioetl.domain.config import DQConfig, PipelineConfig, RuntimeConfig
from bioetl.domain.exceptions.data_quality import DataQualityThresholdError
from bioetl.domain.types import RunType


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
def mock_services(mock_metrics):
    """Create mock pipeline services."""
    services = MagicMock()
    services.metrics = mock_metrics
    services.dq_monitor = None
    return services


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
        return_value=VacuumResult(silver_files_removed=10, gold_files_removed=5, skipped=False)
    )
    return service


@pytest.fixture
def postrun_service(
    pipeline_config, runtime_config, mock_services, mock_logger, mock_lifecycle_service
):
    """Create a PostrunService instance."""
    return PostrunService(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        logger=mock_logger,
        lifecycle_service=mock_lifecycle_service,
    )


@pytest.mark.unit
class TestPostrunServiceInit:
    """Tests for PostrunService initialization."""

    def test_initialization(
        self,
        pipeline_config,
        runtime_config,
        mock_services,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test postrun service initializes correctly."""
        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        assert service._config == pipeline_config
        assert service._runtime == runtime_config
        assert service._services == mock_services
        assert service._logger == mock_logger
        assert service._lifecycle_service == mock_lifecycle_service


@pytest.mark.unit
class TestPostrunServiceDQChecks:
    """Tests for PostrunService.run_dq_checks method."""

    @pytest.mark.asyncio
    async def test_dq_checks_skips_without_monitor(
        self, postrun_service, mock_executor
    ):
        """Test run_dq_checks returns early when dq_monitor is None."""
        result = await postrun_service.run_dq_checks(mock_executor)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        assert result.check_duration_ms == 0

    @pytest.mark.asyncio
    async def test_dq_checks_with_no_anomalies(
        self,
        pipeline_config,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_executor,
        mock_metrics,
    ):
        """Test run_dq_checks with no anomalies detected."""
        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        services = MagicMock()
        services.dq_monitor = mock_dq_monitor
        services.metrics = mock_metrics

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        result = await service.run_dq_checks(mock_executor)

        assert result.anomalies_count == 0
        assert result.has_critical is False
        mock_dq_monitor.check_quality.assert_called_once()
        mock_dq_monitor.update_baseline_from_metrics.assert_called_once()

    @pytest.mark.asyncio
    async def test_dq_checks_with_anomalies(
        self,
        pipeline_config,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_executor,
        mock_metrics,
    ):
        """Test run_dq_checks with anomalies detected."""
        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.25,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.SPIKE,
            severity=AnomalySeverity.HIGH,
            z_score=10.0,
            timestamp=datetime.now(UTC),
            message="Error rate spike detected",
        )

        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[anomaly])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        services = MagicMock()
        services.dq_monitor = mock_dq_monitor
        services.metrics = mock_metrics

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        result = await service.run_dq_checks(mock_executor)

        assert result.anomalies_count == 1
        assert result.has_critical is False
        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_dq_checks_with_critical_anomaly(
        self,
        pipeline_config,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_executor,
        mock_metrics,
    ):
        """Test run_dq_checks with critical anomaly."""
        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        critical_anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.50,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            z_score=22.5,
            timestamp=datetime.now(UTC),
            message="Error rate critical",
        )

        mock_dq_monitor = MagicMock()
        mock_dq_monitor.check_quality = MagicMock(return_value=[critical_anomaly])
        mock_dq_monitor.update_baseline_from_metrics = MagicMock()

        services = MagicMock()
        services.dq_monitor = mock_dq_monitor
        services.metrics = mock_metrics

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        result = await service.run_dq_checks(mock_executor)

        assert result.anomalies_count == 1
        assert result.has_critical is True
        mock_logger.error.assert_called()


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
        mock_services,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test run_vacuum_if_enabled delegates to lifecycle service."""
        from bioetl.application.services.medallion_lifecycle import VacuumResult

        mock_lifecycle_service.finalize_run = AsyncMock(
            return_value=VacuumResult(silver_files_removed=0, gold_files_removed=0, skipped=True)
        )

        runtime = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            vacuum_after_run=False,
            dry_run=False,
        )

        service = PostrunService(
            config=pipeline_config,
            runtime=runtime,
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        result = await service.run_vacuum_if_enabled()

        # Verify delegation
        mock_lifecycle_service.finalize_run.assert_called_once_with(
            config=pipeline_config,
            runtime=runtime,
            metrics=mock_services.metrics,
        )
        assert result.skipped is True

    @pytest.mark.asyncio
    async def test_vacuum_returns_finalize_run_result(
        self,
        pipeline_config,
        mock_services,
        mock_logger,
        mock_lifecycle_service,
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
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
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
class TestDQResult:
    """Tests for DQResult dataclass."""

    def test_dq_result_creation(self):
        """Test DQResult creation."""
        result = DQResult(
            anomalies_count=2,
            has_critical=True,
            check_duration_ms=123.45,
        )

        assert result.anomalies_count == 2
        assert result.has_critical is True
        assert result.check_duration_ms == 123.45


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
class TestPostrunServiceDQThresholds:
    """Tests for DQ threshold checking in PostrunService."""

    @pytest.mark.asyncio
    async def test_hard_threshold_exceeded_raises_error(
        self,
        runtime_config,
        mock_services,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test that error rate exceeding hard threshold raises DataQualityThresholdError."""
        # Config with hard_fail_threshold=0.20 (default)
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with 25% error rate (25/100 quarantined)
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 75
        executor.records_gold = 70
        executor.records_quarantined = 25

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        with pytest.raises(DataQualityThresholdError) as exc_info:
            await service.run_dq_checks(executor)

        assert exc_info.value.error_rate == 0.25
        assert exc_info.value.threshold == 0.20
        mock_logger.error.assert_called_once()
        # Verify error log includes expected details
        error_call = mock_logger.error.call_args
        assert error_call[0][0] == "DQ hard threshold exceeded"

    @pytest.mark.asyncio
    async def test_hard_threshold_exactly_at_limit_raises_error(
        self,
        runtime_config,
        mock_services,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test that error rate exactly at hard threshold raises DataQualityThresholdError."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with exactly 20% error rate (20/100 quarantined)
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 80
        executor.records_gold = 75
        executor.records_quarantined = 20

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        with pytest.raises(DataQualityThresholdError):
            await service.run_dq_checks(executor)

    @pytest.mark.asyncio
    async def test_soft_threshold_exceeded_logs_warning_and_emits_metric(
        self,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_metrics,
    ):
        """Test that error rate exceeding soft threshold logs warning and emits metric."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with 10% error rate (10/100 quarantined) - above soft, below hard
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 90
        executor.records_gold = 85
        executor.records_quarantined = 10

        services = MagicMock()
        services.dq_monitor = None
        services.metrics = mock_metrics

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        # Should not raise, but should log warning
        result = await service.run_dq_checks(executor)

        assert result.anomalies_count == 0
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args
        assert warning_call[0][0] == "DQ soft threshold exceeded"

        # Verify metric was emitted
        mock_metrics.increment_counter.assert_called_once_with(
            "dq_soft_threshold_exceeded",
            1,
            {"pipeline": "test_pipeline"},
        )

    @pytest.mark.asyncio
    async def test_soft_threshold_exactly_at_limit_logs_warning(
        self,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_metrics,
    ):
        """Test that error rate exactly at soft threshold logs warning."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with exactly 5% error rate (5/100 quarantined)
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 95
        executor.records_gold = 90
        executor.records_quarantined = 5

        services = MagicMock()
        services.dq_monitor = None
        services.metrics = mock_metrics

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await service.run_dq_checks(executor)

        mock_logger.warning.assert_called_once()
        mock_metrics.increment_counter.assert_called_once()

    @pytest.mark.asyncio
    async def test_below_soft_threshold_no_warning(
        self,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
        mock_metrics,
    ):
        """Test that error rate below soft threshold does not log warning."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with 3% error rate (3/100 quarantined) - below soft threshold
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 97
        executor.records_gold = 95
        executor.records_quarantined = 3

        services = MagicMock()
        services.dq_monitor = None
        services.metrics = mock_metrics

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await service.run_dq_checks(executor)

        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()
        mock_metrics.increment_counter.assert_not_called()

    @pytest.mark.asyncio
    async def test_soft_threshold_without_metrics_still_logs_warning(
        self,
        runtime_config,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test that soft threshold logs warning even when metrics port is None."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            dq=DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=0.20),
        )

        # Executor with 10% error rate
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_bronze = 100
        executor.records_silver = 90
        executor.records_gold = 85
        executor.records_quarantined = 10

        services = MagicMock()
        services.dq_monitor = None
        services.metrics = None  # No metrics port

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        # Should not raise
        result = await service.run_dq_checks(executor)

        assert result.anomalies_count == 0
        mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_zero_records_does_not_fail(
        self,
        runtime_config,
        mock_services,
        mock_logger,
        mock_lifecycle_service,
    ):
        """Test that zero records processed does not trigger threshold errors."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
        )

        # Executor with zero records
        executor = MagicMock()
        executor.records_fetched = 0
        executor.records_bronze = 0
        executor.records_silver = 0
        executor.records_gold = 0
        executor.records_quarantined = 0

        service = PostrunService(
            config=config,
            runtime=runtime_config,
            services=mock_services,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        # Should not raise - error_rate is 0/1=0 which is below thresholds
        result = await service.run_dq_checks(executor)

        assert result.anomalies_count == 0
        mock_logger.warning.assert_not_called()
        mock_logger.error.assert_not_called()
