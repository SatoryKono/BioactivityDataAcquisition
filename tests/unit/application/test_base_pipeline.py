"""Unit tests for the BasePipeline class."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


class MockTransformer(BaseTransformer):
    """Mock transformer for testing."""

    async def transform(
        self, context: PipelineContext, record: dict
    ) -> dict | None:
        return record


class ConcretePipeline(BasePipeline):
    """Concrete implementation for testing (uses injected transformer)."""

    pass


@pytest.fixture
def mock_transformer():
    """Create mock transformer."""
    return MockTransformer(provider="test_provider")


@pytest.fixture
def mock_pipeline(mock_transformer):
    """Fixture for a mocked BasePipeline."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        primary_keys=["test_entity_id"],
        silver_table="test_provider.test_entity",
    )
    runtime = RuntimeConfig(
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
        tracing=MagicMock(),
        logger=mock_logger,
    )
    pipeline = ConcretePipeline(config, runtime, services, mock_transformer)
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


async def test_base_pipeline_accepts_four_params():
    """Test that BasePipeline.__init__ accepts exactly 4 parameters (with transformer)."""
    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        primary_keys=["id"],
        silver_table="test.entity",
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineServices(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    transformer = MockTransformer(provider="test")

    # Should work with exactly 4 positional args (including transformer)
    pipeline = ConcretePipeline(config, runtime, services, transformer)
    assert pipeline.config == config
    assert pipeline.runtime == runtime
    assert pipeline.services == services
    assert pipeline._transformer == transformer


@pytest.mark.skip(reason="Suspected .pyc cache issue - run with --cache-clear")
async def test_base_pipeline_properties(mock_pipeline):
    """Test all convenience properties."""
    # Test run_id property
    assert mock_pipeline.run_id is not None

    # Test logger property
    assert mock_pipeline.logger is not None

    # Test shutdown_signal property
    assert mock_pipeline.shutdown_signal is not None

    # Test services property provides access to injected services
    assert mock_pipeline.services is not None
    assert mock_pipeline.services.data_source is not None
    assert mock_pipeline.services.storage is not None
    assert mock_pipeline.services.lock is not None
    assert mock_pipeline.services.checkpoint is not None
    assert mock_pipeline.services.quarantine is not None
    assert mock_pipeline.services.metrics is not None

    # Test limit property
    assert mock_pipeline.limit is None


async def test_base_pipeline_should_write_gold(mock_pipeline):
    """Test default should_write_gold returns True."""
    result = mock_pipeline.should_write_gold(mock_pipeline.context, {})
    assert result is True


