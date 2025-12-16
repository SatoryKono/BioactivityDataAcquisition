"""Unit tests for the PipelineExecutor class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.executor import PipelineExecutor
from bioetl.domain.context import PipelineContext
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics
from bioetl.domain.types import RunType


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(
        self, _context: PipelineContext, record: dict
    ) -> dict | None:
        return record


@pytest.fixture
def mock_base_pipeline():
    """Fixture for a mocked BasePipeline."""
    # Use MagicMock for data_source so fetch() returns async generator directly
    # (not a coroutine that wraps it)
    mock_data_source = MagicMock()

    pipeline = ConcretePipeline(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        run_type=RunType.INCREMENTAL,
        data_source=mock_data_source,
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        logger=MagicMock(),
        metrics=NoOpMetrics(warn_on_use=False),
        resume=False,
    )
    pipeline.orchestrator = MagicMock()
    pipeline.orchestrator.shutdown_requested = False
    pipeline.transform_bronze_to_silver = AsyncMock(return_value={"id": 1})
    pipeline.should_write_gold = MagicMock(return_value=True)
    pipeline.checkpoint_manager = AsyncMock()
    pipeline.quarantine_manager = AsyncMock()
    pipeline.error_classifier = MagicMock()
    # Mock context with a logger that has .bind() method
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    from uuid import uuid4

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import RunID

    pipeline.context = PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )
    return pipeline


@pytest.fixture
def executor(mock_base_pipeline):
    """Fixture for a PipelineExecutor."""
    return PipelineExecutor(mock_base_pipeline)


class AsyncIterator:
    def __init__(self, data):
        self.data = data

    async def __aiter__(self):
        for item in self.data:
            yield item


@pytest.mark.asyncio
async def test_executor_initialization(executor):
    """Test that the PipelineExecutor initializes correctly."""
    assert executor.records_fetched == 0
    assert executor.records_bronze == 0
    assert executor.records_silver == 0
    assert executor.records_gold == 0
    assert executor.records_quarantined == 0


@pytest.mark.asyncio
async def test_executor_execute_happy_path(executor, mock_base_pipeline):
    """Test the execute method with a single record."""
    mock_base_pipeline.data_source.fetch.return_value = AsyncIterator([{"id": 1}])
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1
    assert executor.records_bronze == 1
    assert executor.records_silver == 1
    assert executor.records_gold == 1
    assert executor.records_quarantined == 0

    mock_base_pipeline.storage.write_bronze.assert_called_once()
    mock_base_pipeline.storage.write_silver.assert_called_once()
    mock_base_pipeline.storage.write_gold.assert_called_once()
    mock_base_pipeline.checkpoint_manager.save_checkpoint.assert_not_called()


@pytest.mark.asyncio
async def test_executor_execute_with_checkpoint(executor, mock_base_pipeline):
    """Test that the checkpoint is saved every 1000 records."""
    mock_base_pipeline.data_source.fetch.return_value = AsyncIterator(
        [{"id": i} for i in range(1000)]
    )
    await executor.execute(watermark=None, limit=None)

    assert executor.records_fetched == 1000
    mock_base_pipeline.checkpoint_manager.save_checkpoint.assert_called_once()
