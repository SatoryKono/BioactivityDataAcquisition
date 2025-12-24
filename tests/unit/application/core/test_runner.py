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


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.lock = AsyncMock()
    services.lock.acquire = AsyncMock(return_value=True)
    services.lock.release = AsyncMock()
    services.lock.heartbeat = AsyncMock(return_value=True)
    services.metrics = MagicMock()
    services.metrics.observe_histogram = MagicMock()
    services.metrics.increment_counter = MagicMock()
    # Storage with clear methods (part of StoragePort contract)
    services.storage = MagicMock()
    services.storage.clear_silver = AsyncMock(return_value=0)
    services.storage.clear_gold = AsyncMock(return_value=0)
    return services


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
        )

        assert runner._config == pipeline_config
        assert runner._runtime == runtime_config
        assert runner.shutdown_signal == shutdown_signal

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

        mock_services.metrics.observe_histogram.assert_called_once()
        call_args = mock_services.metrics.observe_histogram.call_args
        assert call_args[0][0] == "bioetl_pipeline_duration_seconds"

    @pytest.mark.asyncio
    async def test_run_records_metrics_on_failure(
        self, runner, mock_services, mock_executor
    ):
        """Test metrics are recorded even on failure."""
        mock_executor.execute.side_effect = RuntimeError("Error")

        with pytest.raises(RuntimeError):
            await runner.run()

        mock_services.metrics.observe_histogram.assert_called_once()
        call_args = mock_services.metrics.observe_histogram.call_args
        labels = call_args[1].get("labels") or call_args[0][2]
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
            pipeline=None,
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

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()

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

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()

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

    @pytest.mark.asyncio
    async def test_clear_via_lifecycle_falls_back_to_legacy(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_via_lifecycle falls back to legacy when no service."""
        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=5)
        services.storage.clear_gold = AsyncMock(return_value=3)

        # No lifecycle service injected
        runner = PipelineRunner(
            config=pipeline_config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            lifecycle_service=None,
        )

        await runner._clear_via_lifecycle()

        # Should fall back to calling storage directly
        services.storage.clear_silver.assert_called_once()
        services.storage.clear_gold.assert_called_once()


@pytest.mark.unit
class TestPipelineRunnerClearExportsLegacy:
    """Tests for PipelineRunner._clear_exports_legacy method."""

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_calls_storage_methods(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy calls storage clear methods for REBUILD run."""
        # Use REBUILD run type to trigger clearing
        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        # Create services with storage that has clear methods
        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=5)
        services.storage.clear_gold = AsyncMock(return_value=1)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should clear both silver and gold tables
        services.storage.clear_silver.assert_called_once()
        services.storage.clear_gold.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_logs_when_files_cleared(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy logs when files are cleared."""
        # Use REBUILD run type to trigger clearing
        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=3)
        services.storage.clear_gold = AsyncMock(return_value=2)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should log when files are cleared
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("Cleared storage" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_no_log_when_nothing_cleared(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy does not log when nothing cleared."""
        # Use REBUILD run type to trigger clearing logic
        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=0)
        services.storage.clear_gold = AsyncMock(return_value=0)

        mock_logger.reset_mock()

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should not log about cleared files when nothing was cleared
        info_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert not any("Cleared storage" in call for call in info_calls)

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_uses_default_gold_table(
        self,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy uses default gold table name when not specified."""
        # Use REBUILD run type to trigger clearing
        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        # Config without explicit gold_table
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="chembl.silver_activity",
            gold_table=None,  # No explicit gold table
        )

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=0)
        services.storage.clear_gold = AsyncMock(return_value=0)

        runner = PipelineRunner(
            config=config,
            runtime=rebuild_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should use default gold table: provider.entity_type
        services.storage.clear_silver.assert_called_once_with(
            "chembl.silver_activity", dry_run=False
        )
        services.storage.clear_gold.assert_called_once_with(
            "chembl.activity", dry_run=False
        )

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_skips_for_incremental(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy does NOT clear storage for INCREMENTAL run."""
        # Use INCREMENTAL run type - should skip clearing
        incremental_runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=0)
        services.storage.clear_gold = AsyncMock(return_value=0)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=incremental_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should NOT call clear methods for incremental run
        services.storage.clear_silver.assert_not_called()
        services.storage.clear_gold.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear_exports_legacy_dry_run_mode(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_exports_legacy passes dry_run=True to storage methods."""
        # Use REBUILD with dry_run=True
        dry_run_runtime = RuntimeConfig(
            run_type=RunType.REBUILD, limit=None, dry_run=True
        )

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=5)
        services.storage.clear_gold = AsyncMock(return_value=2)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=dry_run_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )

        await runner._clear_exports_legacy()

        # Should pass dry_run=True to storage methods
        services.storage.clear_silver.assert_called_once_with(
            pipeline_config.silver_table, dry_run=True
        )
        services.storage.clear_gold.assert_called_once()


@pytest.mark.unit
class TestPipelineRunnerClearViaCleanupService:
    """Tests for PipelineRunner._clear_via_cleanup_service method."""

    @pytest.mark.asyncio
    async def test_clear_via_cleanup_service_uses_service(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test _clear_via_lifecycle uses cleanup service when injected."""
        from bioetl.application.core.cleanup_service import CleanupResult, CleanupService

        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()

        # Mock cleanup service
        cleanup_service = MagicMock(spec=CleanupService)
        cleanup_service.execute = AsyncMock(
            return_value=CleanupResult(silver_cleared=5, gold_cleared=3, dry_run=False)
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
            cleanup_service=cleanup_service,
        )

        await runner._clear_via_lifecycle()

        # Should use cleanup service
        cleanup_service.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_service_priority_over_legacy(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test cleanup service is used over legacy when no lifecycle service."""
        from bioetl.application.core.cleanup_service import CleanupResult, CleanupService

        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()
        services.storage = MagicMock()
        services.storage.clear_silver = AsyncMock(return_value=0)
        services.storage.clear_gold = AsyncMock(return_value=0)

        # Mock cleanup service (no lifecycle service)
        cleanup_service = MagicMock(spec=CleanupService)
        cleanup_service.execute = AsyncMock(
            return_value=CleanupResult(silver_cleared=5, gold_cleared=3, dry_run=False)
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
            lifecycle_service=None,  # No lifecycle service
            cleanup_service=cleanup_service,
        )

        await runner._clear_via_lifecycle()

        # Should use cleanup service, not storage directly
        cleanup_service.execute.assert_called_once()
        services.storage.clear_silver.assert_not_called()
        services.storage.clear_gold.assert_not_called()

    @pytest.mark.asyncio
    async def test_lifecycle_service_priority_over_cleanup(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test lifecycle service is used over cleanup service when both present."""
        from bioetl.application.core.cleanup_service import CleanupResult, CleanupService
        from bioetl.application.services.medallion_lifecycle import (
            ClearResult,
            MedallionLifecycleService,
        )

        rebuild_runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()

        # Mock both services
        lifecycle_service = MagicMock(spec=MedallionLifecycleService)
        lifecycle_service.clear = AsyncMock(
            return_value=ClearResult(silver_cleared=10, gold_cleared=5, dry_run=False)
        )

        cleanup_service = MagicMock(spec=CleanupService)
        cleanup_service.execute = AsyncMock(
            return_value=CleanupResult(silver_cleared=5, gold_cleared=3, dry_run=False)
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
            cleanup_service=cleanup_service,
        )

        await runner._clear_via_lifecycle()

        # Should use lifecycle service (higher priority)
        lifecycle_service.clear.assert_called_once()
        cleanup_service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_service_skips_for_incremental(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test cleanup service is not called for incremental runs."""
        from bioetl.application.core.cleanup_service import CleanupService

        incremental_runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()

        cleanup_service = MagicMock(spec=CleanupService)

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=incremental_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            cleanup_service=cleanup_service,
        )

        await runner._clear_via_lifecycle()

        # Should not call cleanup service for incremental
        cleanup_service.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_service_passes_dry_run(
        self,
        pipeline_config,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
        mock_lock_manager,
    ):
        """Test cleanup service receives dry_run flag."""
        from bioetl.application.core.cleanup_service import CleanupResult, CleanupService

        dry_run_runtime = RuntimeConfig(
            run_type=RunType.REBUILD, limit=None, dry_run=True
        )

        services = MagicMock(spec=PipelineServices)
        services.lock = AsyncMock()
        services.metrics = MagicMock()

        cleanup_service = MagicMock(spec=CleanupService)
        cleanup_service.execute = AsyncMock(
            return_value=CleanupResult(silver_cleared=5, gold_cleared=3, dry_run=True)
        )

        runner = PipelineRunner(
            config=pipeline_config,
            runtime=dry_run_runtime,
            services=services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
            cleanup_service=cleanup_service,
        )

        await runner._clear_via_lifecycle()

        # Should pass dry_run=True
        cleanup_service.execute.assert_called_once()
        call_kwargs = cleanup_service.execute.call_args.kwargs
        assert call_kwargs["dry_run"] is True
