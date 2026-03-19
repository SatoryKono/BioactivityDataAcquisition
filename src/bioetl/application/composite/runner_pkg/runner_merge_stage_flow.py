"""Reusable merge-stage helpers for composite runner orchestration."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    PIPELINE_EXECUTION_ERRORS,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    get_mergeable_dependencies,
    get_mergeable_enrichers,
)
from bioetl.application.composite.runner_pkg.runner_merge_stage_types import (
    _CompositeRunnerMergeStageHostProtocol,
    _PreparedMergeInputs,
    _PreparedMergeRequest,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError

__all__ = [
    "build_merge_inputs",
    "build_merge_request",
    "delete_checkpoint_safe",
    "execute_merge_stage",
    "execute_started_merge_phase",
    "handle_dry_run_merge_skip",
    "handle_merge_phase_exception",
    "handle_merge_success",
    "persist_completed_state",
    "run_prepared_merge_request",
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
    merging_state = state.with_state(CompositePipelineState.MERGING)
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
    host._logger.info(
        PipelineEvent.phase_started("merge"),
        composite=host._config.name,
        run_id=host._run_id_str,
    )
    await host._call_save_checkpoint_safe(merging_state, "merging")
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
    host._fsm.log_fsm_transition(
        from_state=CompositePipelineState.MERGING,
        to_state=CompositePipelineState.FAILED,
        stage="merge_failed",
        error=str(error),
    )
    failed_state = state.with_state(CompositePipelineState.FAILED)
    await host._call_save_checkpoint_safe(failed_state, "merge_failed")


def build_merge_inputs(
    host: _CompositeRunnerMergeStageHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> _PreparedMergeInputs:
    """Build mergeable enrichers and dependencies for the merge stage."""
    mergeable_enrichers = get_mergeable_enrichers(
        enrichment_results,
        host._config.enrichers,
        host._logger,
    )
    mergeable_dependencies = get_mergeable_dependencies(
        dependency_results or {},
        host._config.dependencies,
        host._logger,
    )
    return _PreparedMergeInputs(
        enrichers=mergeable_enrichers,
        dependencies=mergeable_dependencies,
    )


def build_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> _PreparedMergeRequest:
    """Build the canonical merge request for the merger seam."""
    prepared_inputs = build_merge_inputs(
        host,
        enrichment_results,
        dependency_results,
    )
    return _PreparedMergeRequest(
        seed_table=host._config.seed.silver_table,
        seed_pipeline=host._config.seed.pipeline,
        enrichers=prepared_inputs.enrichers,
        enrichment_results=enrichment_results,
        run_id=host._run_id_str,
        dependencies=prepared_inputs.dependencies,
        dependency_results=dependency_results,
    )


async def run_prepared_merge_request(
    host: _CompositeRunnerMergeStageHostProtocol,
    request: _PreparedMergeRequest,
) -> MergeResult:
    """Run merger through a normalized request context."""
    return await host._merger.merge(
        seed_table=request.seed_table,
        enrichers=request.enrichers,
        enrichment_results=request.enrichment_results,
        run_id=request.run_id,
        seed_pipeline=request.seed_pipeline,
        dependencies=request.dependencies,
        dependency_results=request.dependency_results,
    )


async def execute_started_merge_phase(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
    *,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None,
) -> MergeResult:
    """Run merge after the phase has been started and handle success/errors."""
    try:
        prepared_request = build_merge_request(
            host,
            enrichment_results,
            dependency_results,
        )
        merge_result = await run_prepared_merge_request(host, prepared_request)
        await handle_merge_success(host, merge_result)
    except (*PIPELINE_EXECUTION_ERRORS, BioETLError) as merge_error:
        await handle_merge_phase_exception(host, state, merge_error)
        raise
    return merge_result


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
    completed_state = state.with_state(CompositePipelineState.COMPLETED)
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
    host._logger.info(
        PipelineEvent.phase_completed("merge"),
        composite=host._config.name,
        run_id=host._run_id_str,
        records_merged=merge_result.records_merged,
    )
    await host._call_generate_dq_reports(merge_result)
    await host._call_write_cv_quarantine(merge_result)


async def execute_merge_stage(
    host: _CompositeRunnerMergeStageHostProtocol,
    state: CompositeCheckpointState,
    enrichment_results: dict[str, EnrichmentResult],
    dependency_results: dict[str, DependencyResult] | None = None,
) -> tuple[CompositeCheckpointState, MergeResult | None]:
    """Execute merge stage or skip it in dry-run mode."""
    merge_result: MergeResult | None = None

    if not host._runtime.dry_run:
        state = await start_merge_phase(host, state)
        merge_result = await execute_started_merge_phase(
            host,
            state,
            enrichment_results=enrichment_results,
            dependency_results=dependency_results,
        )
    else:
        state = handle_dry_run_merge_skip(host, state)

    return state, merge_result
