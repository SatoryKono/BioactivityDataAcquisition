"""Unit tests for CompositeRunnerMergeStageMixin."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_mixin import (
    CompositeRunnerMergeStageMixin,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError, StorageError
from tests.helpers.clock import fixed_test_clock


# ---------------------------------------------------------------------------
# Fakes / factories
# ---------------------------------------------------------------------------


def _make_enricher_cfg(pipeline: str) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, required=False, silver_table=None)


def _make_dependency_cfg(pipeline: str) -> SimpleNamespace:
    return SimpleNamespace(pipeline=pipeline, silver_table="silver/dep")


def _make_state(
    state: CompositePipelineState = CompositePipelineState.ENRICHMENT_COMPLETED,
) -> MagicMock:
    mock = MagicMock()
    mock.state = state

    def _with_state(new_state, **kwargs):
        return _make_state(new_state)

    mock.with_state = MagicMock(side_effect=_with_state)
    return mock


def _success_enrichment(name: str) -> EnrichmentResult:
    return EnrichmentResult(enricher_name=name, status=EnrichmentStatus.SUCCESS)


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


class _MergeHarness(CompositeRunnerMergeStageMixin):
    """Minimal harness providing all required mixin attributes and seam stubs."""

    def __init__(self) -> None:
        self._config = SimpleNamespace(
            name="test_composite",
            seed=SimpleNamespace(
                pipeline="seed_pipeline",
                silver_table="silver/seed",
            ),
            enrichers=[],
            dependencies=[],
            merge=SimpleNamespace(
                output_silver_path="silver/composite/test",
                output_gold_path="gold/composite/test",
            ),
        )
        self._runtime = SimpleNamespace(dry_run=False)
        self._logger = MagicMock()
        self._observer_logger = MagicMock()
        self._observer = CompositeLifecycleObserverService(logger=self._observer_logger)
        self._run_id_str = "run-merge-test"
        self._clock = fixed_test_clock()
        self._fsm = MagicMock()
        self._merger = MagicMock()
        merge_call = AsyncMock(
            return_value=MergeResult(
                records_merged=10,
                records_from_seed=10,
            )
        )
        self._merger.merge = merge_call
        self._merger.execute_request = merge_call
        self._checkpoint_manager = AsyncMock()
        self._checkpoint_manager.delete = AsyncMock()

        self._dq_reports_called = False
        self._quarantine_called = False

    async def _save_checkpoint_safe(self, state: Any, operation: str) -> bool:
        await asyncio.sleep(0)
        return True

    async def _generate_dq_reports(self, merge_result: Any) -> None:
        await asyncio.sleep(0)
        self._dq_reports_called = True

    async def _write_cv_quarantine(self, merge_result: Any) -> None:
        await asyncio.sleep(0)
        self._quarantine_called = True


# ---------------------------------------------------------------------------
# _transition_to_merging_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transition_to_merging_state_when_called_then_validates_and_logs_fsm() -> None:
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.ENRICHMENT_COMPLETED)

    harness._transition_to_merging_state(state)

    harness._fsm.validate_fsm_transition.assert_called_once_with(
        CompositePipelineState.ENRICHMENT_COMPLETED,
        CompositePipelineState.MERGING,
    )
    harness._fsm.log_fsm_transition.assert_called_once()
    state.with_state.assert_called_once_with(
        CompositePipelineState.MERGING,
        clock=harness._clock,
    )


# ---------------------------------------------------------------------------
# _handle_dry_run_merge_skip
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_handle_dry_run_merge_skip_when_called_then_logs_and_returns_completed_state() -> (
    None
):
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.ENRICHMENT_COMPLETED)
    harness._runtime.dry_run = True

    returned = harness._handle_dry_run_merge_skip(state)

    assert returned.state == CompositePipelineState.COMPLETED
    harness._logger.info.assert_called_once()
    harness._fsm.log_fsm_transition.assert_called_once()
    state.with_state.assert_called_once_with(
        CompositePipelineState.COMPLETED,
        clock=harness._clock,
    )


# ---------------------------------------------------------------------------
# _transition_to_completed_state
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_transition_to_completed_state_when_already_completed_then_returns_same_state() -> (
    None
):
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.COMPLETED)

    returned = harness._transition_to_completed_state(state)

    assert returned is state
    harness._fsm.validate_fsm_transition.assert_not_called()


@pytest.mark.unit
def test_transition_to_completed_state_when_not_completed_then_transitions() -> None:
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.MERGING)

    harness._transition_to_completed_state(state)

    harness._fsm.validate_fsm_transition.assert_called_once_with(
        CompositePipelineState.MERGING,
        CompositePipelineState.COMPLETED,
    )
    harness._fsm.log_fsm_transition.assert_called_once()
    state.with_state.assert_called_once_with(
        CompositePipelineState.COMPLETED,
        clock=harness._clock,
    )


# ---------------------------------------------------------------------------
# _build_merge_inputs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_merge_inputs_when_no_results_then_returns_empty_lists() -> None:
    harness = _MergeHarness()

    prepared_inputs = harness._build_merge_inputs({}, {})

    assert prepared_inputs.enrichers == []
    assert prepared_inputs.dependencies == []


@pytest.mark.unit
def test_build_merge_inputs_when_success_enricher_then_included() -> None:
    cfg = _make_enricher_cfg("enricher_a")
    harness = _MergeHarness()
    harness._config.enrichers = [cfg]
    results = {"enricher_a": _success_enrichment("enricher_a")}

    prepared_inputs = harness._build_merge_inputs(results, {})

    assert cfg in prepared_inputs.enrichers
    assert prepared_inputs.dependencies == []


@pytest.mark.unit
def test_prepare_merge_request_when_called_then_binds_seed_and_inputs() -> None:
    dependency_cfg = _make_dependency_cfg("dep_a")
    harness = _MergeHarness()
    harness._config.enrichers = [_make_enricher_cfg("enricher_a")]
    harness._config.dependencies = [dependency_cfg]
    enrichment_results = {"enricher_a": _success_enrichment("enricher_a")}

    request = harness._prepare_merge_request(enrichment_results, {})

    assert request.seed_table == "silver/seed"
    assert request.seed_pipeline == "seed_pipeline"
    assert request.run_id == "run-merge-test"
    assert request.metadata_timestamp is None
    assert request.enrichment_results is enrichment_results
    assert request.enrichers[0].pipeline == "enricher_a"
    assert request.dependencies == []


@pytest.mark.unit
def test_prepare_merge_request_when_cached_bronze_date_present_then_uses_deterministic_timestamp() -> (
    None
):
    harness = _MergeHarness()
    harness._runtime.cached_bronze_date = "2026-04-10"

    request = harness._prepare_merge_request({}, {})

    assert request.metadata_timestamp == datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# _delete_checkpoint_safe
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_checkpoint_safe_when_success_then_deletes() -> None:
    harness = _MergeHarness()

    await harness._delete_checkpoint_safe()

    harness._checkpoint_manager.delete.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_checkpoint_safe_when_non_fatal_error_then_logs_warning() -> None:
    harness = _MergeHarness()
    harness._checkpoint_manager.delete = AsyncMock(
        side_effect=StorageError("delete failed")
    )

    await harness._delete_checkpoint_safe()

    harness._logger.warning.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_delete_checkpoint_safe_when_bioetl_error_then_logs_with_reason_code() -> (
    None
):
    harness = _MergeHarness()
    harness._checkpoint_manager.delete = AsyncMock(
        side_effect=BioETLError("unexpected domain error")
    )

    await harness._delete_checkpoint_safe()

    harness._logger.warning.assert_called_once()
    kwargs = harness._logger.warning.call_args.kwargs
    assert kwargs.get("reason_code") == "checkpoint_delete_failed"


# ---------------------------------------------------------------------------
# _handle_merge_phase_exception
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_merge_phase_exception_when_called_then_logs_error_and_saves_failed() -> (
    None
):
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.MERGING)

    await harness._handle_merge_phase_exception(state, RuntimeError("merge crash"))

    harness._logger.error.assert_called_once()
    harness._fsm.validate_fsm_transition.assert_called_once_with(
        CompositePipelineState.MERGING,
        CompositePipelineState.FAILED,
    )
    harness._fsm.log_fsm_transition.assert_called_once()
    fsm_kwargs = harness._fsm.log_fsm_transition.call_args.kwargs
    assert fsm_kwargs["to_state"] == CompositePipelineState.FAILED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_merge_phase_exception_when_bioetl_error_then_includes_reason_code() -> (
    None
):
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.MERGING)

    await harness._handle_merge_phase_exception(state, BioETLError("domain merge fail"))

    log_kwargs = harness._logger.error.call_args.kwargs
    assert log_kwargs.get("reason_code") == "unexpected_bioetl_error"


# ---------------------------------------------------------------------------
# _execute_merge_stage — dry-run path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_merge_stage_when_dry_run_then_skips_merge() -> None:
    harness = _MergeHarness()
    harness._runtime.dry_run = True
    state = _make_state(CompositePipelineState.ENRICHMENT_COMPLETED)

    _result_state, merge_result = await harness._execute_merge_stage(state, {})

    assert merge_result is None
    harness._merger.merge.assert_not_awaited()


# ---------------------------------------------------------------------------
# _execute_merge_stage — happy path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_merge_stage_when_merge_succeeds_then_returns_merge_result() -> (
    None
):
    harness = _MergeHarness()
    harness._runtime.dry_run = False
    state = _make_state(CompositePipelineState.ENRICHMENT_COMPLETED)

    _result_state, merge_result = await harness._execute_merge_stage(state, {})

    assert merge_result is not None
    assert merge_result.records_merged == 10
    harness._merger.merge.assert_awaited_once()
    assert harness._dq_reports_called is True
    assert harness._quarantine_called is True


# ---------------------------------------------------------------------------
# _execute_merge_stage — error path
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_execute_merge_stage_when_merger_raises_then_propagates_error() -> None:
    harness = _MergeHarness()
    harness._runtime.dry_run = False
    failing_merge = AsyncMock(side_effect=RuntimeError("merge failure"))
    harness._merger.merge = failing_merge
    harness._merger.execute_request = failing_merge
    state = _make_state(CompositePipelineState.ENRICHMENT_COMPLETED)

    with pytest.raises(RuntimeError, match="merge failure"):
        await harness._execute_merge_stage(state, {})

    harness._logger.error.assert_called_once()


# ---------------------------------------------------------------------------
# _finalize_pipeline
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
async def test_finalize_pipeline_when_called_then_sets_completed_and_deletes_checkpoint() -> (
    None
):
    harness = _MergeHarness()
    state = _make_state(CompositePipelineState.MERGING)

    await harness._finalize_pipeline(state)

    harness._fsm.validate_fsm_transition.assert_called_once()
    harness._checkpoint_manager.delete.assert_awaited_once()
