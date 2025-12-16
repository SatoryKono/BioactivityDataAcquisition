"""Unit tests for the BasePipeline class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.pipeline_config import PipelineConfig, PipelineRuntimeConfig
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


@pytest.mark.asyncio
async def test_base_pipeline_initialization(mock_pipeline):
    """Test that the BasePipeline initializes correctly."""
    assert mock_pipeline.pipeline_name == "test_pipeline"
    assert mock_pipeline.provider == "test_provider"
    assert mock_pipeline.entity_type == "test_entity"
    assert mock_pipeline.run_type == RunType.INCREMENTAL
    assert mock_pipeline.resume is False
    assert mock_pipeline.context.run_id is not None
    assert mock_pipeline.context.logger is not None


@pytest.mark.asyncio
async def test_base_pipeline_run_calls_orchestrator(mock_pipeline):
    """Test that the run method calls the orchestrator."""
    await mock_pipeline.run()
    mock_pipeline._orchestrator.run.assert_called_once()


@pytest.mark.asyncio
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


def test_from_params_emits_deprecation_warning():
    """Test that from_params() emits DeprecationWarning."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    with pytest.warns(DeprecationWarning, match="from_params.*deprecated"):
        ConcretePipeline.from_params(
            pipeline_name="test",
            provider="test",
            entity_type="entity",
            run_type=RunType.INCREMENTAL,
            data_source=AsyncMock(),
            storage=AsyncMock(),
            lock=AsyncMock(),
            checkpoint=AsyncMock(),
            quarantine=AsyncMock(),
            logger=mock_logger,
            metrics=MagicMock(),
        )
