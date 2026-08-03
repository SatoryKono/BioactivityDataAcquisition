"""Pure workflow step transition policy for declarative workflow execution."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.workflow import TransformStepConfig, WorkflowStepConfig

__all__ = [
    "WorkflowStepDefinition",
    "WorkflowStepTransitionPolicy",
    "apply_step_result_transition",
    "resolve_step_transition_policy",
    "step_kind_for_config",
]

WorkflowStepDefinition = WorkflowStepConfig | TransformStepConfig

_STEP_KIND_PIPELINE = "pipeline"
_DISPOSITION_RUN = "run"
_DISPOSITION_SKIP_FAILED = "skip_failed"
_DISPOSITION_SKIP_COMPLETED = "skip_completed"


@dataclass(frozen=True, slots=True)
class WorkflowStepTransitionPolicy:
    """Pure transition decision for one workflow step."""

    disposition: str
    stores_output: bool
    failed_step_id: str | None = None

    @property
    def should_run(self) -> bool:
        """Return whether the current step should execute."""
        return self.disposition == _DISPOSITION_RUN


def resolve_step_transition_policy(
    step: WorkflowStepDefinition,
    *,
    failed_step_id: str | None,
    completed_step_ids: frozenset[str] | None,
) -> WorkflowStepTransitionPolicy:
    """Resolve whether a step should run or be skipped by workflow state."""
    if failed_step_id is not None:
        return WorkflowStepTransitionPolicy(
            disposition=_DISPOSITION_SKIP_FAILED,
            stores_output=False,
            failed_step_id=failed_step_id,
        )
    if completed_step_ids and step.step_id in completed_step_ids:
        return WorkflowStepTransitionPolicy(
            disposition=_DISPOSITION_SKIP_COMPLETED,
            stores_output=False,
        )
    return WorkflowStepTransitionPolicy(
        disposition=_DISPOSITION_RUN,
        stores_output=True,
    )


def apply_step_result_transition(
    *,
    step: WorkflowStepDefinition,
    result_status: str,
    workflow_status: str,
    failed_step_id: str | None,
) -> tuple[str, str | None]:
    """Return next workflow terminal status and failed step anchor."""
    if failed_step_id is not None:
        return workflow_status, failed_step_id
    if result_status == "failed":
        return "failed", step.step_id
    return workflow_status, None


def step_kind_for_config(step: WorkflowStepDefinition) -> str:
    """Return canonical workflow step kind label."""
    return _STEP_KIND_PIPELINE if isinstance(step, WorkflowStepConfig) else "transform"
