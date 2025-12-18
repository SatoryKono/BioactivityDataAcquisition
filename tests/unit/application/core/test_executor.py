"""Unit tests for PipelineExecutor."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
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
    processor.process_batch = AsyncMock(return_value=(0, 0, 0, 0))
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

    async def test_execute_processes_records(self, executor, mock_services, mock_record_processor):
        """Test that execute processes records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_services.data_source.fetch = mock_fetch
        mock_record_processor.process_batch.return_value = (3, 3, 3, 0)

        await executor.execute(watermark=None, limit=None)

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

        await executor.execute(watermark=None, limit=None)

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

        await executor.execute(watermark=None, limit=None)

        # With checkpoint_interval=5, should checkpoint at record 5 and 10
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2

    async def test_execute_handles_shutdown_with_last_record(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown saves checkpoint with last record."""
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
            await executor.execute(watermark=None, limit=None)

        # Should have saved checkpoint with the last record before shutdown
        mock_checkpoint_manager.save_checkpoint.assert_called()
        last_call_args = mock_checkpoint_manager.save_checkpoint.call_args
        assert last_call_args[0][0]["id"] == "2"  # Last record before shutdown

    async def test_execute_shutdown_without_records(
        self, executor, mock_services, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown without any processed records."""

        async def mock_fetch(**kwargs):
            shutdown_signal.request()
            yield {"id": "0", "value": 10}

        mock_services.data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(watermark=None, limit=None)

    async def test_execute_empty_data(self, executor, mock_services, mock_record_processor):
        """Test execute with no data."""

        async def mock_fetch(**kwargs):
            if False:  # Empty generator
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(watermark=None, limit=None)

        assert executor.records_fetched == 0
        mock_record_processor.process_batch.assert_not_called()

    async def test_execute_passes_watermark_and_limit(self, executor, mock_services):
        """Test that watermark and limit are passed to data source."""
        watermark = "2024-01-01"  # Watermark is a TypeAlias for str | datetime | int

        captured_kwargs = {}

        async def mock_fetch(**kwargs):
            captured_kwargs.update(kwargs)
            if False:
                yield {}

        mock_services.data_source.fetch = mock_fetch

        await executor.execute(watermark=watermark, limit=100)

        assert captured_kwargs.get("watermark") == watermark
        assert captured_kwargs.get("limit") == 100
