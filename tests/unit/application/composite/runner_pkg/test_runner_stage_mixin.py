"""Unit tests for CompositeRunnerStageMixin."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg.runner_stage_mixin import (
    CompositeRunnerStageMixin,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState
from bioetl.domain.composite.result import (
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError
from tests.unit.application.composite.runner_pkg.runner_pkg_test_support import (
    failed_dep,
    initialize_runner_pkg_harness,
    make_dependency_cfg,
    make_runner_state,
    success_dep,
)


# ---------------------------------------------------------------------------
# Fakes / factories
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _StageMixinHarness(CompositeRunnerStageMixin):
    """Concrete harness providing all required collaborators."""

    def __init__(
        self,
        config: Any | None = None,
        seed_result: SeedResult | None = None,
        seed_raises: Exception | None = None,
    ) -> None:
        initialize_runner_pkg_harness(
            self,
            config=config
            or SimpleNamespace(
                name="test_composite",
                seed=SimpleNamespace(
                    pipeline="seed_pipeline",
                    silver_table="silver/seed",
                ),
                enrichers=[],
                required_enrichers=[],
                dependencies=[],
            ),
            runtime=SimpleNamespace(
                required_only=False,
                enrich_only=None,
                force_enricher=None,
                dry_run=False,
            ),
            run_id_str="run-stage-test",
        )

        # Seed seam
        self._seed_result = seed_result or SeedResult(
            pipeline_name="seed_pipeline",
            records_extracted=100,
            records_silver=90,
        )
        self._seed_raises = seed_raises

        # Dependencies seam
        self._dependency_coordinator = None
        self._dependencies_runner_factory = None

        # Enrichment seam
        self._coordinator = MagicMock()
        self._coordinator.run_enrichers = AsyncMock(return_value={})
        self._enricher_runner_factory = MagicMock()

    # --- seam implementations ---

    async def _save_checkpoint_safe(self, state: Any, operation: str) -> bool:
        await asyncio.sleep(0)
        return True

    async def _run_seed(self) -> SeedResult:
        await asyncio.sleep(0)
        if self._seed_raises is not None:
            raise self._seed_raises
        return self._seed_result

    def _get_enrichers_to_run(self, state: Any) -> list[Any]:
        return []

    def _check_required_enrichers(self, results: Any) -> None:
        # Test double intentionally disables required-enricher validation.
        return None

    def _call_check_required_enrichers(self, results: Any) -> None:
        # Test double intentionally bypasses the wrapper hook.
        return None

    def _call_get_enrichers_to_run(self, state: Any) -> list[Any]:
        return []


# ---------------------------------------------------------------------------
# _execute_seed_phase — resume path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_seed_phase_when_already_completed_then_resumes_without_running() -> (
    None
):
    harness = _StageMixinHarness()
    state = make_runner_state(
        state=CompositePipelineState.SEED_COMPLETED,
        seed_completed=True,
    )

    _, seed_result = await harness._execute_seed_phase(state)

    assert seed_result.resumed is True
    harness._logger.info.assert_called()


# ---------------------------------------------------------------------------
# _execute_seed_phase — run path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_seed_phase_when_not_completed_then_runs_seed() -> None:
    harness = _StageMixinHarness()
    state = make_runner_state(
        state=CompositePipelineState.NOT_STARTED,
        seed_completed=False,
    )

    _, seed_result = await harness._execute_seed_phase(state)

    assert seed_result.resumed is False
    assert seed_result.records_extracted == 100


# ---------------------------------------------------------------------------
# _execute_seed_phase — error path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_seed_phase_when_seed_raises_then_propagates_error() -> None:
    harness = _StageMixinHarness(seed_raises=RuntimeError("seed failure"))
    state = make_runner_state(
        state=CompositePipelineState.NOT_STARTED,
        seed_completed=False,
    )

    with pytest.raises(RuntimeError, match="seed failure"):
        await harness._execute_seed_phase(state)


# ---------------------------------------------------------------------------
# _resume_seed_phase
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_resume_seed_phase_when_state_already_seed_completed_then_no_fsm_transition() -> (
    None
):
    harness = _StageMixinHarness()
    state = make_runner_state(state=CompositePipelineState.SEED_COMPLETED)

    result = harness._resume_seed_phase(state)

    assert result is state
    harness._fsm.log_fsm_transition.assert_not_called()


@pytest.mark.unit
def test_resume_seed_phase_when_state_differs_then_fsm_transition_logged() -> None:
    harness = _StageMixinHarness()
    state = make_runner_state(state=CompositePipelineState.NOT_STARTED)

    harness._resume_seed_phase(state)

    harness._fsm.log_fsm_transition.assert_called_once()


@pytest.mark.unit
def test_resume_seed_phase_uses_recovery_transition_for_checkpoint_reconstruction() -> (
    None
):
    harness = _StageMixinHarness()
    state = CompositeCheckpointState(
        composite_name="test_composite",
        run_id="run-stage-test",
        state=CompositePipelineState.FAILED,
        seed_completed=True,
    )

    result = harness._resume_seed_phase(state)

    assert result.state == CompositePipelineState.SEED_COMPLETED
    harness._fsm.log_fsm_transition.assert_called_once()


# ---------------------------------------------------------------------------
# _skip_dependencies_phase
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_skip_dependencies_phase_when_called_then_returns_empty_dict() -> None:
    harness = _StageMixinHarness()
    state = make_runner_state()

    new_state, dep_results = await harness._skip_dependencies_phase(state)

    assert dep_results == {}
    assert new_state is state


# ---------------------------------------------------------------------------
# _execute_dependencies_phase — no deps configured
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_dependencies_phase_when_no_deps_configured_then_returns_empty() -> (
    None
):
    harness = _StageMixinHarness()
    harness._config.dependencies = []
    state = make_runner_state()

    import polars as pl

    _new_state, dep_results = await harness._execute_dependencies_phase(
        state, pl.DataFrame()
    )

    assert dep_results == {}


# ---------------------------------------------------------------------------
# _validate_dependency_preconditions
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_dependency_preconditions_when_coordinator_absent_then_raises() -> (
    None
):
    harness = _StageMixinHarness()
    harness._dependency_coordinator = None
    harness._dependencies_runner_factory = MagicMock()

    with pytest.raises(InvalidStateError):
        harness._validate_dependency_preconditions()


@pytest.mark.unit
def test_validate_dependency_preconditions_when_factory_absent_then_raises() -> None:
    harness = _StageMixinHarness()
    harness._dependency_coordinator = MagicMock()
    harness._dependencies_runner_factory = None

    with pytest.raises(InvalidStateError):
        harness._validate_dependency_preconditions()


@pytest.mark.unit
def test_validate_dependency_preconditions_when_both_present_then_returns_pair() -> (
    None
):
    harness = _StageMixinHarness()
    coordinator = MagicMock()
    factory = MagicMock()
    harness._dependency_coordinator = coordinator
    harness._dependencies_runner_factory = factory

    returned_coordinator, returned_factory = (
        harness._validate_dependency_preconditions()
    )

    assert returned_coordinator is coordinator
    assert returned_factory is factory


# ---------------------------------------------------------------------------
# _collect_successful_dependencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collect_successful_dependencies_when_success_then_marks_completed() -> None:
    harness = _StageMixinHarness()
    state = make_runner_state()
    results = {"dep_a": success_dep("dep_a")}

    harness._collect_successful_dependencies(state, results)

    state.with_dependency_completed.assert_called_once_with(
        "dep_a",
        results["dep_a"],
        clock=harness._clock,
    )


@pytest.mark.unit
def test_collect_successful_dependencies_when_failed_then_not_marked() -> None:
    harness = _StageMixinHarness()
    state = make_runner_state()
    results = {"dep_a": failed_dep("dep_a")}

    harness._collect_successful_dependencies(state, results)

    state.with_dependency_completed.assert_not_called()


@pytest.mark.unit
def test_collect_successful_dependencies_when_clock_missing_then_raises() -> None:
    harness = _StageMixinHarness()
    harness._clock = None
    state = make_runner_state()
    results = {"dep_a": success_dep("dep_a")}

    with pytest.raises(RuntimeError, match="ClockPort is required"):
        harness._collect_successful_dependencies(state, results)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_postprocess_dependency_results_when_mixed_then_finalizes_with_counts() -> (
    None
):
    harness = _StageMixinHarness(
        config=SimpleNamespace(
            name="test_composite",
            seed=SimpleNamespace(pipeline="seed_pipeline", silver_table="silver/seed"),
            enrichers=[],
            required_enrichers=[],
            dependencies=[make_dependency_cfg("dep_a"), make_dependency_cfg("dep_b")],
            get_dependency=lambda name: {
                "dep_a": make_dependency_cfg("dep_a"),
                "dep_b": make_dependency_cfg("dep_b"),
            }.get(name),
        )
    )
    state = make_runner_state()
    completed_state = make_runner_state(
        state=CompositePipelineState.DEPENDENCIES_COMPLETED
    )
    harness._complete_dependencies_phase = AsyncMock(return_value=completed_state)
    results = {"dep_a": success_dep("dep_a"), "dep_b": failed_dep("dep_b")}

    new_state, dep_results = await harness._postprocess_dependency_results(
        state, results
    )

    assert dep_results is results
    assert new_state is completed_state
    state.with_dependency_completed.assert_called_once_with(
        "dep_a",
        results["dep_a"],
        clock=harness._clock,
    )
    harness._complete_dependencies_phase.assert_awaited_once_with(
        state,
        succeeded=1,
        failed=1,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_dependencies_phase_when_required_failure_then_raises() -> None:
    dep_cfg = make_dependency_cfg("dep_a", required=True)
    harness = _StageMixinHarness(
        config=SimpleNamespace(
            name="test_composite",
            seed=SimpleNamespace(pipeline="seed_pipeline", silver_table="silver/seed"),
            enrichers=[],
            required_enrichers=[],
            dependencies=[dep_cfg],
            get_dependency=lambda name: dep_cfg if name == "dep_a" else None,
        )
    )
    state = make_runner_state()
    harness._persist_failed_state = AsyncMock(return_value=state)
    harness._complete_dependencies_phase = AsyncMock()
    outcome = harness._build_dependency_phase_outcome({"dep_a": failed_dep("dep_a")})

    with pytest.raises(InvalidStateError, match="Required dependencies failed"):
        await harness._finalize_dependencies_phase(state, outcome)

    harness._persist_failed_state.assert_awaited_once()
    harness._complete_dependencies_phase.assert_not_awaited()
