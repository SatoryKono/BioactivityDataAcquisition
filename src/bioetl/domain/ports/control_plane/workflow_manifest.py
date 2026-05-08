"""Port for workflow-manifest persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane import WorkflowManifest
from bioetl.domain.types import RunID

__all__ = ["WorkflowManifestPort"]


@runtime_checkable
class WorkflowManifestPort(Protocol):
    """Persist and retrieve immutable workflow-manifest records."""

    def save(self, manifest: WorkflowManifest) -> None:
        """Persist one immutable workflow manifest."""
        ...

    def get(self, manifest_id: str) -> WorkflowManifest | None:
        """Load a workflow manifest by identifier."""
        ...

    def get_by_run_id(self, workflow_run_id: RunID) -> WorkflowManifest | None:
        """Load the manifest linked to a workflow run identifier."""
        ...
