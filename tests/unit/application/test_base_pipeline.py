"""Unit tests for the BasePipeline class."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.pipeline_services import PipelineService
from bioetl.application.core.lifecycle.shutdown import ShutdownSignal
from bioetl.domain.config import PipelineConfig, RuntimeConfig, TableConfig
from bioetl.domain.context import MISSING_RUNTIME_TIMESTAMP, PipelineContext
from bioetl.domain.types import RunID, RunType
from tests.helpers.transformer_dependencies import (
    build_test_transformer_dependencies,
)


pytestmark = pytest.mark.unit


def _stable_run_id(seed: int) -> RunID:
    return RunID(UUID(int=seed))


class ConcretePipeline(BasePipeline):
    async def transform_bronze_to_silver(
        self, _context: PipelineContext, record: dict, index: int = 0
    ) -> dict | None:
        await asyncio.sleep(0)
        return record


class MockTransformer(BaseTransformer):
    """Mock transformer for testing."""

    def __init__(self):
        super().__init__(
            provider="test",
            dependencies=build_test_transformer_dependencies(),
        )

    async def _transform_impl(self, context, record, index):
        await asyncio.sleep(0)
        return record


@pytest.fixture
def shutdown_signal() -> ShutdownSignal:
    """Create explicit ShutdownSignal for BasePipeline tests."""
    return ShutdownSignal()


@pytest.fixture
def mock_pipeline(shutdown_signal: ShutdownSignal):
    """Fixture for a mocked BasePipeline."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["test_entity_id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        resume=False,
    )
    # Mock logger with bind method
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)

    services = PipelineService(
        data_source=AsyncMock(),
        storage=MagicMock(),
        lock=AsyncMock(),
        checkpoint=MagicMock(),
        quarantine=MagicMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    run_id = _stable_run_id(1)
    # Inject mock transformer
    transformer = MockTransformer()
    pipeline = ConcretePipeline(
        config,
        runtime,
        services,
        run_id,
        shutdown_signal=shutdown_signal,
        transformer=transformer,
    )
    return pipeline


def test_base_pipeline_initialization(mock_pipeline):
    """Test that the BasePipeline initializes correctly."""
    assert mock_pipeline.pipeline_name == "test_pipeline"
    assert mock_pipeline.provider == "test_provider"
    assert mock_pipeline.entity_type == "test_entity"
    assert mock_pipeline.run_type == RunType.INCREMENTAL
    assert mock_pipeline.resume is False
    assert mock_pipeline.context.run_id is not None
    assert mock_pipeline.context.logger is not None
    assert mock_pipeline.context.started_at == MISSING_RUNTIME_TIMESTAMP
    assert mock_pipeline.context.pipeline_name == "test_pipeline"
    assert mock_pipeline.context.workflow_id == "standalone"


def test_base_pipeline_accepts_five_params():
    """Test that BasePipeline.__init__ accepts explicit shutdown signal injection."""
    config = PipelineConfig(
        pipeline_name="test",
        provider="test",
        entity_type="entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test.entity",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    run_id = _stable_run_id(2)
    transformer = MockTransformer()
    shutdown_signal = ShutdownSignal()

    pipeline = ConcretePipeline(
        config,
        runtime,
        services,
        run_id,
        shutdown_signal=shutdown_signal,
        transformer=transformer,
    )
    assert pipeline.config == config
    assert pipeline.runtime == runtime
    assert pipeline.services == services
    assert pipeline.run_id == run_id
    assert pipeline.transformer == transformer


def test_base_pipeline_properties(mock_pipeline):
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


def test_run_id_propagation_is_consistent():
    """Test that run_id from constructor is used consistently across all components.

    This test ensures that the run_id passed to BasePipeline is the same run_id
    that appears in the PipelineContext, preventing the previous bug where
    BasePipeline generated a new run_id internally.
    """
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )

    # Create pipeline with explicit run_id (simulating CLI -> bootstrap -> pipeline flow)
    expected_run_id = _stable_run_id(3)
    pipeline = ConcretePipeline(
        config,
        runtime,
        services,
        expected_run_id,
        shutdown_signal=ShutdownSignal(),
    )

    # Verify run_id consistency across all access points
    assert pipeline.run_id == expected_run_id, (
        "run_id property should return the injected run_id"
    )
    assert pipeline.context.run_id == expected_run_id, (
        "PipelineContext should have the same run_id"
    )
    assert pipeline._run_id == expected_run_id, "Internal _run_id should match"

    # Verify logger was bound with correct run_id
    mock_logger.bind.assert_called_with(
        run_id=str(expected_run_id),
        pipeline=config.pipeline_name,
    )


def test_base_pipeline_uses_injected_shutdown_signal():
    """BasePipeline should support ShutdownSignal injection for DI compliance."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    run_id = _stable_run_id(4)
    injected_signal = ShutdownSignal()

    pipeline = ConcretePipeline.create(
        run_id=run_id,
        runtime=runtime,
        services=services,
        config=config,
        shutdown_signal=injected_signal,
    )

    assert pipeline.shutdown_signal is injected_signal


def test_base_pipeline_preserves_explicit_started_at() -> None:
    """Explicit runtime anchor should propagate into PipelineContext."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(run_type=RunType.INCREMENTAL)
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )
    started_at = datetime(2026, 4, 27, 17, 7, 21, tzinfo=UTC)

    pipeline = ConcretePipeline.create(
        run_id=_stable_run_id(5),
        runtime=runtime,
        services=services,
        config=config,
        shutdown_signal=ShutdownSignal(),
        started_at=started_at,
    )

    assert pipeline.context.started_at == started_at


def test_base_pipeline_propagates_runtime_workflow_id_into_context() -> None:
    """Workflow-aware runtime config should reach in-run pipeline context."""
    config = PipelineConfig(
        pipeline_name="chembl_target",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        workflow_id="chembl_target_workflow",
    )
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )

    pipeline = ConcretePipeline.create(
        run_id=_stable_run_id(6),
        runtime=runtime,
        services=services,
        config=config,
        shutdown_signal=ShutdownSignal(),
    )

    assert pipeline.context.pipeline_name == "chembl_target"
    assert pipeline.context.workflow_id == "chembl_target_workflow"


def test_exact_replay_pipeline_context_uses_deterministic_replay_anchor() -> None:
    """Exact replay should bind a stable DQ/report timestamp anchor into context."""
    config = PipelineConfig(
        pipeline_name="test_pipeline",
        provider="test_provider",
        entity_type="test_entity",
        table=TableConfig(
            primary_keys=["id"],
            silver_table="test_provider.test_entity",
        ),
    )
    runtime = RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        exact_replay=True,
        replay_anchor_date="2026-04-10",
    )
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    services = PipelineService(
        data_source=AsyncMock(),
        storage=AsyncMock(),
        lock=AsyncMock(),
        checkpoint=AsyncMock(),
        quarantine=AsyncMock(),
        metrics=MagicMock(),
        tracing=MagicMock(),
        logger=mock_logger,
    )

    pipeline = ConcretePipeline(
        config,
        runtime,
        services,
        _stable_run_id(6),
        shutdown_signal=ShutdownSignal(),
    )

    assert pipeline.context.replay_timestamp_anchor == datetime(
        2026,
        4,
        10,
        0,
        0,
        0,
        tzinfo=UTC,
    )
