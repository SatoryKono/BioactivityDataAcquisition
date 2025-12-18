"""Unit tests for PipelineExecutor."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.types import RunID, RunType


@pytest.fixture
def mock_data_source():
    """Create mock data source."""
    source = AsyncMock()
    return source


@pytest.fixture
def mock_storage():
    """Create mock storage."""
    storage = AsyncMock()
    storage.write_bronze = AsyncMock()
    storage.write_silver = AsyncMock()
    storage.write_gold = AsyncMock()
    return storage


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock checkpoint manager."""
    manager = MagicMock(spec=CheckpointManager)
    manager.save_checkpoint = AsyncMock()
    return manager


@pytest.fixture
def mock_quarantine_manager():
    """Create mock quarantine manager."""
    manager = MagicMock()
    manager.quarantine_record = AsyncMock()
    return manager


@pytest.fixture
def mock_context():
    """Create mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def shutdown_signal():
    """Create shutdown signal."""
    return ShutdownSignal()


@pytest.fixture
def transform_callback():
    """Create mock transform callback."""

    async def transform(ctx, record):
        return {"entity_id": record.get("id", "unknown"), "value": record.get("value")}

    return transform


@pytest.fixture
def gold_filter_callback():
    """Create mock gold filter callback."""

    def filter_gold(ctx, record):
        return record.get("value", 0) > 5

    return filter_gold


@pytest.fixture
def executor(
    mock_data_source,
    mock_storage,
    mock_checkpoint_manager,
    mock_quarantine_manager,
    mock_context,
    shutdown_signal,
    transform_callback,
    gold_filter_callback,
):
    """Create PipelineExecutor instance."""
    return PipelineExecutor(
        data_source=mock_data_source,
        storage=mock_storage,
        checkpoint_manager=mock_checkpoint_manager,
        quarantine_manager=mock_quarantine_manager,
        error_classifier=ErrorClassifier(),
        context=mock_context,
        shutdown_signal=shutdown_signal,
        provider="test_provider",
        entity_type="test_entity",
        transform_callback=transform_callback,
        gold_filter_callback=gold_filter_callback,
        silver_schema=MagicMock(),
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
        mock_data_source,
        mock_storage,
        mock_checkpoint_manager,
        mock_quarantine_manager,
        mock_context,
        shutdown_signal,
        transform_callback,
        gold_filter_callback,
    ):
        """Test default batch size when not specified."""
        executor = PipelineExecutor(
            data_source=mock_data_source,
            storage=mock_storage,
            checkpoint_manager=mock_checkpoint_manager,
            quarantine_manager=mock_quarantine_manager,
            error_classifier=ErrorClassifier(),
            context=mock_context,
            shutdown_signal=shutdown_signal,
            provider="test",
            entity_type="test",
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            silver_schema=MagicMock(),
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

    async def test_execute_processes_records(self, executor, mock_data_source):
        """Test that execute processes records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(3):
                yield {"id": str(i), "value": 10}

        mock_data_source.fetch = mock_fetch

        await executor.execute(watermark=None, limit=None)

        assert executor.records_fetched == 3
        assert executor.records_bronze == 3
        assert executor.records_silver == 3
        assert executor.records_gold == 3  # All records have value > 5

    async def test_execute_batches_records(
        self, executor, mock_data_source, mock_storage
    ):
        """Test that execute batches records correctly."""

        async def mock_fetch(**kwargs):
            for i in range(15):  # More than batch size of 10
                yield {"id": str(i), "value": 10}

        mock_data_source.fetch = mock_fetch

        await executor.execute(watermark=None, limit=None)

        # Should have called write_silver twice (batch of 10 + batch of 5)
        assert mock_storage.write_silver.call_count == 2

    async def test_execute_checkpoints_at_interval(
        self, executor, mock_data_source, mock_checkpoint_manager
    ):
        """Test that execute checkpoints at configured interval."""

        async def mock_fetch(**kwargs):
            for i in range(10):
                yield {"id": str(i), "value": 10}

        mock_data_source.fetch = mock_fetch

        await executor.execute(watermark=None, limit=None)

        # With checkpoint_interval=5, should checkpoint at record 5 and 10
        assert mock_checkpoint_manager.save_checkpoint.call_count == 2

    async def test_execute_handles_shutdown_with_last_record(
        self, executor, mock_data_source, mock_checkpoint_manager, shutdown_signal
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

        mock_data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(watermark=None, limit=None)

        # Should have saved checkpoint with the last record before shutdown
        mock_checkpoint_manager.save_checkpoint.assert_called()
        last_call_args = mock_checkpoint_manager.save_checkpoint.call_args
        assert last_call_args[0][0]["id"] == "2"  # Last record before shutdown

    async def test_execute_shutdown_without_records(
        self, executor, mock_data_source, mock_checkpoint_manager, shutdown_signal
    ):
        """Test shutdown without any processed records."""

        async def mock_fetch(**kwargs):
            shutdown_signal.request()
            yield {"id": "0", "value": 10}

        mock_data_source.fetch = mock_fetch

        with pytest.raises(PipelineShutdownError):
            await executor.execute(watermark=None, limit=None)

    async def test_execute_empty_data(self, executor, mock_data_source, mock_storage):
        """Test execute with no data."""

        async def mock_fetch(**kwargs):
            if False:  # Empty generator
                yield {}

        mock_data_source.fetch = mock_fetch

        await executor.execute(watermark=None, limit=None)

        assert executor.records_fetched == 0
        mock_storage.write_silver.assert_not_called()

    async def test_execute_passes_watermark_and_limit(self, executor, mock_data_source):
        """Test that watermark and limit are passed to data source."""
        watermark = "2024-01-01"  # Watermark is a TypeAlias for str | datetime | int

        captured_kwargs = {}

        async def mock_fetch(**kwargs):
            captured_kwargs.update(kwargs)
            if False:
                yield {}

        mock_data_source.fetch = mock_fetch

        await executor.execute(watermark=watermark, limit=100)

        assert captured_kwargs.get("watermark") == watermark
        assert captured_kwargs.get("limit") == 100
