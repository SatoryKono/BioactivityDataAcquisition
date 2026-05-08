"""Port for workflow execution-state persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane import WorkflowExecutionState
from bioetl.domain.types import RunID

__all__ = ["WorkflowExecutionStatePort"]


@runtime_checkable
class WorkflowExecutionStatePort(Protocol):
    """Persist and retrieve workflow execution-state owner artifacts."""

    def save(self, state: WorkflowExecutionState) -> None:
        """Persist workflow execution state."""
        ...

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowExecutionState | None:
        """Load workflow execution state by run identifier."""
        ...

    def get_by_manifest_id(self, manifest_id: str) -> WorkflowExecutionState | None:
        """Load workflow execution state by manifest identifier."""
        ...

    def get_latest(self, workflow_name: str) -> WorkflowExecutionState | None:
        """Load the latest known workflow execution state for a workflow name."""
        ...
