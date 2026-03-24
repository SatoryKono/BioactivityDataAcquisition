"""File-backed run-ledger persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID

__all__ = ["FileRunLedgerStore"]


@dataclass(slots=True)
class FileRunLedgerStore(RunLedgerPort):
    """Append ledger entries to one JSONL file per manifest."""

    base_path: Path

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one JSONL ledger entry and maintain run-id index."""
        ledger_path = self.base_path / f"{entry.manifest_id}.jsonl"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{entry.run_id}.txt"

        self.base_path.mkdir(parents=True, exist_ok=True)
        run_index_dir.mkdir(parents=True, exist_ok=True)
        with ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.to_dict(), sort_keys=True))
            handle.write("\n")
        run_index_path.write_text(entry.manifest_id, encoding="utf-8")

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Return all entries for one manifest in append order."""
        ledger_path = self.base_path / f"{manifest_id}.jsonl"
        if not ledger_path.exists():
            return []
        return [
            RunLedgerEntry.from_dict(payload)
            for payload in (
                json.loads(line)
                for line in ledger_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
            if isinstance(payload, dict)
        ]

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        """Resolve run-id index to manifest ledger file."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        if not run_index_path.exists():
            return []
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        if not manifest_id:
            return []
        return self.list_entries(manifest_id)
