"""Unit tests for FSM state transition logging in CompositePipelineRunner.

Tests verify that:
1. FSM transitions are logged with structured context (from_state, to_state, stage)
2. PipelineEvent.phase_started/phase_completed events are emitted
3. All transitions are covered with appropriate log levels
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError
from bioetl.domain.events import PipelineEvent
from bioetl.domain.locking import FencingToken

if TYPE_CHECKING:
    from collections.abc import Callable

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


class TestPipelineEventPhaseHelpers:
    """Tests for PipelineEvent.phase_started and phase_completed helpers."""

    def test_phase_started_generates_correct_string(self) -> None:
        """Test phase_started generates expected event string."""
        assert PipelineEvent.phase_started("seed") == "seed_started"
        assert PipelineEvent.phase_started("enrichment") == "enrichment_started"
        assert PipelineEvent.phase_started("merge") == "merge_started"

    def test_phase_completed_generates_correct_string(self) -> None:
        """Test phase_completed generates expected event string."""
        assert PipelineEvent.phase_completed("seed") == "seed_completed"
        assert PipelineEvent.phase_completed("enrichment") == "enrichment_completed"
        assert PipelineEvent.phase_completed("merge") == "merge_completed"


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock LoggerPort that tracks all calls."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    logger.debug = MagicMock()
    return logger


@pytest.fixture
def mock_lock() -> AsyncMock:
    """Create a mock LockPort."""
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=_MOCK_TOKEN)
    lock.release = AsyncMock()
    return lock


@pytest.fixture
def mock_key_extractor() -> AsyncMock:
    """Create a mock KeyExtractorService."""
    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=pl.DataFrame(
            {
                "chembl_id": ["CHEMBL1", "CHEMBL2"],
                "doi": ["10.1000/abc", "10.1000/def"],
            }
        )
    )
    return extractor


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    """Create a mock EnrichmentCoordinatorService."""
    coordinator = AsyncMock()
    coordinator.run_enrichers = AsyncMock(
        return_value={
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=2,
                records_enriched=2,
                records_not_found=0,
                duration_seconds=5.0,
            ),
        }
    )
    return coordinator


@pytest.fixture
def mock_merger() -> AsyncMock:
    """Create a mock MergeService."""
    merger = AsyncMock()
    merge_call = AsyncMock(
        return_value=MergeResult(
            records_merged=2,
            records_from_seed=2,
            records_enriched=2,
            records_fully_enriched=2,
            sources_used=("seed", "crossref"),
        )
    )
    merger.merge = merge_call
    merger.execute_request = merge_call
    return merger


@pytest.fixture
def mock_checkpoint_manager() -> AsyncMock:
    """Create a mock CompositeCheckpointManager."""
    manager = AsyncMock()
    manager._saved_states: list[CompositeCheckpointState] = []

    async def load_impl() -> CompositeCheckpointState:
        await asyncio.sleep(0)
        return CompositeCheckpointState(
            composite_name="test_composite",
            run_id="00000000-0000-0000-0000-000000000123",
            state=CompositePipelineState.NOT_STARTED,
            created_at=datetime.now(tz=UTC),
        )

    async def save_impl(state: CompositeCheckpointState) -> None:
        await asyncio.sleep(0)
        manager._saved_states.append(state)

    manager.load = AsyncMock(side_effect=load_impl)
    manager.save = AsyncMock(side_effect=save_impl)
    manager.delete = AsyncMock()

    return manager


@pytest.fixture
def mock_seed_runner_factory() -> Callable[[], MagicMock]:
    """Create a mock seed runner factory."""

    def factory() -> MagicMock:
        runner = MagicMock()
        runner.run = AsyncMock()
        executor = MagicMock()
        executor.records_fetched = 100
        executor.records_silver = 95
        runner._executor = executor
        runner.execution_metrics = {
            "records_fetched": 100,
            "records_silver": 95,
        }
        return runner

    return factory


@pytest.fixture
def mock_enricher_runner_factory() -> Callable[[str, pl.DataFrame], MagicMock]:
    """Create a mock enricher runner factory."""

    def factory(name: str, keys: pl.DataFrame) -> MagicMock:
        runner = MagicMock()
        runner.run = AsyncMock()
        executor = MagicMock()
        executor.records_silver = len(keys)
        executor.records_quarantined = 0
        runner._executor = executor
        runner.execution_metrics = {
            "records_silver": len(keys),
            "records_quarantined": 0,
        }
        return runner

    return factory


@pytest.fixture
def sample_composite_config() -> MagicMock:
    """Create a sample CompositeConfig."""
    config = MagicMock()
    config.name = "test_composite"
    config.lock_key = "composite:test_composite"

    config.seed = MagicMock()
    config.seed.pipeline = "chembl_activity"
    config.seed.silver_table = "silver/chembl/activity"
    config.seed.output_keys = ("chembl_id", "doi")

    enricher = MagicMock()
    enricher.pipeline = "crossref"
    enricher.required = True
    enricher.silver_table = "silver/crossref/publication"
    config.enrichers = [enricher]
    config.required_enrichers = ["crossref"]

    config.merge = MagicMock()
    config.merge.output_silver_path = "silver/composite/test"
    config.merge.output_gold_path = "gold/test_composite"

    config.dq = MagicMock()
    config.dq.soft_fail_threshold = 0.05
    config.dq.hard_fail_threshold = 0.20

    return config


@pytest.fixture
def runner(
    sample_composite_config,
    mock_seed_runner_factory,
    mock_enricher_runner_factory,
    mock_key_extractor,
    mock_coordinator,
    mock_merger,
    mock_checkpoint_manager,
    mock_logger,
    mock_lock,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner instance for testing."""
    deps = CompositeRunnerDependencies(
        seed_runner_factory=mock_seed_runner_factory,
        enricher_runner_factory=mock_enricher_runner_factory,
        key_extractor=mock_key_extractor,
        coordinator=mock_coordinator,
        merger=mock_merger,
        checkpoint_manager=mock_checkpoint_manager,
        logger=mock_logger,
        lock=mock_lock,
        fsm_state_helper=FSMStateHelperService(
            config=sample_composite_config,
            logger=mock_logger,
            run_id="00000000-0000-0000-0000-000000000123",
        ),
    )
    return CompositePipelineRunner(
        config=sample_composite_config,
        runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
        deps=deps,
        run_id="00000000-0000-0000-0000-000000000123",
    )


@pytest.mark.unit
class TestFSMTransitionLogging:
    """Tests for FSM state transition logging."""

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_seed_running(
        self, runner, mock_logger
    ) -> None:
        """Test FSM transition to SEED_RUNNING is logged."""
        await runner.run()

        # Find FSM transition log for SEED_RUNNING
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        seed_running_calls = [
            c for c in fsm_calls if "seed_running" in str(c.kwargs.get("to_state", ""))
        ]
        assert len(seed_running_calls) >= 1, "Should log FSM transition to SEED_RUNNING"

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_seed_completed(
        self, runner, mock_logger
    ) -> None:
        """Test FSM transition to SEED_COMPLETED is logged."""
        await runner.run()

        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        seed_completed_calls = [
            c
            for c in fsm_calls
            if "seed_completed" in str(c.kwargs.get("to_state", ""))
        ]
        assert len(seed_completed_calls) >= 1, (
            "Should log FSM transition to SEED_COMPLETED"
        )
        assert any(
            c.kwargs.get("from_state") == "seed_running"
            and c.kwargs.get("to_state") == "seed_completed"
            for c in seed_completed_calls
        ), (
            "Seed completion transition should be logged as seed_running -> seed_completed"
        )

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_enriching(self, runner, mock_logger) -> None:
        """Test FSM transition to ENRICHING is logged."""
        await runner.run()

        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        enriching_calls = [
            c for c in fsm_calls if "enriching" in str(c.kwargs.get("to_state", ""))
        ]
        assert len(enriching_calls) >= 1, "Should log FSM transition to ENRICHING"

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_enrichment_completed(
        self, runner, mock_logger
    ) -> None:
        """Test FSM transition to ENRICHMENT_COMPLETED is logged."""
        await runner.run()

        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        completed_calls = [
            c
            for c in fsm_calls
            if "enrichment_completed" in str(c.kwargs.get("to_state", ""))
        ]
        assert len(completed_calls) >= 1, (
            "Should log FSM transition to ENRICHMENT_COMPLETED"
        )

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_merging(self, runner, mock_logger) -> None:
        """Test FSM transition to MERGING is logged."""
        await runner.run()

        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        merging_calls = [
            c for c in fsm_calls if "merging" in str(c.kwargs.get("to_state", ""))
        ]
        assert len(merging_calls) >= 1, "Should log FSM transition to MERGING"

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_completed(self, runner, mock_logger) -> None:
        """Test FSM transition to COMPLETED is logged."""
        await runner.run()

        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        completed_calls = [
            c for c in fsm_calls if c.kwargs.get("to_state") == "completed"
        ]
        assert len(completed_calls) >= 1, "Should log FSM transition to COMPLETED"

    @pytest.mark.asyncio
    async def test_fsm_transition_includes_context_fields(
        self, runner, mock_logger
    ) -> None:
        """Test FSM transition logs include required context fields."""
        await runner.run()

        # Find any FSM transition log
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        assert len(fsm_calls) > 0, "Should have FSM transition logs"

        # Check that required fields are present in at least one call
        for fsm_call in fsm_calls:
            kwargs = fsm_call.kwargs
            assert "from_state" in kwargs, "FSM log should include from_state"
            assert "to_state" in kwargs, "FSM log should include to_state"
            assert "composite" in kwargs, "FSM log should include composite"
            assert "run_id" in kwargs, "FSM log should include run_id"
            assert "stage" in kwargs, "FSM log should include stage"


@pytest.mark.unit
class TestPhaseEventLogging:
    """Tests for PipelineEvent.phase_started/phase_completed logging."""

    @pytest.mark.asyncio
    async def test_logs_seed_started_phase_event(self, runner, mock_logger) -> None:
        """Test seed_started phase event is logged."""
        await runner.run()

        seed_started_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "seed_started" in str(c.args[0])
        ]
        assert len(seed_started_calls) >= 1, "Should log seed_started phase event"

    @pytest.mark.asyncio
    async def test_logs_seed_completed_phase_event(self, runner, mock_logger) -> None:
        """Test seed_completed phase event is logged."""
        await runner.run()

        seed_completed_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "seed_completed" in str(c.args[0])
        ]
        assert len(seed_completed_calls) >= 1, "Should log seed_completed phase event"

    @pytest.mark.asyncio
    async def test_logs_enrichment_started_phase_event(
        self, runner, mock_logger
    ) -> None:
        """Test enrichment_started phase event is logged."""
        await runner.run()

        enrichment_started_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "enrichment_started" in str(c.args[0])
        ]
        assert len(enrichment_started_calls) >= 1, (
            "Should log enrichment_started phase event"
        )

    @pytest.mark.asyncio
    async def test_logs_enrichment_completed_phase_event(
        self, runner, mock_logger
    ) -> None:
        """Test enrichment_completed phase event is logged."""
        await runner.run()

        enrichment_completed_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "enrichment_completed" in str(c.args[0])
        ]
        assert len(enrichment_completed_calls) >= 1, (
            "Should log enrichment_completed phase event"
        )

    @pytest.mark.asyncio
    async def test_logs_merge_started_phase_event(self, runner, mock_logger) -> None:
        """Test merge_started phase event is logged."""
        await runner.run()

        merge_started_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "merge_started" in str(c.args[0])
        ]
        assert len(merge_started_calls) >= 1, "Should log merge_started phase event"

    @pytest.mark.asyncio
    async def test_logs_merge_completed_phase_event(self, runner, mock_logger) -> None:
        """Test merge_completed phase event is logged."""
        await runner.run()

        merge_completed_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "merge_completed" in str(c.args[0])
        ]
        assert len(merge_completed_calls) >= 1, "Should log merge_completed phase event"


@pytest.mark.unit
class TestFSMFailureLogging:
    """Tests for FSM FAILED state transition logging."""

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_failed_on_merge_error(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ) -> None:
        """Test FSM transition to FAILED is logged when merge fails."""
        mock_merger = AsyncMock()
        merge_call = AsyncMock(side_effect=RuntimeError("Merge failed: disk full"))
        mock_merger.merge = merge_call
        mock_merger.execute_request = merge_call

        deps = CompositeRunnerDependencies(
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=sample_composite_config,
                logger=mock_logger,
                run_id="00000000-0000-0000-0000-000000000123",
            ),
        )
        runner = CompositePipelineRunner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            deps=deps,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(RuntimeError, match="Merge failed"):
            await runner.run()

        # Check for FSM transition to FAILED
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        failed_calls = [c for c in fsm_calls if c.kwargs.get("to_state") == "failed"]
        assert len(failed_calls) >= 1, "Should log FSM transition to FAILED"

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_failed_on_required_enricher_failure(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ) -> None:
        """Test FSM transition to FAILED logged when required enricher fails."""
        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="Connection timeout",
                    records_input=2,
                ),
            }
        )

        deps = CompositeRunnerDependencies(
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=sample_composite_config,
                logger=mock_logger,
                run_id="00000000-0000-0000-0000-000000000123",
            ),
        )
        runner = CompositePipelineRunner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            deps=deps,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(InvalidStateError, match="Required enricher"):
            await runner.run()

        # Check for FSM transition to FAILED
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        failed_calls = [c for c in fsm_calls if c.kwargs.get("to_state") == "failed"]
        assert len(failed_calls) >= 1, "Should log FSM transition to FAILED"

        # Check that stage indicates required enricher failure
        assert any(
            c.kwargs.get("stage") == "required_enricher_failed" for c in failed_calls
        ), "Stage should indicate required_enricher_failed"

    @pytest.mark.asyncio
    async def test_logs_fsm_transition_to_failed_on_seed_error(
        self,
        sample_composite_config,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ) -> None:
        """Test FSM transition to FAILED is logged when seed fails."""

        def failing_seed_factory() -> MagicMock:
            runner = MagicMock()
            runner.run = AsyncMock(side_effect=RuntimeError("Seed failed: API error"))
            return runner

        deps = CompositeRunnerDependencies(
            seed_runner_factory=failing_seed_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=sample_composite_config,
                logger=mock_logger,
                run_id="00000000-0000-0000-0000-000000000123",
            ),
        )
        runner = CompositePipelineRunner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            deps=deps,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(RuntimeError, match="Seed failed"):
            await runner.run()

        # Check for FSM transition to FAILED
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        failed_calls = [c for c in fsm_calls if c.kwargs.get("to_state") == "failed"]
        assert len(failed_calls) >= 1, "Should log FSM transition to FAILED"

        # Check that stage indicates seed failure
        assert any(c.kwargs.get("stage") == "seed_failed" for c in failed_calls), (
            "Stage should indicate seed_failed"
        )


@pytest.mark.unit
class TestDryRunLogging:
    """Tests for dry run mode FSM logging."""

    @pytest.mark.asyncio
    async def test_logs_dry_run_skip_merge_transition(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ) -> None:
        """Test dry run logs FSM transition directly to COMPLETED."""
        deps = CompositeRunnerDependencies(
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=sample_composite_config,
                logger=mock_logger,
                run_id="00000000-0000-0000-0000-000000000123",
            ),
        )
        runner = CompositePipelineRunner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=True),
            deps=deps,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        await runner.run()

        # Check for dry run skip merge FSM transition
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        dry_run_calls = [
            c for c in fsm_calls if c.kwargs.get("stage") == "dry_run_skip_merge"
        ]
        assert len(dry_run_calls) >= 1, "Should log FSM transition for dry run skip"

        # Verify merge was NOT called
        mock_merger.merge.assert_not_called()


@pytest.mark.unit
class TestNoEnrichersLogging:
    """Tests for FSM logging when no enrichers to run."""

    @pytest.mark.asyncio
    async def test_logs_enrichment_empty_transition(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ) -> None:
        """Test FSM logs transition for empty enrichment stage."""
        sample_composite_config.enrichers = []
        sample_composite_config.required_enrichers = []

        deps = CompositeRunnerDependencies(
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=mock_checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=sample_composite_config,
                logger=mock_logger,
                run_id="00000000-0000-0000-0000-000000000123",
            ),
        )
        runner = CompositePipelineRunner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            deps=deps,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        await runner.run()

        # Check for FSM transition with empty enrichment stage
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        empty_enrichment_calls = [
            c for c in fsm_calls if c.kwargs.get("stage") == "enrichment_start_empty"
        ]
        assert len(empty_enrichment_calls) >= 1, (
            "Should log FSM transition for empty enrichment"
        )

        # Verify reason is included
        assert any(
            c.kwargs.get("reason") == "no_enrichers_to_run"
            for c in empty_enrichment_calls
        ), "Should include reason for empty enrichment"
