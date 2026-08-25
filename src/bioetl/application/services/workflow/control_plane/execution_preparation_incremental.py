"""Workflow-owned incremental-offset preparation helpers."""

from __future__ import annotations

from dataclasses import replace

from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.ports import WorkflowExecutionStatePort
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig


def _apply_incremental_offset(
    *,
    config: WorkflowConfig,
    workflow_state_port: WorkflowExecutionStatePort,
) -> WorkflowConfig:
    """Apply the next incremental offset when a successful previous run exists."""
    new_offset = _next_incremental_start_offset(
        workflow_state_port=workflow_state_port,
        workflow_name=config.name,
    )
    if new_offset is None:
        return config

    inherited_offset = config.defaults.start_offset
    return replace(
        config,
        defaults=replace(config.defaults, start_offset=new_offset),
        steps=tuple(
            _workflow_step_with_start_offset(step, new_offset)
            if isinstance(step, WorkflowStepConfig)
            and _step_inherits_incremental_offset(step, inherited_offset)
            else step
            for step in config.steps
        ),
    )


def _next_incremental_start_offset(
    *,
    workflow_state_port: WorkflowExecutionStatePort,
    workflow_name: str,
) -> int | None:
    """Resolve the next start offset from the latest successful workflow state."""
    latest_state = workflow_state_port.get_latest(workflow_name)
    return _offset_from_successful_state(latest_state)


def _offset_from_successful_state(state: WorkflowExecutionState | None) -> int | None:
    if state is None or state.status != "success":
        return None
    if state.last_limit is None:
        return None
    return (state.last_start_offset or 0) + state.last_limit


def _step_inherits_incremental_offset(
    step: WorkflowStepConfig,
    inherited_offset: int | None,
) -> bool:
    """Return whether a pipeline step should receive the workflow-level offset."""
    step_offset = step.run_options.start_offset
    return step_offset is None or step_offset == inherited_offset


def _workflow_step_with_start_offset(
    step: WorkflowStepConfig,
    start_offset: int,
) -> WorkflowStepConfig:
    return replace(
        step,
        run_options=replace(step.run_options, start_offset=start_offset),
    )


__all__ = [
    "_apply_incremental_offset",
    "_next_incremental_start_offset",
    "_offset_from_successful_state",
    "_workflow_step_with_start_offset",
]
