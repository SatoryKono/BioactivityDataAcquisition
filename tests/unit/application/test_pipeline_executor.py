"""Unit tests for the PipelineExecutor class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.shutdown import ShutdownSignal


class AsyncIterator:
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for item in self.data:
            yield item


@pytest.fixture
def mock_services():
    """Create mock PipelineServices."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    data_source = MagicMock()
    storage = AsyncMock()

    services = MagicMock()
    services.data_source = data_source
    services.storage = storage
    services.logger = mock_logger

    return services


@pytest.fixture
def mock_record_processor():
    """Create mock RecordProcessor."""
    processor = AsyncMock()
    processor.process_batch = AsyncMock(return_value=(1, 1, 1, 0))
    return processor


@pytest.fixture
def mock_checkpoint_manager():
    """Create mock CheckpointManager."""
    return AsyncMock(spec=CheckpointManager)


@pytest.fixture
def executor(mock_services, mock_record_processor, mock_checkpoint_manager):
    """Fixture for a PipelineExecutor."""
    return PipelineExecutor(
        services=mock_services,
        record_processor=mock_record_processor,
        checkpoint_manager=mock_checkpoint_manager,
        shutdown_signal=ShutdownSignal(),
        entity_type="test_entity",
    )


async def test_executor_initialization(executor):
    """Test that the PipelineExecutor initializes correctly."""
    assert executor.records_fetched == 0
    assert executor.records_bronze == 0
    assert executor.records_silver == 0
    assert executor.records_gold == 0
    assert executor.records_quarantined == 0


async def test_executor_execute_happy_path(executor, mock_services):
    """Test the execute method with a single record."""
    mock_services.data_source.fetch.return_value = AsyncIterator([{"id": 1}])
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1
    assert executor.records_bronze == 1
    # Silver/Gold counts depend on RecordProcessor implementation


async def test_executor_execute_with_checkpoint(executor, mock_services, mock_checkpoint_manager):
    """Test that the checkpoint is saved every 1000 records."""
    mock_services.data_source.fetch.return_value = AsyncIterator(
        [{"id": i} for i in range(1000)]
    )
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1000
    mock_checkpoint_manager.save_checkpoint.assert_called_once()
