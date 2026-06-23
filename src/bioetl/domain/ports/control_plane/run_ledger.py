"""Port for run-ledger persistence."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from bioetl.domain.control_plane.run_ledger import RunLedgerEntry
from bioetl.domain.types import RunID

__all__ = ["RunLedgerPort"]


@runtime_checkable
class RunLedgerPort(Protocol):
    """Persist and query append-only run-ledger events."""

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one ledger event.

        Implementations should treat non-empty ``idempotency_key`` values as
        stable logical-event identity and avoid persisting duplicates for the
        same manifest.
        """
        ...

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Return all entries for a manifest in append order."""
        ...

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        """Return all entries linked to a run identifier."""
        ...

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        """Return replay-ready entries strictly after one append watermark.

        Implementations must preserve append order so resume replay remains
        deterministic. When ``after_entry_id`` is not ``None`` and the
        watermark cannot be found, implementations should raise ``ValueError``.
        """
        ...
