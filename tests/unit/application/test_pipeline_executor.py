"""Unit tests for the PipelineExecutor class."""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.executor import PipelineExecutor
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.observability.noop_metrics import NoOpMetrics


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(
        self, _context: PipelineContext, record: dict
    ) -> dict | None:
        return record


@pytest.fixture
def mock_base_pipeline():
    """Fixture for a mocked BasePipeline."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        primary_keys=["test_entity_id"],
        silver_table="test_provider.test_entity",
    )
    runtime = PipelineRuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
    )
    # Mock logger with bind method
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    # Use MagicMock for data_source so fetch() returns async generator directly
    mock_data_source = MagicMock()

    # Storage methods are now async per ADR-0005
    mock_storage = AsyncMock()

    services = PipelineServices(
        data_source=mock_data_source,
        storage=mock_storage,
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=NoOpMetrics(warn_on_use=False),
        logger=mock_logger,
    )

    pipeline = ConcretePipeline(config, runtime, services)
    pipeline._orchestrator = MagicMock()
    pipeline._orchestrator.shutdown_requested = False
    pipeline.transform_bronze_to_silver = AsyncMock(return_value={"id": 1})
    pipeline.should_write_gold = MagicMock(return_value=True)
    pipeline._checkpoint_manager = AsyncMock()
    pipeline._quarantine_manager = AsyncMock()
    pipeline._error_classifier = MagicMock()
    # Override context with a logger that has .bind() method
    pipeline._context = PipelineContext(
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


# --- Tests for from_components() API (new API per ADR-0005) ---

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import ShutdownSignal
from bioetl.domain.error_classifier import ErrorClassifier


@pytest.fixture
def mock_components():
    """Fixture for creating executor via from_components()."""
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
def executor_from_components(mock_components):
    """Fixture for PipelineExecutor using from_components()."""
    return PipelineExecutor.from_components(**mock_components)


@pytest.mark.asyncio
async def test_executor_from_components_initialization(executor_from_components):
    """Test that PipelineExecutor initializes correctly via from_components()."""
    assert executor_from_components.records_fetched == 0
    assert executor_from_components.records_bronze == 0
    assert executor_from_components.records_silver == 0
    assert executor_from_components.records_gold == 0
    assert executor_from_components.records_quarantined == 0


@pytest.mark.asyncio
async def test_executor_from_components_execute(executor_from_components, mock_components):
    """Test execute method with from_components() API."""
    mock_components["data_source"].fetch.return_value = AsyncIterator([{"id": 1}])
    await executor_from_components.execute(watermark=None, limit=None)

    assert executor_from_components.records_fetched == 1
    assert executor_from_components.records_bronze == 1
    mock_components["storage"].write_bronze.assert_called_once()


@pytest.mark.asyncio
async def test_executor_no_self_reference():
    """Test that PipelineExecutor created via from_components has no pipeline reference."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    context = PipelineContext(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )

    async def transform(ctx, record):
        return record

    def gold_filter(ctx, record):
        return True

    executor = PipelineExecutor.from_components(
        data_source=MagicMock(),
        storage=AsyncMock(),
        checkpoint_manager=AsyncMock(),
        quarantine_manager=AsyncMock(),
        error_classifier=MagicMock(),
        context=context,
        shutdown_signal=ShutdownSignal(),
        provider="test",
        entity_type="entity",
        transform_callback=transform,
        gold_filter_callback=gold_filter,
    )

    # pipeline attribute should be None when using from_components()
    assert executor.pipeline is None
