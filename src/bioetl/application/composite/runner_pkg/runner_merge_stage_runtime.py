"""Stage-local transition and observability helpers for composite merge flow."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
)
from bioetl.domain.composite.result import MergeResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError

__all__ = [
    "delete_checkpoint_safe",
    "handle_dry_run_merge_skip",
    "handle_merge_phase_exception",
    "handle_merge_success",
    "persist_completed_state",
    "start_merge_phase",
    "transition_to_completed_state",
    "transition_to_merging_state",
]


def transition_to_merging_state(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Return MERGING state and emit the corresponding FSM transition log."""
    previous_state = state.state
    host._fsm.validate_fsm_transition(
        previous_state,
        CompositePipelineState.MERGING,
    )
    merging_state = state.with_state(
        CompositePipelineState.MERGING,
        clock=getattr(host, "_clock", None),
    )
    host._fsm.log_fsm_transition(
        from_state=previous_state,
        to_state=CompositePipelineState.MERGING,
        stage="merge_start",
    )
    return merging_state


async def start_merge_phase(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Transition checkpoint/FSM to MERGING and persist checkpoint."""
    merging_state = transition_to_merging_state(host, state)
    await host._call_save_checkpoint_safe(merging_state, "merging")
    host._record_merge_stage_started()
    host._observer.emit_phase_started(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="merge",
    )
    return merging_state


async def handle_merge_phase_exception(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
    error: Exception,
) -> None:
    """Log merge-phase failure and persist FAILED checkpoint."""
    log_kwargs: dict[str, object] = {
        "composite": host._config.name,
        "run_id": host._run_id_str,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    if isinstance(error, BioETLError):
        log_kwargs["reason_code"] = "unexpected_bioetl_error"
    host._logger.error("Merge failed", **log_kwargs)
    host._fsm.validate_fsm_transition(
        CompositePipelineState.MERGING,
        CompositePipelineState.FAILED,
    )
    host._fsm.log_fsm_transition(
        from_state=CompositePipelineState.MERGING,
        to_state=CompositePipelineState.FAILED,
        stage="merge_failed",
        error=str(error),
    )
    failed_state = state.with_state(
        CompositePipelineState.FAILED,
        clock=getattr(host, "_clock", None),
    )
    await host._call_save_checkpoint_safe(failed_state, "merge_failed")


def handle_dry_run_merge_skip(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Log dry-run merge skip and leave checkpoint state unchanged."""
    host._fsm.log_fsm_transition(
        from_state=state.state,
        to_state=CompositePipelineState.COMPLETED,
        stage="dry_run_skip_merge",
        reason="dry_run_mode",
    )
    host._logger.info(
        "Dry run: merge skipped, pipeline completing",
        composite=host._config.name,
        run_id=host._run_id_str,
    )
    return state


async def delete_checkpoint_safe(
    host: _CompositeRunnerMergeStageHostProtocol,
) -> None:
    """Delete checkpoint with graceful warning-only error handling."""
    try:
        await host._checkpoint_manager.delete()
    except CHECKPOINT_NON_FATAL_ERRORS as delete_error:
        host._logger.warning(
            "Failed to delete checkpoint",
            composite=host._config.name,
            run_id=host._run_id_str,
            error=str(delete_error),
            error_type=type(delete_error).__name__,
        )
    except BioETLError as delete_error:
        host._logger.warning(
            "Failed to delete checkpoint",
            composite=host._config.name,
            run_id=host._run_id_str,
            error=str(delete_error),
            error_type=type(delete_error).__name__,
            reason_code="checkpoint_delete_failed",
        )


def transition_to_completed_state(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Return finalized COMPLETED state, logging FSM transition only when needed."""
    if state.state == CompositePipelineState.COMPLETED:
        return state

    previous_state = state.state
    host._fsm.validate_fsm_transition(
        previous_state,
        CompositePipelineState.COMPLETED,
    )
    completed_state = state.with_state(
        CompositePipelineState.COMPLETED,
        clock=getattr(host, "_clock", None),
    )
    host._fsm.log_fsm_transition(
        from_state=previous_state,
        to_state=CompositePipelineState.COMPLETED,
        stage="pipeline_complete",
    )
    return completed_state


async def persist_completed_state(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
) -> None:
    """Persist finalized checkpoint state via the shared completed-operation seam."""
    await host._call_save_checkpoint_safe(state, "completed")


async def handle_merge_success(
    host: _CompositeRunnerMergeStageHostProtocol,
    merge_result: MergeResult,
) -> None:
    """Emit merge success observability and post-merge side effects."""
    host._observer.emit_phase_completed(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="merge",
        details={"records_merged": merge_result.records_merged},
    )
    await host._call_generate_dq_reports(merge_result)
    await host._call_write_cv_quarantine(merge_result)
    host._record_merge_stage_completed(merge_result)
