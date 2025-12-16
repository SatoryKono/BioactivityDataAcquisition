"""Unit tests for the PipelineExecutor class."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
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

    data_source = MagicMock()
    storage = AsyncMock()
    checkpoint_manager = AsyncMock(spec=CheckpointManager)
    quarantine_manager = AsyncMock(spec=QuarantineManager)
    error_classifier = MagicMock(spec=ErrorClassifier)
    shutdown_signal = ShutdownSignal()

    async def transform_callback(ctx, record):
        return {"id": record.get("id", 1)}

    def gold_filter_callback(ctx, record):
        return True

    return {
        "data_source": data_source,
        "storage": storage,
        "checkpoint_manager": checkpoint_manager,
        "quarantine_manager": quarantine_manager,
        "error_classifier": error_classifier,
        "context": context,
        "shutdown_signal": shutdown_signal,
        "provider": "test_provider",
        "entity_type": "test_entity",
        "transform_callback": transform_callback,
        "gold_filter_callback": gold_filter_callback,
    }


@pytest.fixture
def executor(mock_components):
    """Fixture for a PipelineExecutor."""
    return PipelineExecutor(**mock_components)


@pytest.mark.asyncio
async def test_executor_initialization(executor):
    """Test that the PipelineExecutor initializes correctly."""
    assert executor.records_fetched == 0
    assert executor.records_bronze == 0
    assert executor.records_silver == 0
    assert executor.records_gold == 0
    assert executor.records_quarantined == 0


@pytest.mark.asyncio
async def test_executor_execute_happy_path(executor, mock_components):
    """Test the execute method with a single record."""
    mock_components["data_source"].fetch.return_value = AsyncIterator([{"id": 1}])
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1
    assert executor.records_bronze == 1
    # Silver/Gold counts depend on RecordProcessor implementation


@pytest.mark.asyncio
async def test_executor_execute_with_checkpoint(executor, mock_components):
    """Test that the checkpoint is saved every 1000 records."""
    mock_components["data_source"].fetch.return_value = AsyncIterator(
        [{"id": i} for i in range(1000)]
    )
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1000
    mock_components["checkpoint_manager"].save_checkpoint.assert_called_once()
