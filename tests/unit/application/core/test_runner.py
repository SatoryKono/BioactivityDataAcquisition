"""Unit tests for the PipelineRunner class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


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
def pipeline_config():
    """Create a pipeline config."""
    return PipelineConfig(
        pipeline_name="test_runner_pipeline",
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


def create_mock_services():
    """Create mock pipeline services with all required attributes.

    This is a factory function used by both fixtures and tests
    that need to create custom service mocks.
    """
    from bioetl.domain.types import HealthStatus

    services = MagicMock(spec=PipelineServices)
    services.lock = AsyncMock()
    services.lock.acquire = AsyncMock(return_value=True)
    services.lock.release = AsyncMock()
    services.lock.heartbeat = AsyncMock(return_value=True)
    services.metrics = MagicMock()
    services.metrics.observe_histogram = MagicMock()
    services.metrics.increment_counter = MagicMock()
    services.metrics.set_gauge = MagicMock()
    # Storage with clear methods and health_check (part of StoragePort contract)
    services.storage = MagicMock()
    services.storage.clear_silver = AsyncMock(return_value=0)
    services.storage.clear_gold = AsyncMock(return_value=0)
    services.storage.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    # Data source with health_check (part of DataSourcePort contract)
    services.data_source = MagicMock()
    services.data_source.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
    # Logger for health aggregator
    services.logger = MagicMock()
    services.logger.info = MagicMock()
    services.logger.warning = MagicMock()
    services.logger.error = MagicMock()
    return services


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    return create_mock_services()


@pytest.fixture
def mock_context(mock_logger):
    """Create a mock pipeline context."""
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_executor():
    """Create a mock executor."""
    executor = AsyncMock()
    executor.execute = AsyncMock()
    executor.records_fetched = 100
    executor.records_bronze = 100
    executor.records_silver = 95
    executor.records_gold = 90
    return executor


@pytest.fixture
def mock_checkpoint_manager():
    """Create a mock checkpoint manager."""
    manager = AsyncMock(spec=CheckpointManager)
    manager.load_checkpoint = AsyncMock(return_value=None)
    manager.delete_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def shutdown_signal():
    """Create a shutdown signal."""
    return ShutdownSignal()


@pytest.fixture
def mock_lock_manager():
    """Mock LockManager class."""
    with patch("bioetl.application.core.runner.LockManager") as mock:
        lock_manager = MagicMock()
        lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
        lock_manager.__aexit__ = AsyncMock(return_value=None)
        mock.create.return_value = lock_manager
        yield mock


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock lifecycle service."""
    from bioetl.application.services.medallion_lifecycle import (
        ClearResult,
        MedallionLifecycleService,
    )

    service = MagicMock(spec=MedallionLifecycleService)
    service.clear = AsyncMock(
        return_value=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False)
    )
    return service


@pytest.fixture
def runner(
    pipeline_config,
    runtime_config,
    mock_services,
    mock_context,
    mock_executor,
    mock_checkpoint_manager,
    shutdown_signal,
    mock_logger,
    mock_lock_manager,
    mock_lifecycle_service,
):
    """Create a PipelineRunner instance."""
    return PipelineRunner(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=mock_context,
        executor=mock_executor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        logger=mock_logger,
        lifecycle_service=mock_lifecycle_service,
    )


@pytest.mark.unit
class TestPipelineRunnerInit:
    """Tests for PipelineRunner initialization."""

    def test_initialization(
        self,
        pipeline_config,
        runtime_config,
        mock_services,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
    ):
        """Test runner initializes correctly."""
        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        assert runner._config == pipeline_config
        assert runner._runtime == runtime_config
        assert runner.shutdown_signal == shutdown_signal
        assert runner._lifecycle_service == mock_lifecycle_service

    def test_lock_manager_created_on_init(
        self,
        pipeline_config,
        runtime_config,
        mock_services,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
    ):
        """Test LockManager is created during initialization."""
        PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        mock_lock_manager.create.assert_called_once()
        call_kwargs = mock_lock_manager.create.call_args.kwargs
        assert call_kwargs["heartbeat_interval"] == runtime_config.heartbeat_interval


@pytest.mark.unit
class TestPipelineRunnerRun:
    """Tests for PipelineRunner.run method."""

    @pytest.mark.asyncio
    async def test_run_success(self, runner, mock_executor, mock_checkpoint_manager):
        """Test successful pipeline run."""
        await runner.run()

        mock_checkpoint_manager.load_checkpoint.assert_called_once()
        mock_executor.execute.assert_called_once()
        mock_checkpoint_manager.delete_checkpoint.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_logs_start_message(self, runner, mock_logger):
        """Test run logs start message."""
        await runner.run()

        mock_logger.info.assert_called()
        calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Starting pipeline" in call for call in calls)

    @pytest.mark.asyncio
    async def test_run_logs_completion_message(self, runner, mock_logger):
        """Test run logs completion message."""
        await runner.run()

        calls = [str(call) for call in mock_logger.info.call_args_list]
        # Observer logs "pipeline_finished" on success
        assert any("pipeline_finished" in call or "finished" in call for call in calls)

    @pytest.mark.asyncio
    async def test_run_handles_shutdown_error(self, runner, mock_executor, mock_logger):
        """Test run handles PipelineShutdownError gracefully."""
        mock_executor.execute.side_effect = PipelineShutdownError("Shutdown requested")

        # Should not raise - shutdown error is handled gracefully
        await runner.run()

        mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_run_raises_general_exception(
        self, runner, mock_executor, mock_logger
    ):
        """Test run re-raises general exceptions."""
        mock_executor.execute.side_effect = RuntimeError("Test error")

        with pytest.raises(RuntimeError, match="Test error"):
            await runner.run()

        mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_run_records_metrics_on_success(self, runner, mock_services):
        """Test metrics are recorded on successful run."""
        await runner.run()

        # Should have health check metrics + pipeline duration metric
        assert mock_services.metrics.observe_histogram.call_count >= 1
        # Find the pipeline duration metric call
        pipeline_calls = [
            call
            for call in mock_services.metrics.observe_histogram.call_args_list
            if call[0][0] == "bioetl_pipeline_duration_seconds"
        ]
        assert len(pipeline_calls) == 1

    @pytest.mark.asyncio
    async def test_run_records_metrics_on_failure(
        self, runner, mock_services, mock_executor
    ):
        """Test metrics are recorded even on failure."""
        mock_executor.execute.side_effect = RuntimeError("Error")

        with pytest.raises(RuntimeError):
            await runner.run()

        # Should have health check metrics + pipeline duration metric
        assert mock_services.metrics.observe_histogram.call_count >= 1
        # Find the pipeline duration metric call with failed status
        pipeline_calls = [
            call
            for call in mock_services.metrics.observe_histogram.call_args_list
            if call[0][0] == "bioetl_pipeline_duration_seconds"
        ]
        assert len(pipeline_calls) == 1
        labels = pipeline_calls[0][1].get("labels") or pipeline_calls[0][0][2]
        assert labels["status"] == "failed"

    @pytest.mark.asyncio
    async def test_run_records_metrics_on_shutdown(
        self, runner, mock_services, mock_executor
    ):
        """Test metrics are recorded with shutdown status."""
        mock_executor.execute.side_effect = PipelineShutdownError("Shutdown")

        await runner.run()

        call_args = mock_services.metrics.observe_histogram.call_args
        labels = call_args[1].get("labels") or call_args[0][2]
        assert labels["status"] == "shutdown"

    @pytest.mark.asyncio
    async def test_run_uses_lock_manager_context(
        self, runner, mock_lock_manager, mock_executor
    ):
        """Test run uses lock manager as context manager."""
        await runner.run()

        # Lock manager should be used as async context manager
        runner._lock_manager.__aenter__.assert_called_once()
        runner._lock_manager.__aexit__.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_calls_executor(
        self, runner, mock_checkpoint_manager, mock_executor
    ):
        """Test run calls executor with correct parameters."""
        await runner.run()

        mock_executor.execute.assert_called_once_with(
            limit=None,
            query=None,
        )

    @pytest.mark.asyncio
    async def test_run_passes_limit_to_executor(
        self,
        pipeline_config,
        mock_services,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
    ):
        """Test run passes limit to executor."""
        runtime_with_limit = RuntimeConfig(
            run_type=RunType.INCREMENTAL,
            limit=500,
        )
        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_with_limit,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await runner.run()

        mock_executor.execute.assert_called_once()
        call_kwargs = mock_executor.execute.call_args.kwargs
        assert call_kwargs["limit"] == 500


@pytest.mark.unit
class TestPipelineRunnerClearViaLifecycle:
    """Tests for PipelineRunner._clear_via_lifecycle method with lifecycle service."""

    @pytest.mark.asyncio
    async def test_clear_via_lifecycle_uses_service(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_via_lifecycle uses injected lifecycle service."""
        from bioetl.application.services.medallion_lifecycle import (
            ClearResult,
            MedallionLifecycleService,
        )

        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = create_mock_services()

        # Mock lifecycle service
        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.clear = AsyncMock(
            return_value=ClearResult(silver_cleared=5, gold_cleared=3, dry_run=False)
        )

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=lifecycle_service,
        )

        await runner._clear_via_lifecycle()

        # Should use lifecycle service
        lifecycle_service.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_via_lifecycle_skips_for_incremental(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_via_lifecycle skips for incremental runs."""
        from bioetl.application.services.medallion_lifecycle import (
            MedallionLifecycleService,
        )

        incremental_runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)

        services = create_mock_services()

        lifecycle_service = MagicMock(spec=MedallionLifecycleService)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=incremental_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=lifecycle_service,
        )

        await runner._clear_via_lifecycle()

        # Should not call lifecycle service for incremental
        lifecycle_service.clear.assert_not_called()


@pytest.mark.unit
class TestPipelineRunnerCheckDataQuality:
    """Tests for PipelineRunner._check_data_quality method."""

    @pytest.fixture
    def mock_dq_monitor(self):
        """Create a mock DQ monitor."""
        monitor = MagicMock()
        monitor.check_quality = MagicMock(return_value=[])
        monitor.update_baseline_from_metrics = MagicMock()
        monitor.get_baseline_stats = MagicMock(return_value=None)
        return monitor

    @pytest.mark.asyncio
    async def test_check_data_quality_skips_without_monitor(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
    ):
        """Test _check_data_quality skips when dq_monitor is None."""
        services = create_mock_services()
        services.dq_monitor = None

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        # Should not raise and should return early
        await runner._check_data_quality()

        # No metrics should be recorded for dq_check
        dq_calls = [
            c
            for c in services.metrics.observe_histogram.call_args_list
            if "dq_check" in str(c)
        ]
        assert len(dq_calls) == 0

    @pytest.mark.asyncio
    async def test_check_data_quality_no_anomalies(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
        mock_dq_monitor,
    ):
        """Test _check_data_quality with no anomalies detected."""
        services = create_mock_services()
        services.dq_monitor = mock_dq_monitor

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await runner._check_data_quality()

        # Should call check_quality with batch metrics
        mock_dq_monitor.check_quality.assert_called_once()

        # Should update baseline
        mock_dq_monitor.update_baseline_from_metrics.assert_called_once()

        # Should not log warning (no anomalies)
        warning_calls = list(mock_logger.warning.call_args_list)
        dq_warnings = [c for c in warning_calls if "dq_anomaly" in str(c)]
        assert len(dq_warnings) == 0

    @pytest.mark.asyncio
    async def test_check_data_quality_logs_anomalies(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
        mock_dq_monitor,
    ):
        """Test _check_data_quality logs detected anomalies."""
        from datetime import UTC, datetime

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

        mock_dq_monitor.check_quality.return_value = [anomaly]

        services = create_mock_services()
        services.dq_monitor = mock_dq_monitor

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await runner._check_data_quality()

        # Should log warning
        mock_logger.warning.assert_called()
        call_kwargs = mock_logger.warning.call_args.kwargs
        assert call_kwargs.get("severity") == "high"
        assert call_kwargs.get("metric") == "error_rate"

    @pytest.mark.asyncio
    async def test_check_data_quality_publishes_metrics(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
        mock_dq_monitor,
    ):
        """Test _check_data_quality publishes Prometheus metrics."""
        from datetime import UTC, datetime

        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        anomaly = Anomaly(
            metric_name="record_count",
            current_value=100,
            baseline_mean=1000,
            baseline_stddev=50,
            anomaly_type=AnomalyType.DROP,
            severity=AnomalySeverity.CRITICAL,
            z_score=18.0,
            timestamp=datetime.now(UTC),
            message="Record count drop",
        )

        mock_dq_monitor.check_quality.return_value = [anomaly]

        services = create_mock_services()
        services.dq_monitor = mock_dq_monitor

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await runner._check_data_quality()

        # Should increment counter
        counter_calls = [
            c
            for c in services.metrics.increment_counter.call_args_list
            if c[0][0] == "dq_anomaly_detected"
        ]
        assert len(counter_calls) == 1

    @pytest.mark.asyncio
    async def test_check_data_quality_logs_critical_at_error_level(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_lifecycle_service,
        mock_dq_monitor,
    ):
        """Test _check_data_quality logs critical anomalies at error level."""
        from datetime import UTC, datetime

        from bioetl.infrastructure.observability.anomaly.types import (
            Anomaly,
            AnomalySeverity,
            AnomalyType,
        )

        anomaly = Anomaly(
            metric_name="error_rate",
            current_value=0.50,
            baseline_mean=0.05,
            baseline_stddev=0.02,
            anomaly_type=AnomalyType.THRESHOLD_EXCEEDED,
            severity=AnomalySeverity.CRITICAL,
            z_score=22.5,
            timestamp=datetime.now(UTC),
            message="Error rate exceeds threshold",
        )

        mock_dq_monitor.check_quality.return_value = [anomaly]

        services = create_mock_services()
        services.dq_monitor = mock_dq_monitor

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await runner._check_data_quality()

        # Should log at error level for critical
        mock_logger.error.assert_called()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "critical_dq_anomaly"
