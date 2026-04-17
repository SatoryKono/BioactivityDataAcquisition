"""Unit tests for CompositePipelineRunner FSM state transitions.

Tests for FSM state management during merge and completion phases.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from collections.abc import Callable
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import RecoverableError
from bioetl.domain.locking import FencingToken

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


class InMemoryCheckpointManager:
    """Minimal checkpoint manager fake for CompositePipelineRunner unit tests."""

    expected_effective_config_hash = ""
    expected_contract_ref = ""
    expected_contract_version = ""
    expected_manifest_id = ""

    def __init__(
        self,
        *,
        composite_name: str,
        run_id: str,
        logger: MagicMock,
        resume: bool = False,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id
        self._logger = logger
        self._resume = resume
        self._state = CompositeCheckpointState(
            composite_name=composite_name,
            run_id=run_id,
            created_at=datetime.now(tz=UTC),
        )

    async def load(self) -> CompositeCheckpointState:
        await asyncio.sleep(0)
        return self._state

    async def save(self, state: CompositeCheckpointState) -> None:
        await asyncio.sleep(0)
        self._state = state

    async def delete(self) -> None:
        await asyncio.sleep(0)
        return None

    async def delete_orphaned(self) -> int:
        await asyncio.sleep(0)
        return 0

    async def list_all(self) -> list[str]:
        await asyncio.sleep(0)
        return []


def create_checkpoint_manager(
    *,
    composite_name: str,
    run_id: str,
    logger: MagicMock,
    resume: bool = False,
) -> InMemoryCheckpointManager:
    """Create a lightweight checkpoint manager without filesystem I/O."""
    return InMemoryCheckpointManager(
        composite_name=composite_name,
        run_id=run_id,
        logger=logger,
        resume=resume,
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
    merge_call = AsyncMock(
        return_value=MergeResult(
            records_from_seed=100,
            records_merged=95,
            records_enriched=80,
            records_fully_enriched=70,
            sources_used=("crossref", "pubmed"),
            output_silver_path="silver/composite/test",
            output_gold_path="gold/test_enriched",
            duration_seconds=5.0,
        )
    )
    merger.merge = merge_call
    merger.execute_request = merge_call
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


def _seed_runner_factory(seed_runner: AsyncMock) -> Callable[[], AsyncMock]:
    """Return a zero-argument factory for the configured seed runner."""

    def _factory() -> AsyncMock:
        return seed_runner

    return _factory


def _enricher_runner_factory(name: str, df: pl.DataFrame) -> AsyncMock:
    """Return a fresh enricher stub for runner dependencies."""
    return AsyncMock()


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
        test_run_id: str,
    ) -> None:
        """Runner should transition to MERGING state before merge operation."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
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
        test_run_id: str,
    ) -> None:
        """Runner should transition to FAILED state when merge fails."""
        # Make merge fail
        mock_merger.merge.side_effect = RuntimeError("Merge failed: disk full")

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
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

    def test_handle_dry_run_merge_skip_preserves_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dry-run merge skip helper should only log and keep checkpoint state intact."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=True),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.ENRICHMENT_COMPLETED,
        )

        next_state = runner._handle_dry_run_merge_skip(state)

        assert next_state is state
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        assert any(c.kwargs.get("stage") == "dry_run_skip_merge" for c in fsm_calls)

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
        test_run_id: str,
    ) -> None:
        """In dry run mode, merge should be skipped but COMPLETED should be set."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=True),
            deps=deps,
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


class TestMergeInputPolicy:
    """Tests for mergeable input selection policy."""

    def test_build_merge_inputs_filters_non_mergeable_results(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Merge stage should keep only mergeable enricher/dependency inputs."""
        enricher_ok = MagicMock()
        enricher_ok.pipeline = "crossref"
        enricher_skip = MagicMock()
        enricher_skip.pipeline = "openalex"
        dep_ok = MagicMock()
        dep_ok.pipeline = "pubmed"
        dep_ok.silver_table = "silver/pubmed"
        dep_missing_table = MagicMock()
        dep_missing_table.pipeline = "semanticscholar"
        dep_missing_table.silver_table = ""
        dep_failed = MagicMock()
        dep_failed.pipeline = "uniprot"
        dep_failed.silver_table = "silver/uniprot"

        mock_config.enrichers = [enricher_ok, enricher_skip]
        mock_config.dependencies = [dep_ok, dep_missing_table, dep_failed]

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )

        prepared_inputs = runner._build_merge_inputs(
            {
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
                "openalex": EnrichmentResult.not_run(
                    enricher_name="openalex",
                    reason="Skipped due to required_only mode",
                ),
            },
            {
                "pubmed": DependencyResult.success(
                    pipeline_name="pubmed",
                    records_extracted=100,
                    records_silver=95,
                ),
                "semanticscholar": DependencyResult.success(
                    pipeline_name="semanticscholar",
                    records_extracted=50,
                    records_silver=45,
                ),
                "uniprot": DependencyResult.failed(
                    pipeline_name="uniprot",
                    error_message="dependency failed",
                ),
            },
        )

        assert [cfg.pipeline for cfg in prepared_inputs.enrichers] == ["crossref"]
        assert [cfg.pipeline for cfg in prepared_inputs.dependencies] == ["pubmed"]

    def test_transition_to_merging_state_sets_merge_state_and_logs_transition(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Merge transition helper should return MERGING state and emit merge_start FSM log."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.ENRICHMENT_COMPLETED,
        )

        next_state = runner._transition_to_merging_state(state)

        assert next_state.state == CompositePipelineState.MERGING
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        assert any(c.kwargs.get("stage") == "merge_start" for c in fsm_calls)


class TestFSMEnrichmentCompletedTransition:
    """Tests for ENRICHMENT_COMPLETED state transition."""

    @pytest.mark.asyncio
    async def test_skip_enrichment_stage_keeps_state_and_returns_empty_results(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Skip helper should keep checkpoint state and return no enrichment results."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.SEED_COMPLETED,
        )

        next_state, enrichment_results = await runner._skip_enrichment_stage(state)

        assert next_state is state
        assert enrichment_results == {}
        mock_logger.info.assert_called_once_with(
            "No enrichers to run, skipping enrichment stage",
            composite="test_composite",
            reason="all_completed_or_filtered",
        )

    def test_transition_to_empty_enrichment_start_sets_enriching_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Empty enrichment start helper should move state to ENRICHING and log the stage."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.SEED_COMPLETED,
        )

        next_state = runner._transition_to_empty_enrichment_start(state)

        assert next_state.state == CompositePipelineState.ENRICHING
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        assert any(c.kwargs.get("stage") == "enrichment_start_empty" for c in fsm_calls)

    @pytest.mark.asyncio
    async def test_complete_enrichment_stage_persists_completed_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Enrichment completion helper should save and log the completed enrichment stage."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.ENRICHING,
        )
        runner._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

        next_state = await runner._complete_enrichment_stage(state)

        assert next_state.state == CompositePipelineState.ENRICHMENT_COMPLETED
        runner._save_checkpoint_safe.assert_awaited_once_with(
            next_state,
            "enrichment_completed",
        )
        assert any(
            c.args and c.args[0] == "enrichment_completed"
            for c in mock_logger.info.call_args_list
        )

    def test_record_completed_enrichment_results_keeps_success_and_skipped_only(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Enrichment result recording helper should persist only success/skipped results."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.ENRICHING,
        )

        next_state = runner._record_completed_enrichment_results(
            state,
            {
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=1.0,
                ),
                "openalex": EnrichmentResult.skipped(
                    enricher_name="openalex",
                    reason="Skipped by coordinator",
                ),
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed",
                    error_message="upstream failed",
                ),
            },
        )

        assert set(next_state.completed_enrichers) == {"crossref", "openalex"}
        assert next_state.enrichment_results["crossref"].is_success
        assert (
            next_state.enrichment_results["openalex"].status == EnrichmentStatus.SKIPPED
        )
        assert "pubmed" not in next_state.completed_enrichers

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
        test_run_id: str,
    ) -> None:
        """When no enrichers run, should transition through ENRICHING to ENRICHMENT_COMPLETED."""
        # Configure no enrichers
        mock_coordinator.run_enrichers.return_value = {}

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )

        await runner.run()

        # Verify ENRICHMENT_COMPLETED state was saved
        assert CompositePipelineState.ENRICHMENT_COMPLETED in saved_states
        # Verify full progression
        assert CompositePipelineState.SEED_COMPLETED in saved_states
        assert CompositePipelineState.MERGING in saved_states
        assert CompositePipelineState.COMPLETED in saved_states


class TestFSMDependenciesCompletedTransition:
    """Tests for DEPENDENCIES_COMPLETED state transition."""

    def test_prepare_dependencies_run_context_returns_runner_and_pipeline_names(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependency run-context helper should return runtime collaborators and dependency names."""
        dep_pubmed = MagicMock()
        dep_pubmed.pipeline = "pubmed"
        dep_crossref = MagicMock()
        dep_crossref.pipeline = "crossref"
        mock_config.dependencies = [dep_pubmed, dep_crossref]

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        runner._dependency_coordinator = mock_coordinator  # type: ignore[attr-defined]
        runner._dependencies_runner_factory = MagicMock()  # type: ignore[attr-defined]

        prepared_context = runner._prepare_dependencies_run_context()

        assert prepared_context.coordinator is runner._dependency_coordinator
        assert prepared_context.runner_factory is runner._dependencies_runner_factory
        assert prepared_context.dependency_pipeline_names == ["pubmed", "crossref"]

    @pytest.mark.asyncio
    async def test_run_dependencies_delegates_to_coordinator_with_state_context(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependency run helper should delegate to coordinator with configured dependencies and completed state."""
        dep_pubmed = MagicMock()
        dep_pubmed.pipeline = "pubmed"
        mock_config.dependencies = [dep_pubmed]

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
            completed_dependencies=frozenset({"crossref"}),
        )
        runner_factory = MagicMock()
        runner._dependency_coordinator = mock_coordinator  # type: ignore[attr-defined]
        runner._dependencies_runner_factory = runner_factory  # type: ignore[attr-defined]
        keys_df = pl.DataFrame({"doi": ["10.1234/test"]})
        expected_results = {
            "pubmed": DependencyResult.success(
                pipeline_name="pubmed",
                records_extracted=100,
                records_silver=95,
            )
        }
        mock_coordinator.run_dependencies.return_value = expected_results
        prepared_context = runner._prepare_dependencies_run_context()

        dependency_results = await runner._run_dependencies(
            context=prepared_context,
            keys_df=keys_df,
            state=state,
        )

        assert dependency_results == expected_results
        mock_coordinator.run_dependencies.assert_awaited_once_with(
            keys=keys_df,
            dependencies=mock_config.dependencies,
            completed=state.completed_dependencies,
            runner_factory=runner_factory,
        )

    @pytest.mark.asyncio
    async def test_skip_dependencies_phase_keeps_state_and_returns_empty_results(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependencies skip helper should keep checkpoint state and return no results."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.SEED_COMPLETED,
        )

        next_state, dependency_results = await runner._skip_dependencies_phase(state)

        assert next_state is state
        assert dependency_results == {}

    @pytest.mark.asyncio
    async def test_start_dependencies_phase_persists_running_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependencies start helper should save and log the running dependencies stage."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.SEED_COMPLETED,
        )
        runner._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]
        dep_pubmed = MagicMock()
        dep_pubmed.pipeline = "pubmed"
        dep_crossref = MagicMock()
        dep_crossref.pipeline = "crossref"
        mock_config.dependencies = [dep_pubmed, dep_crossref]
        runner._dependency_coordinator = mock_coordinator  # type: ignore[attr-defined]
        runner._dependencies_runner_factory = MagicMock()  # type: ignore[attr-defined]
        prepared_context = runner._prepare_dependencies_run_context()

        next_state = await runner._start_dependencies_phase(
            state,
            context=prepared_context,
        )

        assert next_state.state == CompositePipelineState.DEPENDENCIES_RUNNING
        runner._save_checkpoint_safe.assert_awaited_once_with(
            next_state,
            "dependencies_running",
        )
        assert any(
            c.args and c.args[0] == "dependencies_started"
            for c in mock_logger.info.call_args_list
        )

    @pytest.mark.asyncio
    async def test_complete_dependencies_phase_persists_completed_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependencies completion helper should save and log the completed dependencies stage."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
        )
        runner._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

        next_state = await runner._complete_dependencies_phase(
            state,
            succeeded=2,
            failed=1,
        )

        assert next_state.state == CompositePipelineState.DEPENDENCIES_COMPLETED
        runner._save_checkpoint_safe.assert_awaited_once_with(
            next_state,
            "dependencies_completed",
        )
        assert any(
            c.args and c.args[0] == "dependencies_completed"
            for c in mock_logger.info.call_args_list
        )

    @pytest.mark.asyncio
    async def test_postprocess_dependency_results_records_successes_then_completes(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Dependency postprocess helper should record successful results and finalize the stage."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.DEPENDENCIES_RUNNING,
        )
        runner._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]
        dependency_results = {
            "pubmed": DependencyResult.success(
                pipeline_name="pubmed",
                records_extracted=100,
                records_silver=95,
            )
        }

        next_state, returned_results = await runner._postprocess_dependency_results(
            state,
            dependency_results,
        )

        assert returned_results == dependency_results
        assert next_state.state == CompositePipelineState.DEPENDENCIES_COMPLETED
        assert next_state.completed_dependencies == frozenset({"pubmed"})
        runner._save_checkpoint_safe.assert_awaited_once_with(
            next_state,
            "dependencies_completed",
        )


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
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False, resume=True),
            deps=deps,
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
    async def test_delete_checkpoint_safe_logs_reason_code_for_bioetl_error(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """BioETL delete errors should log checkpoint_delete_failed reason code."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        async def failing_delete() -> None:
            await asyncio.sleep(0)
            raise RecoverableError("checkpoint cleanup unavailable")

        checkpoint_manager.delete = failing_delete  # type: ignore[method-assign]

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )

        await runner._delete_checkpoint_safe()

        mock_logger.warning.assert_called_once()
        assert (
            mock_logger.warning.call_args.kwargs["reason_code"]
            == "checkpoint_delete_failed"
        )

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
        test_run_id: str,
    ) -> None:
        """Checkpoint deletion error should not fail the pipeline."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        # Make delete fail
        async def failing_delete() -> None:
            await asyncio.sleep(0)
            raise PermissionError("Cannot delete checkpoint")

        checkpoint_manager.delete = failing_delete  # type: ignore[method-assign]

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )

        # Should not raise despite delete failing
        result = await runner.run()

        # Verify result is still returned
        assert result is not None
        assert result.composite_name == "test_composite"
        # Verify warning was logged
        mock_logger.warning.assert_called()


class TestFinalizationPolicy:
    """Tests for finalization state transition policy."""

    def test_transition_to_completed_state_is_noop_for_completed_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Already completed checkpoints should not emit another FSM transition."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.COMPLETED,
        )

        next_state = runner._transition_to_completed_state(state)

        assert next_state is state
        fsm_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "FSM state transition" in str(c.args[0])
        ]
        assert not any(c.kwargs.get("stage") == "pipeline_complete" for c in fsm_calls)

    @pytest.mark.asyncio
    async def test_persist_completed_state_uses_completed_operation(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Completed-state persistence should always use the completed checkpoint op."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.COMPLETED,
        )
        runner._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

        await runner._persist_completed_state(state)

        runner._save_checkpoint_safe.assert_awaited_once_with(state, "completed")

    @pytest.mark.asyncio
    async def test_handle_merge_success_orders_side_effects(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Merge success should log first, then run DQ reports and quarantine writes."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(mock_seed_runner),
            enricher_runner_factory=_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            checkpoint_manager=checkpoint_manager,
            logger=mock_logger,
            lock=mock_lock,
            fsm_state_helper=FSMStateHelperService(
                config=mock_config, logger=mock_logger, run_id=test_run_id
            ),
        )
        runner = CompositePipelineRunner(
            config=mock_config,
            runtime=CompositeRuntimeConfig(dry_run=False),
            deps=deps,
            run_id=test_run_id,
        )
        merge_result = MergeResult(
            records_from_seed=100,
            records_merged=95,
            records_enriched=80,
            records_fully_enriched=70,
            duration_seconds=5.0,
        )
        call_order: list[str] = []

        def log_info(*args: object, **kwargs: object) -> None:
            if args and args[0] == "merge_completed":
                call_order.append("log")

        async def generate_reports(result: MergeResult) -> None:
            await asyncio.sleep(0)
            assert result is merge_result
            call_order.append("dq")

        async def write_quarantine(result: MergeResult) -> None:
            await asyncio.sleep(0)
            assert result is merge_result
            call_order.append("quarantine")

        mock_logger.info.side_effect = log_info
        runner._generate_dq_reports = generate_reports  # type: ignore[method-assign]
        runner._write_cv_quarantine = write_quarantine  # type: ignore[method-assign]

        await runner._handle_merge_success(merge_result)

        assert call_order == ["log", "dq", "quarantine"]


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
