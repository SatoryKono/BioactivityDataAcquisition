"""Unit tests for CompositePipelineRunner FSM checkpoint resume integration.

Tests for resuming from FAILED state and checkpoint resume context logging.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)
from bioetl.application.composite.fsm_helper import FSMStateHelperService
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.locking import FencingToken

_MOCK_TOKEN = FencingToken(
    sequence=1,
    key="lock:mock",
    owner_id=UUID("00000000-0000-0000-0000-000000000000"),
    issued_at=0.0,
)


@dataclass
class MockEnricherConfig:
    """Mock enricher configuration."""

    pipeline: str
    required: bool = False


@dataclass
class MockCompositeConfig:
    """Mock composite configuration for testing."""

    name: str = "test_composite"
    lock_key: str = "lock:test_composite"

    @dataclass
    class SeedConfig:
        pipeline: str = "chembl_activity"
        silver_table: str = "chembl_activity"
        output_keys: tuple[str, ...] = ("chembl_id",)

    @dataclass
    class MergeConfig:
        output_silver_path: str = "silver/composite"
        output_gold_path: str = "gold/composite"

    @dataclass
    class DQConfig:
        soft_fail_threshold: float = 0.05
        hard_fail_threshold: float = 0.20

    seed: SeedConfig = None  # type: ignore[assignment]
    merge: MergeConfig = None  # type: ignore[assignment]
    dq: DQConfig = None  # type: ignore[assignment]
    enrichers: tuple = ()
    required_enrichers: frozenset = frozenset()
    dependencies: tuple = ()

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        return tuple(
            d.pipeline for d in self.dependencies if getattr(d, "required", False)
        )

    def __post_init__(self):
        if self.seed is None:
            self.seed = self.SeedConfig()
        if self.merge is None:
            self.merge = self.MergeConfig()
        if self.dq is None:
            self.dq = self.DQConfig()


class MockPipelineRunner:
    """Mock PipelineRunner for testing."""

    def __init__(
        self, should_fail: bool = False, error_message: str = "Pipeline failed"
    ):
        self._should_fail = should_fail
        self._error_message = error_message
        self.run_called = False
        self._executor = MagicMock()
        self._executor.records_fetched = 100
        self._executor.records_silver = 95

    @property
    def execution_metrics(self) -> dict[str, int]:
        return {
            "records_fetched": self._executor.records_fetched,
            "records_silver": self._executor.records_silver,
        }

    async def run(self):
        await asyncio.sleep(0)
        self.run_called = True
        if self._should_fail:
            raise RuntimeError(self._error_message)


def create_mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


def create_mock_lock() -> AsyncMock:
    """Create a mock lock."""
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=_MOCK_TOKEN)
    lock.release = AsyncMock(return_value=True)
    return lock


def create_mock_checkpoint_manager(
    initial_state: CompositeCheckpointState | None = None,
) -> AsyncMock:
    """Create a mock checkpoint manager."""
    manager = AsyncMock()
    if initial_state is None:
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )
    manager.load = AsyncMock(return_value=initial_state)
    manager.save = AsyncMock()
    manager.delete = AsyncMock()
    return manager


def create_mock_key_extractor() -> AsyncMock:
    """Create a mock key extractor."""
    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=pl.DataFrame({"chembl_id": ["CHEMBL123"]})
    )
    return extractor


def create_mock_coordinator() -> AsyncMock:
    """Create a mock enrichment coordinator."""
    coordinator = AsyncMock()
    coordinator.run_enrichers = AsyncMock(return_value={})
    return coordinator


def create_mock_merger() -> AsyncMock:
    """Create a mock merger."""
    merger = AsyncMock()
    merger.merge = AsyncMock(
        return_value=MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=0,
            records_fully_enriched=0,
            duration_seconds=1.0,
        )
    )
    return merger


def _seed_runner_factory(seed_runner: MockPipelineRunner):
    def _factory() -> MockPipelineRunner:
        return seed_runner

    return _factory


def _new_seed_runner_factory():
    def _factory() -> MockPipelineRunner:
        return MockPipelineRunner()

    return _factory


def _new_enricher_runner_factory():
    def _factory(name: str, df: object) -> MockPipelineRunner:
        return MockPipelineRunner()

    return _factory


def create_mock_fsm_state_helper(
    *,
    config: MockCompositeConfig | None = None,
    logger: MagicMock | None = None,
    run_id: str | None = None,
) -> FSMStateHelperService:
    """Create a real FSM helper service for checkpoint resume tests."""
    return FSMStateHelperService(
        config=config or MockCompositeConfig(),
        logger=logger or create_mock_logger(),
        run_id=run_id or str(uuid4()),
    )


class TestResumeFromFailedState:
    """Tests for resuming from FAILED state."""

    @pytest.mark.asyncio
    async def test_resume_from_failed_seed_phase(self):
        """Resume from FAILED state when seed failed should re-run seed."""
        # Create checkpoint in FAILED state with seed not completed
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=False,  # Seed failed
            created_at=datetime.now(tz=UTC),
        )

        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        seed_runner = MockPipelineRunner()
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(seed_runner),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Seed should be run since it wasn't completed
        assert seed_runner.run_called is True

        # Should log the resume from failed
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("resume_from_failed" in c for c in info_calls)
        assert any("seed (seed not completed)" in c for c in info_calls)

    @pytest.mark.asyncio
    async def test_resume_from_failed_enrichment_phase(self):
        """Resume from FAILED state when enrichment failed should run remaining enrichers."""
        config = MockCompositeConfig()
        config.enrichers = (
            MockEnricherConfig(pipeline="crossref"),
            MockEnricherConfig(pipeline="pubmed"),
            MockEnricherConfig(pipeline="openalex"),
        )

        # Create checkpoint in FAILED state with seed completed and 1 of 3 enrichers done
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
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

        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        seed_runner = MockPipelineRunner()
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(seed_runner),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(config=config, logger=logger),
        )
        runner = CompositePipelineRunner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Seed should NOT be run since it was completed
        assert seed_runner.run_called is False

        # Should log the resume from failed with enrichment phase
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("resume_from_failed" in c for c in info_calls)
        assert any("enrichment" in c for c in info_calls)
        assert any("1/3 enrichers completed" in c for c in info_calls)

    @pytest.mark.asyncio
    async def test_resume_from_failed_merge_phase(self):
        """Resume from FAILED state when merge failed should skip to merge."""
        config = MockCompositeConfig()
        config.enrichers = (
            MockEnricherConfig(pipeline="crossref"),
            MockEnricherConfig(pipeline="pubmed"),
        )

        # Create checkpoint in FAILED state with all enrichers completed
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset({"crossref", "pubmed"}),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
                "pubmed": EnrichmentResult.success(
                    enricher_name="pubmed",
                    records_input=100,
                    records_enriched=80,
                    records_not_found=20,
                    duration_seconds=15.0,
                ),
            },
            created_at=datetime.now(tz=UTC),
        )

        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        seed_runner = MockPipelineRunner()
        merger = create_mock_merger()
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_seed_runner_factory(seed_runner),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=merger,
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(config=config, logger=logger),
        )
        runner = CompositePipelineRunner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Seed should NOT be run
        assert seed_runner.run_called is False

        # Merge should be called
        merger.merge.assert_called_once()

        # Should log the resume from failed with merge phase
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("resume_from_failed" in c for c in info_calls)
        assert any("merge (all enrichers completed)" in c for c in info_calls)


class TestResumeContextLogging:
    """Tests for resume context logging."""

    @pytest.mark.asyncio
    async def test_logs_resume_context_with_completed_enrichers(self):
        """Should log detailed resume context when resuming."""
        config = MockCompositeConfig()
        config.enrichers = (
            MockEnricherConfig(pipeline="crossref"),
            MockEnricherConfig(pipeline="pubmed"),
            MockEnricherConfig(pipeline="openalex"),
        )

        # Create checkpoint with partial progress
        partial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset({"crossref", "pubmed"}),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
                "pubmed": EnrichmentResult.success(
                    enricher_name="pubmed",
                    records_input=100,
                    records_enriched=80,
                    records_not_found=20,
                    duration_seconds=15.0,
                ),
            },
            created_at=datetime.now(tz=UTC),
        )

        checkpoint_manager = create_mock_checkpoint_manager(partial_state)
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_new_seed_runner_factory(),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(config=config, logger=logger),
        )
        runner = CompositePipelineRunner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Should log resume context
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("Resuming from checkpoint" in c for c in info_calls)
        assert any("completed_enrichers_count" in c and "2" in c for c in info_calls)
        assert any("remaining_enrichers_count" in c and "1" in c for c in info_calls)

    @pytest.mark.asyncio
    async def test_no_resume_logging_without_resume_flag(self):
        """Should not log resume context when resume=False."""
        checkpoint_manager = create_mock_checkpoint_manager()
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_new_seed_runner_factory(),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=False),
            deps=deps,
        )

        await runner.run()

        # Should NOT log resume context
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert not any("Resuming from checkpoint" in c for c in info_calls)


class TestCheckpointExistsWarning:
    """Tests for warning when checkpoint exists but resume=False."""

    @pytest.mark.asyncio
    async def test_warns_when_checkpoint_exists_without_resume(self, tmp_path):
        """Should warn when checkpoint with progress exists but resume=False."""
        logger = create_mock_logger()
        run_id = str(uuid4())

        # Create a real checkpoint manager and save a state with progress
        manager = CompositeCheckpointService(
            composite_name="test_composite",
            run_id=run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=logger,
            resume=False,  # No resume
        )

        # Create and save a checkpoint with progress
        existing_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=run_id,
            state=CompositePipelineState.ENRICHING,
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

        # Save checkpoint directly to file
        await manager.save(existing_state)

        # Create new manager without resume flag (should warn)
        manager_no_resume = CompositeCheckpointService(
            composite_name="test_composite",
            run_id=str(uuid4()),  # New run
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=logger,
            resume=False,
        )

        # Load should warn about existing checkpoint
        await manager_no_resume.load()

        # Verify warning was logged
        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )
        assert any("--resume flag" in c for c in warning_calls)

    @pytest.mark.asyncio
    async def test_no_warning_when_no_checkpoint_exists(self, tmp_path):
        """Should not warn when no checkpoint exists."""
        logger = create_mock_logger()

        manager = CompositeCheckpointService(
            composite_name="test_composite",
            run_id=str(uuid4()),
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=logger,
            resume=False,
        )

        await manager.load()

        # No warning should be logged
        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )

    @pytest.mark.asyncio
    async def test_no_warning_when_checkpoint_has_no_progress(self, tmp_path):
        """Should not warn when checkpoint exists but has no progress."""
        logger = create_mock_logger()
        run_id = str(uuid4())

        # Save a fresh checkpoint with no progress
        manager_setup = CompositeCheckpointService(
            composite_name="test_composite",
            run_id=run_id,
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=MagicMock(),
            resume=False,
        )

        fresh_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=run_id,
            state=CompositePipelineState.NOT_STARTED,
            seed_completed=False,
            created_at=datetime.now(tz=UTC),
        )
        await manager_setup.save(fresh_state)

        # Create new manager without resume flag
        manager_no_resume = CompositeCheckpointService(
            composite_name="test_composite",
            run_id=str(uuid4()),
            storage=FileCompositeCheckpointWriter(tmp_path),
            logger=logger,
            resume=False,
        )

        await manager_no_resume.load()

        # No warning should be logged (checkpoint has no progress)
        warning_calls = [str(c) for c in logger.warning.call_args_list]
        assert not any(
            "Existing checkpoint with progress will be overwritten" in c
            for c in warning_calls
        )


class TestFSMStateTransitionOnResume:
    """Tests for FSM state transitions when resuming from FAILED."""

    @pytest.mark.asyncio
    async def test_fsm_transition_logged_on_resume_from_failed(self):
        """FSM transition from FAILED should be logged."""
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset(),
            created_at=datetime.now(tz=UTC),
        )

        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_new_seed_runner_factory(),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Should log FSM transition
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any(
            "FSM state transition" in c and "from_state" in c and "failed" in c
            for c in info_calls
        )

    @pytest.mark.asyncio
    async def test_checkpoint_state_updated_on_resume_from_failed(self):
        """Checkpoint state should be updated when resuming from FAILED."""
        config = MockCompositeConfig()
        config.enrichers = (MockEnricherConfig(pipeline="crossref"),)

        # All enrichers completed, merge failed
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
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

        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        saved_states: list[CompositePipelineState] = []
        original_save = checkpoint_manager.save
        logger = create_mock_logger()

        async def tracking_save(state: CompositeCheckpointState) -> None:
            saved_states.append(state.state)
            await original_save(state)

        checkpoint_manager.save = tracking_save  # type: ignore[method-assign]

        deps = CompositeRunnerDependencies(
            seed_runner_factory=_new_seed_runner_factory(),
            enricher_runner_factory=_new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(config=config, logger=logger),
        )
        runner = CompositePipelineRunner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )

        await runner.run()

        # Should transition through states after FAILED
        # ENRICHMENT_COMPLETED -> MERGING -> COMPLETED
        assert CompositePipelineState.ENRICHMENT_COMPLETED in saved_states
        assert CompositePipelineState.MERGING in saved_states
        assert CompositePipelineState.COMPLETED in saved_states
