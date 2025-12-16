"""Unit tests for the BasePipeline class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.pipeline.base import BasePipeline
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(self, _context: PipelineContext, record: dict) -> dict | None:
        return record


@pytest.fixture
def mock_pipeline():
    """Fixture for a mocked BasePipeline."""
    pipeline = ConcretePipeline(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        run_type=RunType.INCREMENTAL,
        data_source=AsyncMock(),
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        resume=False,
    )
    pipeline.orchestrator = AsyncMock()
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
    mock_pipeline.orchestrator.run.assert_called_once()
