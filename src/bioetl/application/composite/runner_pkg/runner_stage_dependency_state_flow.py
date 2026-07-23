"""Dependency state-transition helpers for composite runner orchestration."""

from __future__ import annotations

__all__ = [
    "complete_dependencies_phase",
    "handle_dependencies_phase_exception",
    "start_dependencies_phase",
]

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_stage_payloads import (
    build_dependency_stage_details,
)
from bioetl.application.composite.runner_pkg.runner_stage_start_flow import (
    start_composite_phase,
)
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import BioETLError


async def start_dependencies_phase(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
    *,
    dependency_pipeline_names: list[str],
) -> CompositeCheckpointState:
    """Transition to DEPENDENCIES_RUNNING, persist checkpoint, and emit log."""
    stage_details = build_dependency_stage_details(dependency_pipeline_names)
    return await start_composite_phase(
        host,
        state,
        to_state=CompositePipelineState.DEPENDENCIES_RUNNING,
        stage="dependencies_start",
        checkpoint_operation="dependencies_running",
        phase_name="dependencies",
        transition_details=stage_details,
        log_details=stage_details,
        on_started=lambda: host._record_dependencies_stage_started(
            dependency_pipeline_names
        ),
    )


async def complete_dependencies_phase(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
    *,
    succeeded: int,
    failed: int,
) -> CompositeCheckpointState:
    """Transition to DEPENDENCIES_COMPLETED, log, and persist checkpoint."""
    completed_state = host._transition_state_with_fsm_log(
        state,
        CompositePipelineState.DEPENDENCIES_COMPLETED,
        stage="dependencies_complete",
        succeeded=succeeded,
        failed=failed,
    )
    host._observer.emit_phase_completed(
        composite_name=host._config.name,
        run_id=host._run_id_str,
        phase_name="dependencies",
        details={
            "succeeded": succeeded,
            "failed": failed,
        },
    )
    await host._call_save_checkpoint_safe(completed_state, "dependencies_completed")
    return completed_state


async def handle_dependencies_phase_exception(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
    error: Exception,
) -> None:
    """Log dependency-phase failure and persist FAILED checkpoint."""
    log_kwargs: dict[str, object] = {
        "composite": host._config.name,
        "run_id": host._run_id_str,
        "error": str(error),
        "error_type": type(error).__name__,
    }
    if isinstance(error, BioETLError):
        reason_code = error.get_reason_code()
        log_kwargs["reason_code"] = reason_code or "unexpected_bioetl_error"
    host._logger.error("Dependencies phase failed", **log_kwargs)
    await host._persist_failed_state(
        state,
        stage="dependencies_failed",
        error=str(error),
    )
