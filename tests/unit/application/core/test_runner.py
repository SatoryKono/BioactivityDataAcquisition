"""Unit tests for the PipelineRunner class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.services.medallion_lifecycle import (
    MedallionLifecycleService,
    PrepareResult,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.postrun_service import PostrunService
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.application.observability.observer import PipelineObserver
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
    """Create a mock LockManager instance (injected via DI)."""
    lock_manager = MagicMock(spec=LockManager)
    lock_manager.__aenter__ = AsyncMock(return_value=lock_manager)
    lock_manager.__aexit__ = AsyncMock(return_value=None)
    return lock_manager


@pytest.fixture
def mock_preflight_service():
    """Create a mock PreflightService (injected via DI)."""
    from bioetl.domain.types import HealthReport

    service = MagicMock(spec=PreflightService)
    service.validate_infrastructure = AsyncMock(return_value=HealthReport(results=[]))
    return service


@pytest.fixture
def mock_postrun_service():
    """Create a mock PostrunService (injected via DI)."""
    from bioetl.application.core.postrun_service import DQResult, DQStatus, VacuumResult

    service = MagicMock(spec=PostrunService)
    service.run_dq_checks = AsyncMock(
        return_value=DQResult(
            error_rate=0.0,
            status=DQStatus.PASSED,
            anomalies=(),
            has_critical=False,
            check_duration_ms=0.0,
        )
    )
    service.run_vacuum_if_enabled = AsyncMock(
        return_value=VacuumResult(
            silver_files_removed=0, gold_files_removed=0, skipped=True
        )
    )
    service.cleanup = AsyncMock()
    return service


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock MedallionLifecycleService (injected via DI)."""
    from bioetl.application.services.medallion_lifecycle import (
        ClearResult,
        VacuumResult,
    )
    from bioetl.domain.medallion import MedallionPolicy
    from bioetl.domain.types import RunType

    service = MagicMock(spec=MedallionLifecycleService)
    service.prepare_for_run = AsyncMock(
        return_value=PrepareResult(
            clear_result=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False),
            policy=MedallionPolicy.for_run_type(RunType.INCREMENTAL),
        )
    )
    service.finalize_run = AsyncMock(
        return_value=VacuumResult(silver_files_removed=0, gold_files_removed=0, skipped=True)
    )
    service.clear = AsyncMock(
        return_value=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False)
    )
    return service


@pytest.fixture
def mock_observer(mock_services, mock_logger):
    """Create a mock PipelineObserver that delegates to real observer behavior.

    This mock properly handles context manager protocol and calls
    metrics/logger as the real observer would.
    """
    from bioetl.application.core.shutdown import PipelineShutdownError

    observer = MagicMock(spec=PipelineObserver)

    # Track enter/exit state
    observer._entered = False

    def enter_side_effect():
        observer._entered = True
        # Simulate observer logging start
        mock_logger.info("pipeline_started", run_type="incremental")
        return observer

    def exit_side_effect(exc_type, exc_val, exc_tb):
        # Simulate observer logging completion and recording metrics
        duration = 0.1  # Simulated duration
        status = "success"
        suppress_exception = False

        if exc_val:
            if isinstance(exc_val, PipelineShutdownError):
                status = "shutdown"
                suppress_exception = True
            else:
                status = "failed"
                mock_logger.error("pipeline_failed", error=str(exc_val))

        # Record metrics like the real observer
        mock_services.metrics.observe_histogram(
            "bioetl_pipeline_duration_seconds",
            duration,
            labels={
                "pipeline": "test_runner_pipeline",
                "run_type": "incremental",
                "status": status,
            },
        )
        mock_services.metrics.increment_counter(
            "bioetl_pipeline_runs_total",
            1,
            labels={
                "pipeline": "test_runner_pipeline",
                "run_type": "incremental",
                "status": status,
            },
        )

        if status == "success":
            mock_logger.info("pipeline_finished", status=status)
        elif status == "shutdown":
            mock_logger.warning("pipeline_shutdown", status=status)

        return suppress_exception

    observer.__enter__ = MagicMock(side_effect=enter_side_effect)
    observer.__exit__ = MagicMock(side_effect=exit_side_effect)

    return observer


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
    mock_preflight_service,
    mock_postrun_service,
    mock_lifecycle_service,
    mock_observer,
):
    """Create a PipelineRunner instance with directly injected services (DI pattern)."""
    return PipelineRunner(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=mock_context,
        executor=mock_executor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        logger=mock_logger,
        lock_manager=mock_lock_manager,
        preflight=mock_preflight_service,
        postrun=mock_postrun_service,
        lifecycle_service=mock_lifecycle_service,
        observer=mock_observer,
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
        mock_preflight_service,
        mock_postrun_service,
        mock_lifecycle_service,
        mock_observer,
    ):
        """Test runner initializes correctly with directly injected services."""
        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
        )

        assert runner._config == pipeline_config
        assert runner._runtime == runtime_config
        assert runner.shutdown_signal == shutdown_signal
        # Verify services are stored directly
        assert runner._lock_manager == mock_lock_manager
        assert runner._preflight_service == mock_preflight_service
        assert runner._postrun_service == mock_postrun_service
        assert runner._lifecycle_service == mock_lifecycle_service
        assert runner._observer == mock_observer

    def test_services_are_injected_not_created(
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
        mock_preflight_service,
        mock_postrun_service,
        mock_lifecycle_service,
        mock_observer,
    ):
        """Test services are injected via DI, not created internally."""
        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
        )

        # The exact same instances should be used (DI)
        assert runner._lock_manager is mock_lock_manager
        assert runner._preflight_service is mock_preflight_service
        assert runner._postrun_service is mock_postrun_service
        assert runner._lifecycle_service is mock_lifecycle_service
        assert runner._observer is mock_observer


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
        """Test run logs start message using PipelineEvent.START constant."""
        await runner.run()

        mock_logger.info.assert_called()
        calls = [str(call) for call in mock_logger.info.call_args_list]
        # Runner now uses PipelineEvent.START = "pipeline_started"
        assert any("pipeline_started" in call for call in calls)

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
        mock_preflight_service,
        mock_postrun_service,
        mock_lifecycle_service,
        mock_observer,
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
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
        )

        await runner.run()

        mock_executor.execute.assert_called_once()
        call_kwargs = mock_executor.execute.call_args.kwargs
        assert call_kwargs["limit"] == 500


@pytest.mark.unit
class TestPipelineRunnerClearViaLifecycle:
    """Tests for PipelineRunner._prepare_medallion_layers method with MedallionLifecycleService.

    Verifies delegation pattern: PipelineRunner delegates to MedallionLifecycleService.
    The service handles MedallionPolicy and clear operations.
    """

    @pytest.mark.asyncio
    async def test_prepare_medallion_layers_delegates_to_lifecycle_service(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_preflight_service,
        mock_postrun_service,
    ):
        """Test _prepare_medallion_layers delegates to lifecycle service."""
        from bioetl.application.services.medallion_lifecycle import (
            ClearResult,
        )
        from bioetl.domain.medallion import MedallionPolicy

        services = create_mock_services()

        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.prepare_for_run = AsyncMock(
            return_value=PrepareResult(
                clear_result=ClearResult(silver_cleared=5, gold_cleared=3, dry_run=False),
                policy=MedallionPolicy.for_run_type(RunType.REBUILD),
            )
        )

        mock_observer = MagicMock(spec=PipelineObserver)
        mock_observer.__enter__ = MagicMock(return_value=mock_observer)
        mock_observer.__exit__ = MagicMock(return_value=None)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=lifecycle_service,
            observer=mock_observer,
        )

        await runner._prepare_medallion_layers()

        lifecycle_service.prepare_for_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_prepare_medallion_layers_is_called_during_run(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_preflight_service,
        mock_postrun_service,
    ):
        """Test _prepare_medallion_layers is called as part of run() execution."""
        from bioetl.application.services.medallion_lifecycle import (
            ClearResult,
            VacuumResult,
        )
        from bioetl.domain.medallion import MedallionPolicy

        services = create_mock_services()

        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.prepare_for_run = AsyncMock(
            return_value=PrepareResult(
                clear_result=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False),
                policy=MedallionPolicy.for_run_type(RunType.INCREMENTAL),
            )
        )
        lifecycle_service.finalize_run = AsyncMock(
            return_value=VacuumResult(silver_files_removed=0, gold_files_removed=0, skipped=True)
        )

        mock_observer = MagicMock(spec=PipelineObserver)
        mock_observer.__enter__ = MagicMock(return_value=mock_observer)
        mock_observer.__exit__ = MagicMock(return_value=None)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=mock_postrun_service,
            lifecycle_service=lifecycle_service,
            observer=mock_observer,
        )

        await runner.run()

        # Lifecycle service should be called during run()
        lifecycle_service.prepare_for_run.assert_called_once()


@pytest.mark.unit
class TestPipelineRunnerCheckDataQuality:
    """Tests for PipelineRunner._check_data_quality method.

    Note: _check_data_quality delegates to PostrunService.run_dq_checks().
    These tests verify the delegation behavior.
    """

    @pytest.fixture
    def mock_dq_monitor(self):
        """Create a mock DQ monitor."""
        monitor = MagicMock()
        monitor.check_quality = MagicMock(return_value=[])
        monitor.update_baseline_from_metrics = MagicMock()
        monitor.get_baseline_stats = MagicMock(return_value=None)
        return monitor

    @pytest.mark.asyncio
    async def test_check_data_quality_delegates_to_postrun_service(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_preflight_service,
        mock_lifecycle_service,
    ):
        """Test _check_data_quality delegates to PostrunService."""
        from bioetl.application.core.postrun_service import DQResult, DQStatus, VacuumResult

        services = create_mock_services()

        postrun_service = MagicMock(spec=PostrunService)
        postrun_service.run_dq_checks = AsyncMock(
            return_value=DQResult(
                error_rate=0.0,
                status=DQStatus.PASSED,
                anomalies=(),
                has_critical=False,
                check_duration_ms=5.0,
            )
        )
        postrun_service.run_vacuum_if_enabled = AsyncMock(
            return_value=VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )
        )
        postrun_service.cleanup = AsyncMock()

        mock_observer = MagicMock(spec=PipelineObserver)
        mock_observer.__enter__ = MagicMock(return_value=mock_observer)
        mock_observer.__exit__ = MagicMock(return_value=None)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
        )

        await runner._check_data_quality()

        # Should delegate to postrun service
        postrun_service.run_dq_checks.assert_called_once_with(mock_executor)

    @pytest.mark.asyncio
    async def test_check_data_quality_is_called_during_run(
        self,
        pipeline_config,
        runtime_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
        mock_preflight_service,
        mock_lifecycle_service,
    ):
        """Test _check_data_quality is invoked during run()."""
        from bioetl.application.core.postrun_service import DQResult, DQStatus, VacuumResult

        services = create_mock_services()

        postrun_service = MagicMock(spec=PostrunService)
        postrun_service.run_dq_checks = AsyncMock(
            return_value=DQResult(
                error_rate=0.0,
                status=DQStatus.PASSED,
                anomalies=(),
                has_critical=False,
                check_duration_ms=0.0,
            )
        )
        postrun_service.run_vacuum_if_enabled = AsyncMock(
            return_value=VacuumResult(
                silver_files_removed=0, gold_files_removed=0, skipped=True
            )
        )
        postrun_service.cleanup = AsyncMock()

        mock_observer = MagicMock(spec=PipelineObserver)
        mock_observer.__enter__ = MagicMock(return_value=mock_observer)
        mock_observer.__exit__ = MagicMock(return_value=None)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=runtime_config,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lock_manager=mock_lock_manager,
            preflight=mock_preflight_service,
            postrun=postrun_service,
            lifecycle_service=mock_lifecycle_service,
            observer=mock_observer,
        )

        await runner.run()

        # PostrunService.run_dq_checks should be called during run()
        postrun_service.run_dq_checks.assert_called_once()
