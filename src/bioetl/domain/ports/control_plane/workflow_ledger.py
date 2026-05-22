"""Port for workflow-ledger persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.workflow_ledger import WorkflowLedgerEntry
from bioetl.domain.types import RunID

__all__ = ["WorkflowLedgerPort"]


@runtime_checkable
class WorkflowLedgerPort(Protocol):
    """Persist and query append-only workflow-ledger events."""

    def append(self, entry: WorkflowLedgerEntry) -> None:
        """Append one workflow-ledger event."""
        ...

    def list_entries(self, manifest_id: str) -> list[WorkflowLedgerEntry]:
        """Return all entries for a manifest in append order."""
        ...

    def list_entries_by_run_id(
        self,
        workflow_run_id: RunID,
    ) -> list[WorkflowLedgerEntry]:
        """Return all entries linked to a workflow run identifier."""
        ...
