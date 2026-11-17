"""Pure pending-step selection shared by dependency admission and execution."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.workflow.control_plane._execution_resume_support import (
    resolve_completed_transform_fingerprints,
    resolve_skipped_step_ids,
)
from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowTransformSpec,
)


@dataclass(frozen=True, slots=True)
class WorkflowMutationSpec:
    """Which configured steps can execute, without trusting caller launch metadata."""

    pending_step_ids: frozenset[str]
    resumed: bool = False


def build_workflow_mutation_plan(
    config: WorkflowConfig,
    state: WorkflowExecutionState | None = None,
    *,
    force_steps: tuple[str, ...] = (),
    repair_steps: tuple[str, ...] = (),
) -> WorkflowMutationSpec:
    """Use the runner's persisted success/selector/fingerprint skip semantics."""
    if state is None:
        return WorkflowMutationSpec(frozenset(config.step_ids))
    skipped = resolve_skipped_step_ids(
        state=state, force_steps=force_steps, repair_steps=repair_steps
    )
    completed = resolve_completed_transform_fingerprints(
        state=state,
        force_steps=force_steps,
        repair_steps=repair_steps,
    )
    cached_transforms = {
        step.step_id
        for step in config.steps
        if isinstance(step, TransformStepConfig)
        and completed.get(step.step_id)
        == WorkflowTransformSpec.from_step(step).fingerprint
    }
    return WorkflowMutationSpec(
        frozenset(config.step_ids).difference(skipped, cached_transforms), resumed=True
    )
