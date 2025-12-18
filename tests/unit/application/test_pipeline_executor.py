"""Unit tests for the PipelineExecutor class."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType


class AsyncIterator:
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for item in self.data:
            yield item


@pytest.fixture
def mock_components():
    """Fixture for creating executor with explicit dependencies."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    context = PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )

    # Create mock services
    data_source = MagicMock()
    storage = AsyncMock()

    services = MagicMock(spec=PipelineServices)
    services.data_source = data_source
    services.storage = storage
    services.logger = mock_logger

    # Create mock record processor
    record_processor = AsyncMock(spec=RecordProcessor)
    record_processor.process_batch = AsyncMock(return_value=(1, 1, 1, 0))

    checkpoint_manager = AsyncMock(spec=CheckpointManager)
    shutdown_signal = ShutdownSignal()

    return {
        "services": services,
        "record_processor": record_processor,
        "checkpoint_manager": checkpoint_manager,
        "shutdown_signal": shutdown_signal,
        "entity_type": "test_entity",
        # Keep data_source reference for test assertions
        "_data_source": data_source,
    }


@pytest.fixture
def executor(mock_components):
    """Fixture for a PipelineExecutor."""
    # Extract only the args needed for PipelineExecutor
    return PipelineExecutor(
        services=mock_components["services"],
        record_processor=mock_components["record_processor"],
        checkpoint_manager=mock_components["checkpoint_manager"],
        shutdown_signal=mock_components["shutdown_signal"],
        entity_type=mock_components["entity_type"],
    )


async def test_executor_initialization(executor):
    """Test that the PipelineExecutor initializes correctly."""
    assert executor.records_fetched == 0
    assert executor.records_bronze == 0
    assert executor.records_silver == 0
    assert executor.records_gold == 0
    assert executor.records_quarantined == 0


async def test_executor_execute_happy_path(executor, mock_components):
    """Test the execute method with a single record."""
    mock_components["_data_source"].fetch.return_value = AsyncIterator([{"id": 1}])
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1
    assert executor.records_bronze == 1
    # Silver/Gold counts depend on RecordProcessor implementation


async def test_executor_execute_with_checkpoint(executor, mock_components):
    """Test that the checkpoint is saved every 1000 records."""
    mock_components["_data_source"].fetch.return_value = AsyncIterator(
        [{"id": i} for i in range(1000)]
    )
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1000
    mock_components["checkpoint_manager"].save_checkpoint.assert_called_once()
