"""Unit tests for _CompositeRunnerStageSupportMixin."""

from __future__ import annotations

from types import SimpleNamespace
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_mixin import (
    _CompositeRunnerStageSupportMixin,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _make_checkpoint_state(
    state: CompositePipelineState = CompositePipelineState.NOT_STARTED,
) -> MagicMock:
    mock_state = MagicMock()
    mock_state.state = state
    mock_state.with_state = MagicMock(return_value=mock_state)
    mock_state.with_seed_completed = MagicMock(return_value=mock_state)
    mock_state.with_dependency_completed = MagicMock(return_value=mock_state)
    return mock_state


def _make_dependency_cfg(
    pipeline: str,
    *,
    required: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, required=required)


def _success_dep(name: str) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=DependencyStatus.SUCCESS)


def _failed_dep(name: str) -> DependencyResult:
    return DependencyResult(pipeline_name=name, status=DependencyStatus.FAILED)


def _dep_cfg_lookup(dep_cfg: SimpleNamespace, name: str) -> SimpleNamespace | None:
    if name == dep_cfg.pipeline:
        return dep_cfg
    return None


def _make_dependency_lookup(
    dep_cfg: SimpleNamespace,
) -> Callable[[str], SimpleNamespace | None]:
    def _lookup(name: str) -> SimpleNamespace | None:
        return _dep_cfg_lookup(dep_cfg, name)

    return _lookup


class _StageSupportHarness(_CompositeRunnerStageSupportMixin):
    """Concrete harness that stubs out all abstract seams."""

    def __init__(self, config: Any | None = None) -> None:
        self._config = config or SimpleNamespace(
            name="test_composite",
            seed=SimpleNamespace(pipeline="seed_pipeline"),
            enrichers=[],
            required_enrichers=[],
            dependencies=[],
        )
        self._runtime = SimpleNamespace(
            required_only=False,
            enrich_only=None,
            force_enricher=None,
        )
        self._logger = MagicMock()
        self._observer_logger = MagicMock()
        self._observer = CompositeLifecycleObserverService(logger=self._observer_logger)
        self._run_id_str = "run-stage-support-test"
        self._fsm = MagicMock()
        self._checkpoint_manager = AsyncMock()
        self._dependency_coordinator = None
        self._dependencies_runner_factory = None
        self._coordinator = MagicMock()
        self._enricher_runner_factory = MagicMock()

        # Wire abstract seams to trackable stubs
        self._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

    async def _save_checkpoint_safe(  # type: ignore[override]
        self,
        state: Any,
        operation: str,
    ) -> bool:
        return True

    async def _run_seed(self) -> Any:  # type: ignore[override]
        raise NotImplementedError("inject via test")

    def _get_enrichers_to_run(self, state: Any) -> list[Any]:  # type: ignore[override]
        return []

    def _check_required_enrichers(self, results: Any) -> None:  # type: ignore[override]
        pass


# ---------------------------------------------------------------------------
# _call_save_checkpoint_safe delegates to _save_checkpoint_safe
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_call_save_checkpoint_safe_when_invoked_then_delegates() -> None:
    harness = _StageSupportHarness()
    state = _make_checkpoint_state()
    harness._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

    result = await harness._call_save_checkpoint_safe(state, "test_op")

    assert result is True
    harness._save_checkpoint_safe.assert_awaited_once_with(state, "test_op")


# ---------------------------------------------------------------------------
# _has_dependencies_configured
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_has_dependencies_configured_when_missing_coordinator_then_returns_false() -> (
    None
):
    harness = _StageSupportHarness()
    harness._config.dependencies = [_make_dependency_cfg("dep_a")]
    harness._dependency_coordinator = None
    harness._dependencies_runner_factory = MagicMock()

    assert harness._has_dependencies_configured() is False


@pytest.mark.unit
def test_has_dependencies_configured_when_all_present_then_returns_true() -> None:
    harness = _StageSupportHarness()
    harness._config.dependencies = [_make_dependency_cfg("dep_a")]
    harness._dependency_coordinator = MagicMock()
    harness._dependencies_runner_factory = MagicMock()

    assert harness._has_dependencies_configured() is True


@pytest.mark.unit
def test_has_dependencies_configured_when_no_deps_configured_then_returns_false() -> (
    None
):
    harness = _StageSupportHarness()
    harness._config.dependencies = []

    assert harness._has_dependencies_configured() is False


# ---------------------------------------------------------------------------
# _find_required_failures
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_find_required_failures_when_all_succeed_then_empty_list() -> None:
    dep_cfg = _make_dependency_cfg("dep_a", required=True)
    harness = _StageSupportHarness()
    harness._config.dependencies = [dep_cfg]
    harness._config.get_dependency = _make_dependency_lookup(dep_cfg)
    results = {"dep_a": _success_dep("dep_a")}

    failed = harness._find_required_failures(results)

    assert failed == []


@pytest.mark.unit
def test_find_required_failures_when_required_dep_fails_then_included() -> None:
    dep_cfg = _make_dependency_cfg("dep_a", required=True)
    harness = _StageSupportHarness()
    harness._config.get_dependency = _make_dependency_lookup(dep_cfg)
    results = {"dep_a": _failed_dep("dep_a")}

    failed = harness._find_required_failures(results)

    assert "dep_a" in failed


@pytest.mark.unit
def test_find_required_failures_when_optional_dep_fails_then_not_included() -> None:
    dep_cfg = _make_dependency_cfg("opt_dep", required=False)
    harness = _StageSupportHarness()
    harness._config.get_dependency = _make_dependency_lookup(dep_cfg)
    results = {"opt_dep": _failed_dep("opt_dep")}

    failed = harness._find_required_failures(results)

    assert "opt_dep" not in failed


# ---------------------------------------------------------------------------
# _summarize_dependency_outcomes (static method)
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "results,expected_succeeded,expected_failed",
    [
        ({}, 0, 0),
        ({"a": _success_dep("a")}, 1, 0),
        ({"a": _failed_dep("a")}, 0, 1),
        ({"a": _success_dep("a"), "b": _failed_dep("b")}, 1, 1),
        (
            {
                "a": _success_dep("a"),
                "b": _success_dep("b"),
                "c": _failed_dep("c"),
            },
            2,
            1,
        ),
    ],
)
def test_summarize_dependency_outcomes_when_various_inputs_then_correct_counts(
    results: dict[str, DependencyResult],
    expected_succeeded: int,
    expected_failed: int,
) -> None:
    succeeded, failed = _StageSupportHarness._summarize_dependency_outcomes(results)

    assert succeeded == expected_succeeded
    assert failed == expected_failed


# ---------------------------------------------------------------------------
# _transition_state_with_fsm_log
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transition_state_with_fsm_log_when_validate_true_then_calls_fsm_validate() -> (
    None
):
    harness = _StageSupportHarness()
    state = _make_checkpoint_state(CompositePipelineState.NOT_STARTED)
    to_state = CompositePipelineState.SEED_RUNNING

    harness._transition_state_with_fsm_log(state, to_state, stage="test", validate=True)

    harness._fsm.validate_fsm_transition.assert_called_once_with(
        CompositePipelineState.NOT_STARTED,
        to_state,
    )


@pytest.mark.unit
def test_transition_state_with_fsm_log_when_validate_false_then_skips_fsm_validate() -> (
    None
):
    harness = _StageSupportHarness()
    state = _make_checkpoint_state(CompositePipelineState.NOT_STARTED)

    harness._transition_state_with_fsm_log(
        state,
        CompositePipelineState.FAILED,
        stage="error",
        validate=False,
    )

    harness._fsm.validate_fsm_transition.assert_not_called()


@pytest.mark.unit
def test_transition_state_with_fsm_log_when_called_then_logs_transition() -> None:
    harness = _StageSupportHarness()
    state = _make_checkpoint_state(CompositePipelineState.NOT_STARTED)
    to_state = CompositePipelineState.SEED_RUNNING

    harness._transition_state_with_fsm_log(
        state, to_state, stage="seed_start", validate=False
    )

    harness._fsm.log_fsm_transition.assert_called_once()
    call_kwargs = harness._fsm.log_fsm_transition.call_args.kwargs
    assert call_kwargs["from_state"] == CompositePipelineState.NOT_STARTED
    assert call_kwargs["to_state"] == to_state
    assert call_kwargs["stage"] == "seed_start"


# ---------------------------------------------------------------------------
# _persist_failed_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_failed_state_when_called_then_transitions_to_failed_and_saves() -> (
    None
):
    harness = _StageSupportHarness()
    save_mock = AsyncMock(return_value=True)
    harness._save_checkpoint_safe = save_mock  # type: ignore[method-assign]
    state = _make_checkpoint_state(CompositePipelineState.SEED_RUNNING)

    await harness._persist_failed_state(
        state,
        stage="seed_failed",
        error="test error",
    )

    save_mock.assert_awaited_once()
    harness._fsm.log_fsm_transition.assert_called_once()
    fsm_kwargs = harness._fsm.log_fsm_transition.call_args.kwargs
    assert fsm_kwargs["to_state"] == CompositePipelineState.FAILED
    assert fsm_kwargs["stage"] == "seed_failed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_seed_phase_when_called_then_logs_running_to_completed() -> None:
    harness = _StageSupportHarness()
    running_state = _make_checkpoint_state(CompositePipelineState.SEED_RUNNING)
    completed_state = _make_checkpoint_state(CompositePipelineState.SEED_COMPLETED)
    running_state.with_seed_completed.return_value = completed_state
    harness._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]

    seed_result = SimpleNamespace(records_extracted=100, records_silver=90)

    result = await harness._complete_seed_phase(running_state, seed_result)

    assert result is completed_state
    harness._fsm.validate_fsm_transition.assert_called_once_with(
        CompositePipelineState.SEED_RUNNING,
        CompositePipelineState.SEED_COMPLETED,
    )
    harness._fsm.log_fsm_transition.assert_called_once()
    fsm_kwargs = harness._fsm.log_fsm_transition.call_args.kwargs
    assert fsm_kwargs["from_state"] == CompositePipelineState.SEED_RUNNING
    assert fsm_kwargs["to_state"] == CompositePipelineState.SEED_COMPLETED
    assert fsm_kwargs["stage"] == "seed_complete"


# ---------------------------------------------------------------------------
# _fail_required_dependencies
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fail_required_dependencies_when_called_then_raises_invalid_state() -> (
    None
):
    harness = _StageSupportHarness()
    harness._save_checkpoint_safe = AsyncMock(return_value=True)  # type: ignore[method-assign]
    state = _make_checkpoint_state(CompositePipelineState.DEPENDENCIES_RUNNING)

    with pytest.raises(InvalidStateError, match="Required dependencies failed"):
        await harness._fail_required_dependencies(state, ["dep_a"])
