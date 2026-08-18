"""Workflow step transition policy (domain pure).

ARCH-REF-06 / #7707: invariants for step run/skip dispositions live in domain,
not application services. Application re-exports remain available via
``bioetl.application.services.workflow.workflow_transition_policy``.
"""

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
    """Pure transition decision for one workflow step (domain policy VO)."""

    disposition: str
    stores_output: bool
    failed_step_id: str | None = None

    def __post_init__(self) -> None:
        allowed = {
            _DISPOSITION_RUN,
            _DISPOSITION_SKIP_FAILED,
            _DISPOSITION_SKIP_COMPLETED,
        }
        if self.disposition not in allowed:
            raise ValueError(
                f"Unknown workflow step disposition: {self.disposition!r}"
            )
        self.ensure_runnable()

    @property
    def should_run(self) -> bool:
        """Return whether the current step should execute."""
        return self.disposition == _DISPOSITION_RUN

    def ensure_runnable(self) -> None:
        """Invariant: skip dispositions must not claim stores_output."""
        if self.disposition != _DISPOSITION_RUN and self.stores_output:
            raise ValueError(
                "WorkflowStepTransitionPolicy invariant violated: "
                f"disposition={self.disposition!r} cannot set stores_output=True"
            )


def resolve_step_transition_policy(
    step: WorkflowStepDefinition,
    *,
    failed_step_id: str | None,
    completed_step_ids: frozenset[str] | None,
) -> WorkflowStepTransitionPolicy:
    """Resolve whether a step should run or be skipped by workflow state."""
    if failed_step_id is not None:
        policy = WorkflowStepTransitionPolicy(
            disposition=_DISPOSITION_SKIP_FAILED,
            stores_output=False,
            failed_step_id=failed_step_id,
        )
        policy.ensure_runnable()
        return policy
    if completed_step_ids and step.step_id in completed_step_ids:
        policy = WorkflowStepTransitionPolicy(
            disposition=_DISPOSITION_SKIP_COMPLETED,
            stores_output=False,
        )
        policy.ensure_runnable()
        return policy
    policy = WorkflowStepTransitionPolicy(
        disposition=_DISPOSITION_RUN,
        stores_output=True,
    )
    policy.ensure_runnable()
    return policy


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
