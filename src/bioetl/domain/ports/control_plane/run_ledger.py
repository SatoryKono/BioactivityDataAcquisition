"""Port for run-ledger persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID

__all__ = ["RunLedgerPort"]


@runtime_checkable
class RunLedgerPort(Protocol):
    """Persist and query append-only run-ledger events."""

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one ledger event."""
        ...

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Return all entries for a manifest in append order."""
        ...

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        """Return all entries linked to a run identifier."""
        ...
