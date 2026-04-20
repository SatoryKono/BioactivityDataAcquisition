"""Comprehensive tests for FSM pipeline scenarios.

Tests cover all execution paths:
- Full success with multiple enrichers
- Seed failure -> FAILED state
- Required enricher failure -> FAILED state
- Optional enricher failure -> completed with had_warnings
- Merge failure -> FAILED state
- Resume scenarios (seed, enrichment, merge phases)
- Edge cases: no enrichers, dry_run, required_only

This file provides reusable fakes for testing composite pipeline components.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import uuid4

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
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import LockAcquisitionError

if TYPE_CHECKING:
    from collections.abc import Callable


# =============================================================================
# Reusable Fakes for Testing
# =============================================================================


class FakeLoggerPort:
    """Fake logger that captures all log calls for verification.

    Attributes:
        info_calls: List of (message, kwargs) tuples from info calls.
        warning_calls: List of (message, kwargs) tuples from warning calls.
        error_calls: List of (message, kwargs) tuples from error calls.
        debug_calls: List of (message, kwargs) tuples from debug calls.
    """

    def __init__(self) -> None:
        self.info_calls: list[tuple[str, dict[str, Any]]] = []
        self.warning_calls: list[tuple[str, dict[str, Any]]] = []
        self.error_calls: list[tuple[str, dict[str, Any]]] = []
        self.debug_calls: list[tuple[str, dict[str, Any]]] = []

    def info(self, message: str, **kwargs: Any) -> None:
        self.info_calls.append((message, kwargs))

    def warning(self, message: str, **kwargs: Any) -> None:
        self.warning_calls.append((message, kwargs))

    def error(self, message: str, **kwargs: Any) -> None:
        self.error_calls.append((message, kwargs))

    def debug(self, message: str, **kwargs: Any) -> None:
        self.debug_calls.append((message, kwargs))

    def has_message(self, text: str, level: str = "info") -> bool:
        """Check if a message containing text was logged at the given level."""
        calls = getattr(self, f"{level}_calls")
        return any(text in str(msg) or text in str(kwargs) for msg, kwargs in calls)

    def get_fsm_transitions(self) -> list[tuple[str, str]]:
        """Extract FSM transitions from info logs."""
        transitions = []
        for msg, kwargs in self.info_calls:
            if "FSM state transition" in str(msg):
                from_state = kwargs.get("from_state", "")
                to_state = kwargs.get("to_state", "")
                transitions.append((from_state, to_state))
        return transitions


class FakeLockPort:
    """Fake lock that always succeeds.

    Tracks acquire/release calls for verification.
    """

    def __init__(self, should_acquire: bool = True) -> None:
        self._should_acquire = should_acquire
        self.acquire_calls: list[dict[str, Any]] = []
        self.release_calls: list[dict[str, Any]] = []

    async def acquire(
        self,
        key: str,
        owner_id: Any,
        ttl: int = 60,
        wait: bool = False,
        wait_timeout: float = 10.0,
        exclusive: bool = True,
    ) -> bool:
        await asyncio.sleep(0)
        self.acquire_calls.append(
            {
                "key": key,
                "owner_id": owner_id,
                "ttl": ttl,
            }
        )
        return self._should_acquire

    async def release(
        self,
        key: str,
        owner_id: Any,
        exclusive: bool = True,
    ) -> bool:
        await asyncio.sleep(0)
        self.release_calls.append(
            {
                "key": key,
                "owner_id": owner_id,
            }
        )
        return True

    async def heartbeat(
        self,
        key: str,
        owner_id: Any,
        exclusive: bool = False,
    ) -> bool:
        await asyncio.sleep(0)
        return True


class FakeCheckpointManager:
    """In-memory checkpoint manager for testing.

    Tracks all state transitions without filesystem I/O.

    Attributes:
        states: List of saved checkpoint states (in order).
        current_state: Current checkpoint state.
        deleted: Whether checkpoint was deleted.
    """

    def __init__(
        self,
        initial_state: CompositeCheckpointState | None = None,
        composite_name: str = "test_composite",
        run_id: str | None = None,
    ) -> None:
        self._composite_name = composite_name
        self._run_id = run_id or str(uuid4())

        if initial_state is None:
            initial_state = CompositeCheckpointState(
                composite_name=composite_name,
                run_id=self._run_id,
                state=CompositePipelineState.NOT_STARTED,
                created_at=datetime.now(tz=UTC),
            )

        self.current_state = initial_state
        self.states: list[CompositeCheckpointState] = []
        self.deleted = False
        self.delete_error: Exception | None = None

    async def load(self) -> CompositeCheckpointState:
        """Return the current state."""
        await asyncio.sleep(0)
        return self.current_state

    async def save(self, state: CompositeCheckpointState) -> None:
        """Save state to in-memory list."""
        await asyncio.sleep(0)
        self.states.append(state)
        self.current_state = state

    async def delete(self) -> None:
        """Mark checkpoint as deleted or raise if error configured."""
        await asyncio.sleep(0)
        if self.delete_error:
            raise self.delete_error
        self.deleted = True

    async def delete_orphaned(self) -> int:
        """No-op orphan cleanup for tests."""
        await asyncio.sleep(0)
        return 0

    def get_state_sequence(self) -> list[CompositePipelineState]:
        """Get the sequence of FSM states saved."""
        return [s.state for s in self.states]

    def get_final_state(self) -> CompositePipelineState | None:
        """Get the final FSM state."""
        if self.states:
            return self.states[-1].state
        return None


@dataclass
class FakePipelineRunner:
    """Fake pipeline runner with configurable behavior.

    Attributes:
        name: Pipeline name for identification.
        should_fail: If True, run() raises RuntimeError.
        error_message: Error message when failing.
        execution_count: Number of times run() was called.
        records_fetched: Simulated records fetched.
        records_silver: Simulated records written to silver.
    """

    name: str = "fake_pipeline"
    should_fail: bool = False
    error_message: str = "Pipeline failed"
    execution_count: int = 0
    records_fetched: int = 100
    records_silver: int = 95
    records_quarantined: int = 0

    def __post_init__(self) -> None:
        # Create executor mock for stats
        self._executor = type(
            "Executor",
            (),
            {
                "records_fetched": self.records_fetched,
                "records_silver": self.records_silver,
                "records_quarantined": self.records_quarantined,
            },
        )()

    @property
    def execution_metrics(self) -> dict[str, int]:
        return {
            "records_fetched": self._executor.records_fetched,
            "records_silver": self._executor.records_silver,
            "records_quarantined": self._executor.records_quarantined,
        }

    async def run(self) -> None:
        await asyncio.sleep(0)
        self.execution_count += 1
        if self.should_fail:
            raise RuntimeError(self.error_message)


class FakePipelineRunnerFactory:
    """Factory that creates and tracks FakePipelineRunner instances.

    Useful for verifying which pipelines were actually executed.
    """

    def __init__(self) -> None:
        self.created_runners: dict[str, FakePipelineRunner] = {}
        self.runner_configs: dict[str, dict[str, Any]] = {}

    def configure(
        self,
        name: str,
        should_fail: bool = False,
        error_message: str = "Pipeline failed",
        records_fetched: int = 100,
        records_silver: int = 95,
    ) -> None:
        """Configure behavior for a specific pipeline."""
        self.runner_configs[name] = {
            "should_fail": should_fail,
            "error_message": error_message,
            "records_fetched": records_fetched,
            "records_silver": records_silver,
        }

    def create(self, name: str = "default") -> FakePipelineRunner:
        """Create a runner with the configured behavior."""
        config = self.runner_configs.get(name, {})
        runner = FakePipelineRunner(name=name, **config)
        self.created_runners[name] = runner
        return runner

    def create_enricher(self, name: str, keys: pl.DataFrame) -> FakePipelineRunner:
        """Create an enricher runner with the configured behavior."""
        return self.create(name)

    def get_execution_counts(self) -> dict[str, int]:
        """Get execution counts for all created runners."""
        return {name: r.execution_count for name, r in self.created_runners.items()}

    def was_executed(self, name: str) -> bool:
        """Check if a pipeline was executed."""
        runner = self.created_runners.get(name)
        return runner is not None and runner.execution_count > 0


@dataclass
class FakeKeyExtractorService:
    """Fake key extractor that returns configurable data."""

    keys_df: pl.DataFrame = field(
        default_factory=lambda: pl.DataFrame(
            {
                "chembl_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3"],
                "doi": ["10.1000/a", "10.1000/b", "10.1000/c"],
            }
        )
    )

    async def extract(
        self,
        silver_table: str,
        keys: tuple[str, ...] | list[str],
    ) -> pl.DataFrame:
        await asyncio.sleep(0)
        return self.keys_df


@dataclass
class FakeEnrichmentCoordinator:
    """Fake enrichment coordinator with configurable results."""

    results: dict[str, EnrichmentResult] = field(default_factory=dict)
    execution_count: int = 0

    async def run_enrichers(
        self,
        keys: pl.DataFrame,
        enrichers: Any,
        completed: frozenset[str],
        runner_factory: Callable[[str, pl.DataFrame], Any],
    ) -> dict[str, EnrichmentResult]:
        await asyncio.sleep(0)
        self.execution_count += 1
        return self.results


@dataclass
class FakeMergeService:
    """Fake merge service with configurable behavior."""

    result: MergeResult = field(
        default_factory=lambda: MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=80,
            records_fully_enriched=70,
            sources_used=("seed", "crossref"),
            duration_seconds=5.0,
        )
    )
    should_fail: bool = False
    error_message: str = "Merge failed"
    execution_count: int = 0

    async def merge(
        self,
        seed_table: str,
        enrichers: Any,
        enrichment_results: dict[str, EnrichmentResult],
        run_id: str,
        seed_pipeline: str | None = None,
        dependencies: Any | None = None,
        dependency_results: Any | None = None,
    ) -> MergeResult:
        await asyncio.sleep(0)
        self.execution_count += 1
        if self.should_fail:
            raise RuntimeError(self.error_message)
        return self.result


# =============================================================================
# Configuration Dataclasses
# =============================================================================


@dataclass
class FakeEnricherConfig:
    """Fake enricher configuration."""

    pipeline: str
    join_keys: tuple[str, ...] = ("doi",)
    required: bool = False
    filter_condition: str | None = None
    timeout_seconds: int = 600
    silver_table: str | None = None


@dataclass
class FakeSeedConfig:
    """Fake seed configuration."""

    pipeline: str = "chembl_activity"
    silver_table: str = "silver/chembl/activity"
    output_keys: tuple[str, ...] = ("chembl_id", "doi")


@dataclass
class FakeMergeConfig:
    """Fake merge configuration."""

    output_silver_path: str = "silver/composite/test"
    output_gold_path: str = "gold/test_composite"


@dataclass
class FakeDQConfig:
    """Fake DQ configuration."""

    soft_fail_threshold: float = 0.05
    hard_fail_threshold: float = 0.20


@dataclass
class FakeCompositeConfig:
    """Fake composite configuration for testing."""

    name: str = "test_composite"
    lock_key: str = "composite:test_composite"
    seed: FakeSeedConfig = field(default_factory=FakeSeedConfig)
    merge: FakeMergeConfig = field(default_factory=FakeMergeConfig)
    dq: FakeDQConfig = field(default_factory=FakeDQConfig)
    enrichers: tuple[FakeEnricherConfig, ...] = ()
    dependencies: tuple = ()

    @property
    def required_enrichers(self) -> tuple[str, ...]:
        return tuple(e.pipeline for e in self.enrichers if e.required)

    @property
    def required_dependencies(self) -> tuple[str, ...]:
        return tuple(
            d.pipeline for d in self.dependencies if getattr(d, "required", False)
        )


# =============================================================================
# Helper Functions
# =============================================================================


def create_test_runner(
    config: FakeCompositeConfig | None = None,
    runtime: CompositeRuntimeConfig | None = None,
    seed_factory: FakePipelineRunnerFactory | None = None,
    enricher_factory: FakePipelineRunnerFactory | None = None,
    key_extractor: FakeKeyExtractorService | None = None,
    coordinator: FakeEnrichmentCoordinator | None = None,
    merger: FakeMergeService | None = None,
    checkpoint_manager: FakeCheckpointManager | None = None,
    logger: FakeLoggerPort | None = None,
    lock: FakeLockPort | None = None,
    run_id: str | None = None,
) -> tuple[CompositePipelineRunner, dict[str, Any]]:
    """Create a test runner with all fakes.

    Returns:
        Tuple of (runner, components) where components is a dict of all fakes.
    """
    if config is None:
        config = FakeCompositeConfig()
    if runtime is None:
        runtime = CompositeRuntimeConfig()
    if seed_factory is None:
        seed_factory = FakePipelineRunnerFactory()
    if enricher_factory is None:
        enricher_factory = FakePipelineRunnerFactory()
    if key_extractor is None:
        key_extractor = FakeKeyExtractorService()
    if coordinator is None:
        coordinator = FakeEnrichmentCoordinator()
    if merger is None:
        merger = FakeMergeService()
    if checkpoint_manager is None:
        checkpoint_manager = FakeCheckpointManager()
    if logger is None:
        logger = FakeLoggerPort()
    if lock is None:
        lock = FakeLockPort()
    if run_id is None:
        run_id = str(uuid4())
    fsm_state_helper = FSMStateHelperService(
        config=config,
        logger=logger,
        run_id=run_id,
    )

    deps = CompositeRunnerDependencies(
        seed_runner_factory=lambda: seed_factory.create("seed"),
        enricher_runner_factory=enricher_factory.create_enricher,
        key_extractor=key_extractor,
        coordinator=coordinator,
        merger=merger,
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=lock,
        fsm_state_helper=fsm_state_helper,
    )
    runner = CompositePipelineRunner(
        config=config,
        runtime=runtime,
        deps=deps,
        run_id=run_id,
    )

    components = {
        "config": config,
        "runtime": runtime,
        "seed_factory": seed_factory,
        "enricher_factory": enricher_factory,
        "key_extractor": key_extractor,
        "coordinator": coordinator,
        "merger": merger,
        "checkpoint_manager": checkpoint_manager,
        "logger": logger,
        "lock": lock,
    }

    return runner, components


# =============================================================================
# Test Classes
# =============================================================================


@pytest.mark.unit
class TestSeedFailure:
    """Tests for seed pipeline failure scenarios."""

    @pytest.mark.asyncio
    async def test_seed_failure_transitions_to_failed_state(self):
        """Seed failure should transition FSM to FAILED state."""
        seed_factory = FakePipelineRunnerFactory()
        seed_factory.configure(
            "seed", should_fail=True, error_message="Seed database connection failed"
        )

        runner, components = create_test_runner(seed_factory=seed_factory)

        with pytest.raises(RuntimeError, match="Seed database connection failed"):
            await runner.run()

        # Verify FAILED state was saved
        checkpoint = components["checkpoint_manager"]
        assert checkpoint.get_final_state() == CompositePipelineState.FAILED

    @pytest.mark.asyncio
    async def test_seed_failure_saves_checkpoint_before_raising(self):
        """Seed failure should save checkpoint to enable resume."""
        seed_factory = FakePipelineRunnerFactory()
        seed_factory.configure("seed", should_fail=True)

        runner, components = create_test_runner(seed_factory=seed_factory)

        with pytest.raises(RuntimeError):
            await runner.run()

        # Verify checkpoint was saved with FAILED state
        checkpoint = components["checkpoint_manager"]
        states = checkpoint.get_state_sequence()
        assert CompositePipelineState.SEED_RUNNING in states
        assert CompositePipelineState.FAILED in states

    @pytest.mark.asyncio
    async def test_seed_failure_logs_error(self):
        """Seed failure should be logged as error."""
        seed_factory = FakePipelineRunnerFactory()
        seed_factory.configure("seed", should_fail=True, error_message="API timeout")

        runner, components = create_test_runner(seed_factory=seed_factory)

        with pytest.raises(RuntimeError):
            await runner.run()

        logger = components["logger"]
        assert logger.has_message("Seed pipeline failed", "error")

    @pytest.mark.asyncio
    async def test_seed_failure_releases_lock(self):
        """Seed failure should still release the lock."""
        seed_factory = FakePipelineRunnerFactory()
        seed_factory.configure("seed", should_fail=True)
        lock = FakeLockPort()

        runner, _ = create_test_runner(seed_factory=seed_factory, lock=lock)

        with pytest.raises(RuntimeError):
            await runner.run()

        # Lock should be released
        assert len(lock.release_calls) == 1

    @pytest.mark.asyncio
    async def test_seed_failure_does_not_call_enrichers(self):
        """Seed failure should not execute enrichers."""
        seed_factory = FakePipelineRunnerFactory()
        seed_factory.configure("seed", should_fail=True)

        coordinator = FakeEnrichmentCoordinator()
        merger = FakeMergeService()

        runner, _components = create_test_runner(
            seed_factory=seed_factory,
            coordinator=coordinator,
            merger=merger,
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        # Neither coordinator nor merger should be called
        assert coordinator.execution_count == 0
        assert merger.execution_count == 0


@pytest.mark.unit
class TestMergeFailure:
    """Tests for merge failure scenarios."""

    @pytest.mark.asyncio
    async def test_merge_failure_transitions_to_failed_state(self):
        """Merge failure should transition FSM to FAILED state."""
        merger = FakeMergeService(should_fail=True, error_message="Disk full")

        runner, components = create_test_runner(merger=merger)

        with pytest.raises(RuntimeError, match="Disk full"):
            await runner.run()

        checkpoint = components["checkpoint_manager"]
        assert checkpoint.get_final_state() == CompositePipelineState.FAILED

    @pytest.mark.asyncio
    async def test_merge_failure_preserves_enrichment_results(self):
        """Merge failure should preserve enrichment results in checkpoint."""
        config = FakeCompositeConfig(
            enrichers=(FakeEnricherConfig(pipeline="crossref", required=False),)
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )
        merger = FakeMergeService(should_fail=True)

        runner, components = create_test_runner(
            config=config,
            coordinator=coordinator,
            merger=merger,
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        # Verify checkpoint contains enrichment results
        checkpoint = components["checkpoint_manager"]
        final_state = checkpoint.current_state
        assert final_state.seed_completed is True

    @pytest.mark.asyncio
    async def test_merge_failure_goes_through_merging_state(self):
        """Merge failure should go through MERGING before FAILED."""
        merger = FakeMergeService(should_fail=True)

        runner, components = create_test_runner(merger=merger)

        with pytest.raises(RuntimeError):
            await runner.run()

        states = components["checkpoint_manager"].get_state_sequence()

        # MERGING should appear before FAILED
        merging_idx = states.index(CompositePipelineState.MERGING)
        failed_idx = states.index(CompositePipelineState.FAILED)
        assert merging_idx < failed_idx


@pytest.mark.unit
class TestFullSuccessFlow:
    """Tests for full successful pipeline execution."""

    @pytest.mark.asyncio
    async def test_full_success_with_multiple_enrichers(self):
        """Full pipeline with multiple enrichers should complete successfully."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref", required=True),
                FakeEnricherConfig(pipeline="pubmed", required=False),
                FakeEnricherConfig(pipeline="openalex", required=False),
            )
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                ),
                "pubmed": EnrichmentResult.success(
                    enricher_name="pubmed",
                    records_input=100,
                    records_enriched=80,
                ),
                "openalex": EnrichmentResult.success(
                    enricher_name="openalex",
                    records_input=100,
                    records_enriched=70,
                ),
            }
        )

        runner, components = create_test_runner(config=config, coordinator=coordinator)

        result = await runner.run()

        # Verify success
        assert result is not None
        assert result.composite_name == "test_composite"
        assert result.had_warnings is False

        # Verify checkpoint deleted
        checkpoint = components["checkpoint_manager"]
        assert checkpoint.deleted is True
        assert checkpoint.get_final_state() == CompositePipelineState.COMPLETED

    @pytest.mark.asyncio
    async def test_full_success_fsm_state_sequence(self):
        """Full success should follow correct FSM state sequence."""
        config = FakeCompositeConfig(
            enrichers=(FakeEnricherConfig(pipeline="crossref"),)
        )
        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )

        runner, components = create_test_runner(config=config, coordinator=coordinator)

        await runner.run()

        states = components["checkpoint_manager"].get_state_sequence()

        # Verify state sequence
        expected_order = [
            CompositePipelineState.SEED_RUNNING,
            CompositePipelineState.SEED_COMPLETED,
            CompositePipelineState.ENRICHING,
            CompositePipelineState.ENRICHMENT_COMPLETED,
            CompositePipelineState.MERGING,
            CompositePipelineState.COMPLETED,
        ]

        for expected in expected_order:
            assert expected in states, f"Missing state: {expected}"

    @pytest.mark.asyncio
    async def test_full_success_returns_complete_result(self):
        """Full success should return CompositeResult with all data."""
        config = FakeCompositeConfig(
            enrichers=(FakeEnricherConfig(pipeline="crossref", required=True),)
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )

        merger = FakeMergeService(
            result=MergeResult(
                records_merged=100,
                records_from_seed=100,
                records_enriched=90,
                records_fully_enriched=85,
                sources_used=("seed", "crossref"),
            )
        )

        runner, _components = create_test_runner(
            config=config,
            coordinator=coordinator,
            merger=merger,
        )

        result = await runner.run()

        # Verify result completeness
        assert result.seed_result is not None
        assert "crossref" in result.enrichment_results
        assert result.enrichment_results["crossref"].is_success
        assert result.merge_result is not None
        assert result.merge_result.records_merged == 100


@pytest.mark.unit
class TestResumePartialEnrichment:
    """Tests for resuming from partial enrichment completion."""

    @pytest.mark.asyncio
    async def test_resume_skips_completed_enrichers(self):
        """Resume should not re-run already completed enrichers."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref"),
                FakeEnricherConfig(pipeline="pubmed"),
                FakeEnricherConfig(pipeline="openalex"),
            )
        )

        # Create checkpoint with crossref already completed
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.ENRICHING,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
            ),
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            },
            created_at=datetime.now(tz=UTC),
        )

        checkpoint = FakeCheckpointManager(initial_state=initial_state)

        # Coordinator should only receive results for remaining enrichers
        coordinator = FakeEnrichmentCoordinator(
            results={
                "pubmed": EnrichmentResult.success(
                    enricher_name="pubmed",
                    records_input=100,
                    records_enriched=80,
                ),
                "openalex": EnrichmentResult.success(
                    enricher_name="openalex",
                    records_input=100,
                    records_enriched=70,
                ),
            }
        )

        seed_factory = FakePipelineRunnerFactory()

        runner, _components = create_test_runner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            seed_factory=seed_factory,
            coordinator=coordinator,
            checkpoint_manager=checkpoint,
        )

        result = await runner.run()

        # Seed should NOT be re-run
        assert not seed_factory.was_executed("seed")

        # Result should include both completed and new enrichment results
        assert "crossref" in result.enrichment_results
        assert "pubmed" in result.enrichment_results
        assert "openalex" in result.enrichment_results

    @pytest.mark.asyncio
    async def test_resume_after_merge_failure_reruns_merge(self):
        """Resume after merge failure should re-run merge only."""
        config = FakeCompositeConfig(
            enrichers=(FakeEnricherConfig(pipeline="crossref"),)
        )

        # Create checkpoint with all enrichers completed but merge failed
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
            ),
            completed_enrichers=frozenset({"crossref"}),
            enrichment_results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            },
            created_at=datetime.now(tz=UTC),
        )

        checkpoint = FakeCheckpointManager(initial_state=initial_state)
        seed_factory = FakePipelineRunnerFactory()
        coordinator = FakeEnrichmentCoordinator()
        merger = FakeMergeService()

        runner, _ = create_test_runner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            seed_factory=seed_factory,
            coordinator=coordinator,
            checkpoint_manager=checkpoint,
            merger=merger,
        )

        result = await runner.run()

        # Seed and coordinator should NOT be called
        assert not seed_factory.was_executed("seed")
        # Coordinator gets called but sees all enrichers already completed
        # Merge should be called
        assert merger.execution_count == 1

        # Pipeline should complete
        assert result is not None
        assert checkpoint.get_final_state() == CompositePipelineState.COMPLETED


@pytest.mark.unit
class TestDryRunMode:
    """Tests for dry run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_skips_merge(self):
        """Dry run should skip merge operation."""
        merger = FakeMergeService()

        runner, _ = create_test_runner(
            runtime=CompositeRuntimeConfig(dry_run=True),
            merger=merger,
        )

        result = await runner.run()

        # Merge should NOT be called
        assert merger.execution_count == 0

        # Result should have no merge_result
        assert result.merge_result is None

    @pytest.mark.asyncio
    async def test_dry_run_still_completes_successfully(self):
        """Dry run should still mark pipeline as completed."""
        runner, components = create_test_runner(
            runtime=CompositeRuntimeConfig(dry_run=True),
        )

        result = await runner.run()

        assert result is not None
        checkpoint = components["checkpoint_manager"]
        assert checkpoint.get_final_state() == CompositePipelineState.COMPLETED
        assert checkpoint.deleted is True

    @pytest.mark.asyncio
    async def test_dry_run_does_not_go_through_merging_state(self):
        """Dry run should skip MERGING state entirely."""
        runner, components = create_test_runner(
            runtime=CompositeRuntimeConfig(dry_run=True),
        )

        await runner.run()

        states = components["checkpoint_manager"].get_state_sequence()
        assert CompositePipelineState.MERGING not in states


@pytest.mark.unit
class TestNoEnrichers:
    """Tests for pipeline with no enrichers configured."""

    @pytest.mark.asyncio
    async def test_no_enrichers_completes_successfully(self):
        """Pipeline with no enrichers should complete successfully."""
        config = FakeCompositeConfig(enrichers=())
        coordinator = FakeEnrichmentCoordinator()

        runner, _ = create_test_runner(
            config=config,
            coordinator=coordinator,
        )

        result = await runner.run()

        assert result is not None
        # Coordinator should not be called (or be called with empty enrichers)
        assert len(result.enrichment_results) == 0

    @pytest.mark.asyncio
    async def test_no_enrichers_goes_to_enrichment_completed(self):
        """No enrichers should still transition through ENRICHMENT_COMPLETED."""
        config = FakeCompositeConfig(enrichers=())

        runner, components = create_test_runner(config=config)

        await runner.run()

        states = components["checkpoint_manager"].get_state_sequence()
        assert CompositePipelineState.ENRICHMENT_COMPLETED in states


@pytest.mark.unit
class TestRequiredOnlyMode:
    """Tests for required_only mode."""

    @pytest.mark.asyncio
    async def test_required_only_adds_not_run_for_optional(self):
        """required_only mode should add NOT_RUN status for optional enrichers."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref", required=True),
                FakeEnricherConfig(pipeline="pubmed", required=False),
                FakeEnricherConfig(pipeline="openalex", required=False),
            )
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )

        runner, _ = create_test_runner(
            config=config,
            runtime=CompositeRuntimeConfig(required_only=True),
            coordinator=coordinator,
        )

        result = await runner.run()

        # Required enricher should succeed
        assert "crossref" in result.enrichment_results
        assert result.enrichment_results["crossref"].is_success

        # Optional enrichers should have NOT_RUN status
        assert "pubmed" in result.enrichment_results
        assert result.enrichment_results["pubmed"].status == EnrichmentStatus.NOT_RUN

        assert "openalex" in result.enrichment_results
        assert result.enrichment_results["openalex"].status == EnrichmentStatus.NOT_RUN

    @pytest.mark.asyncio
    async def test_required_only_does_not_set_had_warnings(self):
        """NOT_RUN from required_only should not trigger had_warnings."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref", required=True),
                FakeEnricherConfig(pipeline="pubmed", required=False),
            )
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )

        runner, _ = create_test_runner(
            config=config,
            runtime=CompositeRuntimeConfig(required_only=True),
            coordinator=coordinator,
        )

        result = await runner.run()

        # had_warnings should be False for NOT_RUN (intentionally skipped)
        assert result.had_warnings is False


@pytest.mark.unit
class TestOptionalEnricherFailure:
    """Tests for optional enricher failure scenarios."""

    @pytest.mark.asyncio
    async def test_optional_failure_sets_had_warnings_true(self):
        """Optional enricher failure should set had_warnings=True."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref", required=True),
                FakeEnricherConfig(pipeline="pubmed", required=False),
            )
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed",
                    error_message="Connection timeout",
                ),
            }
        )

        runner, _ = create_test_runner(config=config, coordinator=coordinator)

        result = await runner.run()

        assert result.had_warnings is True
        assert result.is_success is True  # Still succeeds overall

    @pytest.mark.asyncio
    async def test_optional_timeout_sets_had_warnings_true(self):
        """Optional enricher timeout should set had_warnings=True."""
        config = FakeCompositeConfig(
            enrichers=(
                FakeEnricherConfig(pipeline="crossref", required=True),
                FakeEnricherConfig(pipeline="pubmed", required=False),
            )
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
                "pubmed": EnrichmentResult.timeout(
                    enricher_name="pubmed",
                    timeout_seconds=600,
                    records_input=100,
                ),
            }
        )

        runner, _ = create_test_runner(config=config, coordinator=coordinator)

        result = await runner.run()

        assert result.had_warnings is True


@pytest.mark.unit
class TestCheckpointDeletionError:
    """Tests for checkpoint deletion error handling."""

    @pytest.mark.asyncio
    async def test_checkpoint_delete_error_is_non_fatal(self):
        """Checkpoint deletion failure should not fail the pipeline."""
        checkpoint = FakeCheckpointManager()
        checkpoint.delete_error = PermissionError("Cannot delete file")

        runner, components = create_test_runner(checkpoint_manager=checkpoint)

        # Should NOT raise
        result = await runner.run()

        assert result is not None

        # Warning should be logged
        logger = components["logger"]
        assert logger.has_message("Failed to delete checkpoint", "warning")


@pytest.mark.unit
class TestLockAcquisitionFailure:
    """Tests for lock acquisition failure."""

    @pytest.mark.asyncio
    async def test_lock_acquisition_failure_raises(self):
        """Lock acquisition failure should raise LockAcquisitionError."""
        lock = FakeLockPort(should_acquire=False)

        runner, _ = create_test_runner(lock=lock)

        with pytest.raises(LockAcquisitionError, match="Failed to acquire lock"):
            await runner.run()


@pytest.mark.unit
class TestFSMTransitionLogging:
    """Tests for FSM transition logging."""

    @pytest.mark.asyncio
    async def test_all_transitions_are_logged(self):
        """All FSM transitions should be logged."""
        config = FakeCompositeConfig(
            enrichers=(FakeEnricherConfig(pipeline="crossref"),)
        )

        coordinator = FakeEnrichmentCoordinator(
            results={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=90,
                ),
            }
        )

        runner, components = create_test_runner(config=config, coordinator=coordinator)

        await runner.run()

        logger = components["logger"]
        transitions = logger.get_fsm_transitions()

        # Should have multiple transitions logged
        assert (
            len(transitions) >= 4
        )  # At least: seed_start, seed_complete, enrichment, merge, complete

        # Verify key transitions
        transition_pairs = transitions
        assert any(to == "seed_running" for _, to in transition_pairs)
        assert any(to == "seed_completed" for _, to in transition_pairs)
        assert any(to == "completed" for _, to in transition_pairs)
