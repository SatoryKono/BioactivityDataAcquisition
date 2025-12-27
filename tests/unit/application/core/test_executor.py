"""Unit tests for PipelineExecutor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.memory_manager import MemoryConfig, MemoryManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import BatchResult, RecordProcessor
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal


@pytest.fixture
def mock_services():
    """Create mock pipeline services."""
    services = MagicMock(spec=PipelineServices)
    services.data_source = AsyncMock()
    return services


@pytest.fixture
def mock_record_processor():
    """Create mock record processor."""
    processor = MagicMock(spec=RecordProcessor)
    processor.process_batch = AsyncMock(
        return_value=BatchResult(
            bronze_count=0, silver_count=0, gold_count=0, quarantined_count=0
        )
    )
    return processor


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    manager = MagicMock(spec=CheckpointManager)
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def shutdown_signal():
    """Create shutdown signal."""
    return ShutdownSignal()


@pytest.fixture
def executor(
    mock_services,
    mock_record_processor,
    mock_checkpoint_manager,
    shutdown_signal,
):
    """Create PipelineExecutor instance."""
    return PipelineExecutor(
        services=mock_services,
        record_processor=mock_record_processor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=shutdown_signal,
        entity_type="test_entity",
        batch_size=10,
        checkpoint_interval=5,
    )


@pytest.mark.unit
class TestPipelineExecutorInit:
    """Tests for PipelineExecutor initialization."""

    def test_init_stores_batch_size(self, executor):
        """Test that initialization stores batch size."""
        assert executor.batch_size == 10

    def test_init_stores_checkpoint_interval(self, executor):
        """Test that initialization stores checkpoint interval."""
        assert executor.checkpoint_interval == 5

    def test_init_default_batch_size(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test default batch size when not specified."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test",
        )
        assert executor.batch_size == PipelineExecutor.DEFAULT_BATCH_SIZE

    def test_init_counters_zero(self, executor):
        """Test that counters start at zero."""
        assert executor.records_fetched == 0
        assert executor.records_bronze == 0
        assert executor.records_silver == 0
        assert executor.records_gold == 0
        assert executor.records_quarantined == 0


@pytest.mark.unit
class TestPipelineExecutorExecute:
    """Tests for execute method."""

    async def test_execute_processes_records(
        self, executor, mock_services, mock_record_processor
    ):
        """Test that execute processes records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch
        mock_record_processor.process_batch.return_value = BatchResult(
            bronze_count=3, silver_count=3, gold_count=3, quarantined_count=0
        )

        await executor.execute(limit=None)

        assert executor.records_fetched == 3
        assert executor.records_bronze == 3
        assert executor.records_silver == 3
        assert executor.records_gold == 3
        mock_record_processor.process_batch.assert_called()

    async def test_execute_batches_records(
        self, executor, mock_services, mock_record_processor
    ):
        """Test that execute batches records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(15):  # More than batch size of 10
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # Should have called process_batch twice (batch of 10 + batch of 5)
        assert mock_record_processor.process_batch.call_count == 2

    async def test_execute_checkpoints_at_interval(
        self, executor, mock_services, mock_checkpoint_manager
    ):
        """Test that execute checkpoints at configured interval."""

        async def mock_fetch(**kwargs):
            for i in range(10):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        # With checkpoint_interval=5, should checkpoint at record 5 and 10
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2

    async def test_execute_handles_shutdown(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown saves checkpoint."""
        records_yielded = 0

        async def mock_fetch(**kwargs):
            nonlocal records_yielded
            for i in range(10):
                yield {"id": str(i), "value": 10}
                records_yielded += 1
                if records_yielded == 3:
                    # Trigger shutdown after 3 records
                    shutdown_signal.request()

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(limit=None)

        # Should have saved checkpoint before shutdown
        mock_checkpoint_manager.save_checkpoint.assert_called()

    async def test_execute_shutdown_early(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown at start of processing."""

        async def mock_fetch(**kwargs):
            shutdown_signal.request()
            yield {"id": "0", "value": 10}

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(limit=None)

    async def test_execute_empty_data(
        self, executor, mock_services, mock_record_processor
    ):
        """Test execute with no data."""

        async def mock_fetch(**kwargs):
            if False:  # Empty generator
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=None)

        assert executor.records_fetched == 0
        mock_record_processor.process_batch.assert_not_called()

    async def test_execute_passes_limit(self, executor, mock_services):
        """Test that limit is passed to data source."""
        captured_kwargs = {}

        async def mock_fetch(**kwargs):
            captured_kwargs.update(kwargs)
            if False:
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(limit=100)

        assert captured_kwargs.get("limit") == 100


@pytest.mark.unit
class TestPipelineExecutorMemoryManagement:
    """Tests for memory management features."""

    def test_memory_manager_property(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that memory_manager property is accessible."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
        )

        assert isinstance(executor.memory_manager, MemoryManager)

    def test_custom_memory_config(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that custom memory config is applied."""
        config = MemoryConfig(max_batch_memory_mb=1024, enabled=False)
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            memory_config=config,
        )

        assert executor.memory_manager.config.max_batch_memory_mb == 1024
        assert executor.memory_manager.is_enabled is False

    def test_base_batch_size_stored(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that base batch size is stored for recovery."""
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=200,
        )

        assert executor._base_batch_size == 200
        assert executor.batch_size == 200

    def test_memory_management_disabled_by_default_keeps_batch_size(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that memory management respects enabled flag."""
        config = MemoryConfig(enabled=False)
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=100,
            memory_config=config,
        )

        # When disabled, batch size should remain constant
        recommended = executor.memory_manager.get_recommended_batch_size(100)
        assert recommended == 100

    async def test_adaptive_batch_size_updates_during_execution(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that batch size can be updated during execution."""
        # Use enabled memory config
        config = MemoryConfig(enabled=True, max_batch_memory_mb=10000)
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            batch_size=10,
            memory_config=config,
        )

        async def mock_fetch(**kwargs):
            for i in range(25):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch
        mock_record_processor.process_batch.return_value = BatchResult(
            bronze_count=10, silver_count=10, gold_count=10, quarantined_count=0
        )

        await executor.execute(limit=None)

        # Should have processed all records
        assert executor.records_fetched == 25


@pytest.mark.unit
class TestPipelineExecutorWithLogger:
    """Tests for executor with logger integration."""

    def test_logger_passed_to_memory_manager(
        self,
        mock_services,
        mock_record_processor,
        mock_checkpoint_manager,
        shutdown_signal,
    ):
        """Test that logger is passed to memory manager."""
        mock_logger = MagicMock()
        executor = PipelineExecutor(
            services=mock_services,
            record_processor=mock_record_processor,
            checkpoint_manager=mock_checkpoint_manager,
            shutdown_signal=shutdown_signal,
            entity_type="test_entity",
            logger=mock_logger,
        )

        assert executor.memory_manager._logger is mock_logger
