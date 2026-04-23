"""State-transition helpers for composite runner stage orchestration."""

from __future__ import annotations

__all__ = [
    "complete_seed_phase",
    "fail_required_dependencies",
    "find_required_failures",
    "handle_seed_phase_exception",
    "persist_failed_state",
    "start_seed_phase",
    "summarize_dependency_outcomes",
    "transition_state_with_fsm_log",
]

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_stage_start_flow import (
    start_composite_phase,
)
from bioetl.application.composite.runner_pkg.runner_stage_support_types import (
    _CompositeRunnerStageSupportHostProtocol,
)
from bioetl.domain.composite.result import DependencyResult, SeedResult
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError, InvalidStateError


def find_required_failures(
    host: _CompositeRunnerStageSupportHostProtocol,
    results: dict[str, DependencyResult],
) -> list[str]:
    """Find required dependencies that failed."""
    failed: list[str] = []
    for name, result in results.items():
        if result.is_success:
            continue
        dep_cfg = host._config.get_dependency(name)
        if dep_cfg and dep_cfg.required:
            failed.append(name)
    return failed


def transition_state_with_fsm_log(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
    to_state: CompositePipelineState,
    *,
    stage: str,
    validate: bool = True,
    **transition_kwargs: object,
) -> CompositeCheckpointState:
    """Transition immutable state and emit FSM log entry."""
    previous_state = state.state
    if validate:
        host._fsm.validate_fsm_transition(previous_state, to_state)
    next_state = state.with_state(to_state, clock=getattr(host, "_clock", None))
    host._fsm.log_fsm_transition(
        from_state=previous_state,
        to_state=to_state,
        stage=stage,
        **transition_kwargs,
    )
    return next_state


async def persist_failed_state(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
    *,
    stage: str,
    error: str,
) -> CompositeCheckpointState:
    """Transition to FAILED and persist checkpoint via the shared safe seam."""
    failed_state = transition_state_with_fsm_log(
        host,
        state,
        CompositePipelineState.FAILED,
        stage=stage,
        validate=False,
        error=error,
    )
    await host._call_save_checkpoint_safe(failed_state, stage)
    return failed_state


async def start_seed_phase(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
) -> CompositeCheckpointState:
    """Transition checkpoint/FSM to SEED_RUNNING and persist checkpoint."""
    return await start_composite_phase(
        host,
        state,
        to_state=CompositePipelineState.SEED_RUNNING,
        stage="seed_start",
        checkpoint_operation="seed_running",
        phase_name="seed",
        on_started=host._record_seed_stage_started,
    )


async def complete_seed_phase(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
    seed_result: SeedResult,
) -> CompositeCheckpointState:
    """Record successful seed completion and persist checkpoint."""
    previous_state = state.state
    completed_state = state.with_seed_completed(
        seed_result,
        clock=getattr(host, "_clock", None),
    )
    host._fsm.validate_fsm_transition(
        previous_state,
        CompositePipelineState.SEED_COMPLETED,
    )
    host._fsm.log_fsm_transition(
        from_state=previous_state,
        to_state=CompositePipelineState.SEED_COMPLETED,
        stage="seed_complete",
        records_extracted=seed_result.records_extracted,
        records_silver=seed_result.records_silver,
    )
    host._observer.emit_phase_completed(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="seed",
        details={
            "records_extracted": seed_result.records_extracted,
            "records_silver": seed_result.records_silver,
        },
    )
    await host._call_save_checkpoint_safe(completed_state, "seed_completed")
    host._record_seed_stage_completed(seed_result)
    return completed_state


async def handle_seed_phase_exception(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
    error: Exception,
) -> None:
    """Handle seed-phase failure and persist FAILED checkpoint."""
    log_kwargs: dict[str, object] = {
        "composite": host._config.name,
        "run_id": host._run_id_str,
        "seed_pipeline": host._config.seed.pipeline,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    if isinstance(error, BioETLError):
        log_kwargs["reason_code"] = "unexpected_bioetl_error"
    host._logger.error("Seed pipeline failed", **log_kwargs)
    await host._persist_failed_state(
        state,
        stage="seed_failed",
        error=str(error),
    )


async def fail_required_dependencies(
    host: _CompositeRunnerStageSupportHostProtocol,
    state: CompositeCheckpointState,
    required_failed: list[str],
) -> None:
    """Persist dependency failure state when required dependencies fail."""
    await host._persist_failed_state(
        state,
        stage="dependencies_failed",
        error=f"Required dependencies failed: {required_failed}",
    )
    raise InvalidStateError(f"Required dependencies failed: {required_failed}")


def summarize_dependency_outcomes(
    dependency_results: dict[str, DependencyResult],
) -> tuple[int, int]:
    """Return counts of successful and failed dependency executions."""
    succeeded = sum(1 for result in dependency_results.values() if result.is_success)
    failed = len(dependency_results) - succeeded
    return succeeded, failed
