"""Unit tests for the PipelineOrchestrator class."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.orchestrator import PipelineOrchestrator
from bioetl.application.core.pipeline_config import (
    PipelineConfig,
    PipelineRuntimeConfig,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


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
        pipeline_name="test_pipeline",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="test_silver",
    )


@pytest.fixture
def runtime_config():
    """Create a runtime config."""
    return PipelineRuntimeConfig(
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
    return services


@pytest.fixture
def mock_context(mock_logger):
    """Create a mock pipeline context."""
    return PipelineContext(
        run_id=RunID(uuid4()),
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
def orchestrator(
    pipeline_config,
    runtime_config,
    mock_services,
    mock_context,
    mock_executor,
    mock_checkpoint_manager,
    shutdown_signal,
    mock_logger,
):
    """Create a PipelineOrchestrator instance."""
    return PipelineOrchestrator(
        config=pipeline_config,
        runtime=runtime_config,
        services=mock_services,
        context=mock_context,
        executor=mock_executor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        logger=mock_logger,
        heartbeat_interval=0.1,
    )


@pytest.mark.unit
class TestPipelineOrchestrator:
    """Tests for PipelineOrchestrator."""

    def test_initialization(self, orchestrator, pipeline_config):
        """Test orchestrator initializes correctly."""
        assert orchestrator._config == pipeline_config
        assert orchestrator.heartbeat_task is None

    def test_from_components_factory(
        self,
        pipeline_config,
        runtime_config,
        mock_services,
        mock_context,
        mock_executor,
        mock_checkpoint_manager,
        shutdown_signal,
        mock_logger,
    ):
        """Test from_components factory method."""
        orch = PipelineOrchestrator.from_components(
            config=pipeline_config,
            runtime=runtime_config,
            services=mock_services,
            context=mock_context,
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            logger=mock_logger,
        )
        assert orch._config == pipeline_config
        assert orch._runtime == runtime_config

    def test_shutdown_requested_property(self, orchestrator, shutdown_signal):
        """Test shutdown_requested property."""
        assert orchestrator.shutdown_requested is False
        shutdown_signal.request()
        assert orchestrator.shutdown_requested is True

    async def test_run_success(self, orchestrator, mock_services, mock_executor):
        """Test successful pipeline run."""
        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        mock_services.lock.acquire.assert_called_once()
        mock_executor.execute.assert_called_once()
        mock_services.lock.release.assert_called_once()
        mock_services.metrics.observe_histogram.assert_called()

    async def test_run_lock_acquisition_failure(
        self, orchestrator, mock_services, mock_logger
    ):
        """Test pipeline run when lock acquisition fails."""
        mock_services.lock.acquire.return_value = False

        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        mock_logger.error.assert_called()
        # Executor should not be called if lock fails
        orchestrator._executor.execute.assert_not_called()

    async def test_run_exclusive_lock_for_backfill(
        self, orchestrator, mock_services, runtime_config
    ):
        """Test that backfill acquires exclusive lock."""
        orchestrator._runtime = PipelineRuntimeConfig(
            run_type=RunType.BACKFILL, limit=None
        )

        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        mock_services.lock.acquire.assert_called_once()
        call_kwargs = mock_services.lock.acquire.call_args.kwargs
        assert call_kwargs["exclusive"] is True

    async def test_run_exclusive_lock_for_rebuild(
        self, orchestrator, mock_services, runtime_config
    ):
        """Test that rebuild acquires exclusive lock."""
        orchestrator._runtime = PipelineRuntimeConfig(
            run_type=RunType.REBUILD, limit=None
        )

        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        call_kwargs = mock_services.lock.acquire.call_args.kwargs
        assert call_kwargs["exclusive"] is True

    async def test_run_shared_lock_for_incremental(self, orchestrator, mock_services):
        """Test that incremental acquires shared lock."""
        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        call_kwargs = mock_services.lock.acquire.call_args.kwargs
        assert call_kwargs["exclusive"] is False

    async def test_run_with_shutdown_error(
        self, orchestrator, mock_executor, mock_logger
    ):
        """Test pipeline run with shutdown error."""
        mock_executor.execute.side_effect = PipelineShutdownError("Shutdown requested")

        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            with pytest.raises(PipelineShutdownError):
                await orchestrator.run()

        mock_logger.warning.assert_called()

    async def test_run_with_general_exception(
        self, orchestrator, mock_executor, mock_logger
    ):
        """Test pipeline run with general exception."""
        mock_executor.execute.side_effect = RuntimeError("Test error")

        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            with pytest.raises(RuntimeError):
                await orchestrator.run()

        mock_logger.error.assert_called()

    async def test_heartbeat_task_created_and_cancelled(
        self, orchestrator, mock_services
    ):
        """Test heartbeat task is created and cancelled on completion."""
        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        # Heartbeat task should have been created and then cancelled
        assert orchestrator.heartbeat_task is not None

    async def test_heartbeat_loop_stops_on_shutdown(
        self, orchestrator, shutdown_signal
    ):
        """Test heartbeat loop stops when shutdown is requested."""
        shutdown_signal.request()

        # Should return immediately when shutdown is requested
        await orchestrator._heartbeat_loop("test_key", exclusive=False)

    async def test_heartbeat_loop_requests_shutdown_on_lock_lost(
        self, orchestrator, mock_services, shutdown_signal
    ):
        """Test heartbeat loop requests shutdown when lock is lost."""
        mock_services.lock.heartbeat.return_value = False

        with pytest.raises(PipelineShutdownError):
            await orchestrator._heartbeat_loop("test_key", exclusive=False)

        assert shutdown_signal.is_requested

    async def test_metrics_recorded_on_completion(
        self, orchestrator, mock_services, mock_executor
    ):
        """Test metrics are recorded after pipeline completion."""
        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        mock_services.metrics.observe_histogram.assert_called_once()
        # Check increment_counter called for bronze, silver, gold
        assert mock_services.metrics.increment_counter.call_count == 3

    async def test_checkpoint_deleted_on_success(
        self, orchestrator, mock_checkpoint_manager
    ):
        """Test checkpoint is deleted after successful run."""
        with patch.object(orchestrator, "_setup_shutdown_handlers"):
            await orchestrator.run()

        mock_checkpoint_manager.delete_checkpoint.assert_called_once()

    def test_setup_shutdown_handlers(self, orchestrator):
        """Test signal handlers are set up."""
        import signal

        with patch.object(signal, "signal") as mock_signal:
            orchestrator._setup_shutdown_handlers()

            assert mock_signal.call_count == 2
            calls = [call[0][0] for call in mock_signal.call_args_list]
            assert signal.SIGTERM in calls
            assert signal.SIGINT in calls
