"""Shared public models for declarative workflow runner execution."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "WorkflowRunExecutionResult",
    "WorkflowStepExecutionResult",
]


@dataclass(frozen=True, slots=True)
class WorkflowStepExecutionResult:
    """Normalized result for one workflow DAG step."""

    step_id: str
    step_kind: str
    status: str
    payload: object | None = None
    error_type: str | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowRunExecutionResult:
    """Normalized result for one declarative workflow run."""

    workflow_name: str
    status: str
    steps: tuple[WorkflowStepExecutionResult, ...]
    workflow_run_id: str | None = None
    manifest_id: str | None = None
    execution_fingerprint: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    resumed: bool = False

    @property
    def is_success(self) -> bool:
        """Return whether every workflow step completed or was skipped."""
        return self.status == "success"
