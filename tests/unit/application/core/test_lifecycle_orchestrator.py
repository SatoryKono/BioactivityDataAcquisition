"""Unit tests for the LifecycleOrchestrator class."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.core.lifecycle_orchestrator import (
    ClearDecision,
    LifecycleOrchestrator,
)
from bioetl.application.services.medallion_lifecycle import ClearResult
from bioetl.domain.config import PipelineConfig, RuntimeConfig
from bioetl.domain.medallion import ClearPolicy
from bioetl.domain.types import RunType


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def pipeline_config():
    """Create a pipeline config."""
    return PipelineConfig(
        pipeline_name="test_lifecycle_pipeline",
        provider="chembl",
        entity_type="activity",
        primary_keys=["activity_id"],
        silver_table="test_silver",
    )


@pytest.fixture
def runtime_config():
    """Create a runtime config."""
    return RuntimeConfig(
        run_type=RunType.INCREMENTAL,
        limit=None,
    )


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock lifecycle service."""
    service = MagicMock()
    service.clear = AsyncMock(
        return_value=ClearResult(silver_cleared=0, gold_cleared=0, dry_run=False)
    )
    return service


@pytest.fixture
def lifecycle_orchestrator(
    pipeline_config, runtime_config, mock_logger, mock_lifecycle_service
):
    """Create a LifecycleOrchestrator instance."""
    return LifecycleOrchestrator(
        config=pipeline_config,
        runtime=runtime_config,
        logger=mock_logger,
        lifecycle_service=mock_lifecycle_service,
    )


@pytest.mark.unit
class TestLifecycleOrchestratorInit:
    """Tests for LifecycleOrchestrator initialization."""

    def test_initialization(
        self, pipeline_config, runtime_config, mock_logger, mock_lifecycle_service
    ):
        """Test lifecycle orchestrator initializes correctly."""
        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime_config,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        assert orchestrator._config == pipeline_config
        assert orchestrator._runtime == runtime_config
        assert orchestrator._logger == mock_logger
        assert orchestrator._lifecycle_service == mock_lifecycle_service


@pytest.mark.unit
class TestLifecycleOrchestratorClear:
    """Tests for LifecycleOrchestrator.clear_for_run method."""

    @pytest.mark.asyncio
    async def test_clear_for_incremental_uses_never_policy(
        self, pipeline_config, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run uses NEVER policy for incremental runs."""
        runtime = RuntimeConfig(run_type=RunType.INCREMENTAL, limit=None)

        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        decision = await orchestrator.clear_for_run()

        assert decision.policy.clear_policy == ClearPolicy.NEVER
        mock_lifecycle_service.clear.assert_called_once()
        call_kwargs = mock_lifecycle_service.clear.call_args.kwargs
        assert call_kwargs["policy"].clear_policy == ClearPolicy.NEVER

    @pytest.mark.asyncio
    async def test_clear_for_rebuild_uses_silver_and_gold_policy(
        self, pipeline_config, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run uses SILVER_AND_GOLD policy for rebuild runs."""
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        decision = await orchestrator.clear_for_run()

        assert decision.policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
        mock_lifecycle_service.clear.assert_called_once()
        call_kwargs = mock_lifecycle_service.clear.call_args.kwargs
        assert call_kwargs["policy"].clear_policy == ClearPolicy.SILVER_AND_GOLD

    @pytest.mark.asyncio
    async def test_clear_for_backfill_uses_silver_and_gold_policy(
        self, pipeline_config, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run uses SILVER_AND_GOLD policy for backfill runs."""
        runtime = RuntimeConfig(run_type=RunType.BACKFILL, limit=None)

        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        decision = await orchestrator.clear_for_run()

        assert decision.policy.clear_policy == ClearPolicy.SILVER_AND_GOLD

    @pytest.mark.asyncio
    async def test_clear_uses_default_gold_table(
        self, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run uses default gold table when not configured."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            gold_table=None,
        )
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        orchestrator = LifecycleOrchestrator(
            config=config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await orchestrator.clear_for_run()

        call_kwargs = mock_lifecycle_service.clear.call_args.kwargs
        assert call_kwargs["gold_table"] == "chembl.activity"

    @pytest.mark.asyncio
    async def test_clear_uses_configured_gold_table(
        self, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run uses configured gold table when provided."""
        config = PipelineConfig(
            pipeline_name="test_pipeline",
            provider="chembl",
            entity_type="activity",
            primary_keys=["activity_id"],
            silver_table="test_silver",
            gold_table="custom_gold_table",
        )
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        orchestrator = LifecycleOrchestrator(
            config=config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await orchestrator.clear_for_run()

        call_kwargs = mock_lifecycle_service.clear.call_args.kwargs
        assert call_kwargs["gold_table"] == "custom_gold_table"

    @pytest.mark.asyncio
    async def test_clear_passes_dry_run_flag(
        self, pipeline_config, mock_logger, mock_lifecycle_service
    ):
        """Test clear_for_run passes dry_run flag to service."""
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None, dry_run=True)

        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=mock_lifecycle_service,
        )

        await orchestrator.clear_for_run()

        call_kwargs = mock_lifecycle_service.clear.call_args.kwargs
        assert call_kwargs["dry_run"] is True

    @pytest.mark.asyncio
    async def test_clear_logs_completion(self, lifecycle_orchestrator, mock_logger):
        """Test clear_for_run logs completion message."""
        await lifecycle_orchestrator.clear_for_run()

        mock_logger.debug.assert_called()
        call_args = mock_logger.debug.call_args
        assert "Medallion clear completed" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_clear_returns_decision_with_result(
        self, pipeline_config, mock_logger
    ):
        """Test clear_for_run returns ClearDecision with result."""
        runtime = RuntimeConfig(run_type=RunType.REBUILD, limit=None)

        clear_result = ClearResult(silver_cleared=10, gold_cleared=5, dry_run=False)
        lifecycle_service = MagicMock()
        lifecycle_service.clear = AsyncMock(return_value=clear_result)

        orchestrator = LifecycleOrchestrator(
            config=pipeline_config,
            runtime=runtime,
            logger=mock_logger,
            lifecycle_service=lifecycle_service,
        )

        decision = await orchestrator.clear_for_run()

        assert isinstance(decision, ClearDecision)
        assert decision.result == clear_result
        assert decision.result.silver_cleared == 10
        assert decision.result.gold_cleared == 5


@pytest.mark.unit
class TestClearDecision:
    """Tests for ClearDecision dataclass."""

    def test_clear_decision_creation(self):
        """Test ClearDecision creation."""
        from bioetl.domain.medallion import MedallionPolicy

        result = ClearResult(silver_cleared=5, gold_cleared=3, dry_run=False)
        policy = MedallionPolicy.for_run_type(RunType.REBUILD)

        decision = ClearDecision(result=result, policy=policy)

        assert decision.result == result
        assert decision.policy == policy
        assert decision.policy.clear_policy == ClearPolicy.SILVER_AND_GOLD
