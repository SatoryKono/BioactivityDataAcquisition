"""Dependency state-transition helpers for composite runner orchestration."""

from __future__ import annotations

__all__ = [
    "complete_dependencies_phase",
    "handle_dependencies_phase_exception",
    "start_dependencies_phase",
]

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg.runner_stage_types import (
    _CompositeRunnerStageHostProtocol,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.events import PipelineEvent
from bioetl.domain.exceptions import BioETLError


def _record_dependencies_stage_started_if_supported(
    host: _CompositeRunnerStageHostProtocol,
    dependency_pipeline_names: list[str],
) -> None:
    """Record optional dependency-stage start event when host exposes callback."""
    record = getattr(host, "_record_dependencies_stage_started", None)
    if callable(record):
        record(dependency_pipeline_names)


async def start_dependencies_phase(
    host: _CompositeRunnerStageHostProtocol,
    state: CompositeCheckpointState,
    *,
    dependency_pipeline_names: list[str],
) -> CompositeCheckpointState:
    """Transition to DEPENDENCIES_RUNNING, persist checkpoint, and emit log."""
    next_state = host._transition_state_with_fsm_log(
        state,
        CompositePipelineState.DEPENDENCIES_RUNNING,
        stage="dependencies_start",
        dependencies=dependency_pipeline_names,
        count=len(dependency_pipeline_names),
    )
    await host._call_save_checkpoint_safe(next_state, "dependencies_running")
    _record_dependencies_stage_started_if_supported(host, dependency_pipeline_names)
    host._logger.info(
        PipelineEvent.phase_started("dependencies"),
        composite=host._config.name,
        run_id=host._run_id_str,
        dependencies=dependency_pipeline_names,
        count=len(dependency_pipeline_names),
    )
    return next_state


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
        validate=False,
        succeeded=succeeded,
        failed=failed,
    )
    host._logger.info(
        PipelineEvent.phase_completed("dependencies"),
        composite=host._config.name,
        run_id=host._run_id_str,
        succeeded=succeeded,
        failed=failed,
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
        log_kwargs["reason_code"] = "unexpected_bioetl_error"
    host._logger.error("Dependencies phase failed", **log_kwargs)
    await host._persist_failed_state(
        state,
        stage="dependencies_failed",
        error=str(error),
    )
