"""Unit tests for the BasePipeline class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import (
    PipelineConfig,
    PipelineRuntimeConfig,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(
        self, _context: PipelineContext, record: dict
    ) -> dict | None:
        return record


@pytest.fixture
def mock_pipeline():
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

    services = PipelineServices(
        data_source=AsyncMock(),
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        metrics=MagicMock(),
        logger=mock_logger,
    )
    pipeline = ConcretePipeline(config, runtime, services)
    pipeline._orchestrator = AsyncMock()
    return pipeline


async def test_base_pipeline_initialization(mock_pipeline):
    """Test that the BasePipeline initializes correctly."""
    assert mock_pipeline.pipeline_name == "test_pipeline"
    assert mock_pipeline.provider == "test_provider"
    assert mock_pipeline.entity_type == "test_entity"
    assert mock_pipeline.run_type == RunType.INCREMENTAL
    assert mock_pipeline.resume is False
    assert mock_pipeline.context.run_id is not None
    assert mock_pipeline.context.logger is not None


async def test_base_pipeline_run_calls_orchestrator(mock_pipeline):
    """Test that the run method calls the orchestrator."""
    await mock_pipeline.run()
    mock_pipeline._orchestrator.run.assert_called_once()


async def test_base_pipeline_accepts_three_params():
    """Test that BasePipeline.__init__ accepts exactly 3 parameters."""
    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="test.entity",
    )
    runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        logger=mock_logger,
    )

    # Should work with exactly 3 positional args
    pipeline = ConcretePipeline(config, runtime, services)
    assert pipeline.config == config
    assert pipeline.runtime == runtime
    assert pipeline.services == services


async def test_base_pipeline_properties(mock_pipeline):
    """Test all convenience properties."""
    # Test run_id property
    assert mock_pipeline.run_id is not None

    # Test logger property
    assert mock_pipeline.logger is not None

    # Test shutdown_signal property
    assert mock_pipeline.shutdown_signal is not None

    # Test service delegate properties
    assert mock_pipeline.data_source is mock_pipeline.services.data_source
    assert mock_pipeline.storage is mock_pipeline.services.storage
    assert mock_pipeline.lock is mock_pipeline.services.lock
    assert mock_pipeline.checkpoint is mock_pipeline.services.checkpoint
    assert mock_pipeline.quarantine is mock_pipeline.services.quarantine
    assert mock_pipeline.metrics is mock_pipeline.services.metrics

    # Test limit property
    assert mock_pipeline.limit is None


async def test_base_pipeline_error_classifier(mock_pipeline):
    """Test error classifier lazy initialization."""
    # First access should initialize
    classifier = mock_pipeline.error_classifier
    assert classifier is not None

    # Second access should return same instance
    assert mock_pipeline.error_classifier is classifier


async def test_base_pipeline_checkpoint_manager(mock_pipeline):
    """Test checkpoint manager lazy initialization."""
    manager = mock_pipeline.checkpoint_manager
    assert manager is not None

    # Second access should return same instance
    assert mock_pipeline.checkpoint_manager is manager


async def test_base_pipeline_quarantine_manager(mock_pipeline):
    """Test quarantine manager lazy initialization."""
    manager = mock_pipeline.quarantine_manager
    assert manager is not None

    # Second access should return same instance
    assert mock_pipeline.quarantine_manager is manager


async def test_base_pipeline_should_write_gold(mock_pipeline):
    """Test default should_write_gold returns True."""
    result = mock_pipeline.should_write_gold(mock_pipeline.context, {})
    assert result is True


async def test_base_pipeline_extract_watermark(mock_pipeline):
    """Test default extract_watermark returns datetime."""
    from datetime import datetime

    result = mock_pipeline.extract_watermark(mock_pipeline.context, {})
    assert isinstance(result, datetime)


async def test_run_pipeline_flow():
    """Test run_pipeline_flow helper function."""
    from bioetl.application.core.base import run_pipeline_flow

    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="test.entity",
    )
    runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_services = MagicMock(spec=PipelineServices)
    mock_services.aclose = AsyncMock()
    mock_services.logger = mock_logger

    pipeline = ConcretePipeline.__new__(ConcretePipeline)
    pipeline._config = config
    pipeline._runtime = runtime
    pipeline._services = mock_services
    pipeline._orchestrator = AsyncMock()

    await run_pipeline_flow(pipeline, mock_logger)

    pipeline._orchestrator.run.assert_called_once()
    mock_services.aclose.assert_called_once()


async def test_run_pipeline_flow_with_exception():
    """Test run_pipeline_flow handles exceptions."""
    from bioetl.application.core.base import run_pipeline_flow

    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="test.entity",
    )
    runtime = PipelineRuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_services = MagicMock(spec=PipelineServices)
    mock_services.aclose = AsyncMock()
    mock_services.logger = mock_logger

    pipeline = ConcretePipeline.__new__(ConcretePipeline)
    pipeline._config = config
    pipeline._runtime = runtime
    pipeline._services = mock_services
    pipeline._orchestrator = AsyncMock()
    pipeline._orchestrator.run.side_effect = RuntimeError("Test error")

    with pytest.raises(RuntimeError):
        await run_pipeline_flow(pipeline, mock_logger)

    # aclose should still be called in finally block
    mock_services.aclose.assert_called_once()
