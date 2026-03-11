"""Unit tests for CompositePipelineRunner FSM state transitions.

Tests for FSM state management during merge and completion phases.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointState,
)
from bioetl.infrastructure.storage.composite_checkpoint_writer import (
    FileCompositeCheckpointWriter,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.locking import FencingToken

if TYPE_CHECKING:
    from pathlib import Path

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


@pytest.fixture
def test_run_id() -> str:
    """Generate a valid UUID for test run ID."""
    return str(uuid4())


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_lock() -> AsyncMock:
    """Create a mock lock."""
    lock = AsyncMock()
    lock.acquire.return_value = _MOCK_TOKEN
    lock.release.return_value = True
    return lock


@pytest.fixture
def mock_merger() -> AsyncMock:
    """Create a mock merger service."""
    merger = AsyncMock()
    merger.merge.return_value = MergeResult(
        records_from_seed=100,
        records_merged=95,
        records_enriched=80,
        records_fully_enriched=70,
        sources_used=("crossref", "pubmed"),
        output_silver_path="silver/composite/test",
        output_gold_path="gold/test_enriched",
        duration_seconds=5.0,
    )
    return merger


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    """Create a mock enrichment coordinator."""
    coordinator = AsyncMock()
    coordinator.run_enrichers.return_value = {
        "crossref": EnrichmentResult.success(
            enricher_name="crossref",
            records_input=100,
            records_enriched=95,
            records_not_found=5,
            duration_seconds=10.0,
        ),
    }
    return coordinator


@pytest.fixture
def mock_key_extractor() -> AsyncMock:
    """Create a mock key extractor service."""
    extractor = AsyncMock()
    extractor.extract.return_value = pl.DataFrame({"doi": ["10.1234/test"]})
    return extractor


@pytest.fixture
def mock_seed_runner() -> AsyncMock:
    """Create a mock seed runner."""
    runner = AsyncMock()
    runner.run.return_value = None
    runner._executor = MagicMock(records_fetched=100, records_silver=95)
    runner.execution_metrics = {
        "records_fetched": 100,
        "records_silver": 95,
    }
    return runner


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock composite config."""
    config = MagicMock()
    config.name = "test_composite"
    config.lock_key = "composite:test_composite"
    config.seed.pipeline = "chembl_activity"
    config.seed.silver_table = "silver/chembl/activity"
    config.seed.output_keys = ("doi",)
    config.enrichers = []
    config.required_enrichers = []
    config.merge.output_silver_path = "silver/composite/test"
    config.merge.output_gold_path = "gold/test_enriched"
    config.dq.soft_fail_threshold = 0.05
    config.dq.hard_fail_threshold = 0.20
    return config


class TestFSMMergeStateTransitions:
    """Tests for FSM state transitions during merge phase."""

    @pytest.mark.asyncio
    async def test_transitions_to_merging_before_merge(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """Runner should transition to MERGING state before merge operation."""
        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=False,
        )

        # Track saved states
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        await runner.run()

        # Verify MERGING state was saved before merge
        assert CompositePipelineState.MERGING in saved_states
        # Verify COMPLETED state was saved after merge
        assert CompositePipelineState.COMPLETED in saved_states
        # Verify order: MERGING comes before COMPLETED
        merging_idx = saved_states.index(CompositePipelineState.MERGING)
        completed_idx = saved_states.index(CompositePipelineState.COMPLETED)
        assert merging_idx < completed_idx

    @pytest.mark.asyncio
    async def test_transitions_to_failed_on_merge_error(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """Runner should transition to FAILED state when merge fails."""
        # Make merge fail
        mock_merger.merge.side_effect = RuntimeError("Merge failed: disk full")

        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=False,
        )

        # Track saved states
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        with pytest.raises(RuntimeError, match="Merge failed"):
            await runner.run()

        # Verify FAILED state was saved
        assert CompositePipelineState.FAILED in saved_states
        # Verify MERGING was set before FAILED
        merging_idx = saved_states.index(CompositePipelineState.MERGING)
        failed_idx = saved_states.index(CompositePipelineState.FAILED)
        assert merging_idx < failed_idx


class TestFSMDryRunMode:
    """Tests for FSM state transitions in dry run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_skips_merging_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """In dry run mode, merge should be skipped but COMPLETED should be set."""
        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=False,
        )

        # Track saved states
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=True),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        result = await runner.run()

        # Verify merge was not called
        mock_merger.merge.assert_not_called()
        # Verify MERGING state was NOT saved (dry run skips merge)
        assert CompositePipelineState.MERGING not in saved_states
        # Verify COMPLETED state was saved
        assert CompositePipelineState.COMPLETED in saved_states
        # Verify result has no merge_result
        assert result.merge_result is None


class TestFSMEnrichmentCompletedTransition:
    """Tests for ENRICHMENT_COMPLETED state transition."""

    @pytest.mark.asyncio
    async def test_transitions_through_enriching_to_enrichment_completed(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """When no enrichers run, should transition through ENRICHING to ENRICHMENT_COMPLETED."""
        # Configure no enrichers
        mock_coordinator.run_enrichers.return_value = {}

        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=False,
        )

        # Track saved states
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        await runner.run()

        # Verify ENRICHMENT_COMPLETED state was saved
        assert CompositePipelineState.ENRICHMENT_COMPLETED in saved_states
        # Verify full progression
        assert CompositePipelineState.SEED_COMPLETED in saved_states
        assert CompositePipelineState.MERGING in saved_states
        assert CompositePipelineState.COMPLETED in saved_states


class TestFSMResumeFromFailed:
    """Tests for resuming from FAILED state."""

    @pytest.mark.asyncio
    async def test_resume_from_failed_retries_merge(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """When resuming from FAILED state, should retry merge."""
        # Create a checkpoint in FAILED state with completed seed and enrichers
        failed_checkpoint = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
            },
            created_at=datetime.now(tz=UTC),
        )

        # Write checkpoint to file
        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=True,
        )
        await checkpoint_manager.save(failed_checkpoint)

        # Track saved states
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False, resume=True),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        await runner.run()

        # Verify seed was not re-run (resumed from checkpoint)
        mock_seed_runner.run.assert_not_called()
        # Verify merge was called
        mock_merger.merge.assert_called_once()
        # Verify COMPLETED state was reached
        assert CompositePipelineState.COMPLETED in saved_states


class TestFSMCheckpointDeletion:
    """Tests for checkpoint deletion error handling."""

    @pytest.mark.asyncio
    async def test_checkpoint_delete_error_is_non_fatal(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        tmp_path: Path,
        test_run_id: str,
    ) -> None:
        """Checkpoint deletion error should not fail the pipeline."""
        checkpoint_manager = CompositeCheckpointManager(
            composite_name="test_composite",
            run_id=test_run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=mock_logger,
            resume=False,
        )

        # Make delete fail
        async def failing_delete() -> None:
            raise PermissionError("Cannot delete checkpoint")

        checkpoint_manager.delete = failing_delete  # type: ignore[method-assign]

        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            seed_runner_factory=lambda: mock_seed_runner,
            enricher_runner_factory=lambda name, df: AsyncMock(),
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
            run_id=test_run_id,
        )

        # Should not raise despite delete failing
        result = await runner.run()

        # Verify result is still returned
        assert result is not None
        assert result.composite_name == "test_composite"
        # Verify warning was logged
        mock_logger.warning.assert_called()


class TestFSMFailedStateIsResumable:
    """Tests that FAILED state is resumable."""

    def test_failed_state_is_resumable(self) -> None:
        """FAILED state should be resumable for merge retry."""
        assert CompositePipelineState.FAILED.is_resumable is True

    def test_checkpoint_with_failed_state_is_resumable(self) -> None:
        """Checkpoint with FAILED state should be resumable."""
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=True,
        )
        assert state.is_resumable is True
