"""File-backed run-ledger persistence."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID

__all__ = ["FileRunLedgerStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


def _resolve_ledger_pipeline(entry: RunLedgerEntry) -> str:
    """Resolve the canonical pipeline label from diagnostic entry details."""
    if entry.details is None:
        return "unknown"
    diagnostic = entry.details.get("_diagnostic")
    if not isinstance(diagnostic, dict):
        return "unknown"
    pipeline = diagnostic.get("pipeline")
    if pipeline is None:
        return "unknown"
    text = str(pipeline).strip()
    return text or "unknown"


def _emit_ledger_append_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    event_type: str,
    status: str,
) -> None:
    """Emit one run-ledger append metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "control_plane_ledger_appends_total",
        1,
        {
            "pipeline": pipeline,
            "event_type": event_type,
            "status": status,
        },
    )


@dataclass(slots=True)
class FileRunLedgerStore(RunLedgerPort):
    """Append ledger entries to one JSONL file per manifest."""

    base_path: Path
    metrics: MetricsPort | None = None

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one JSONL ledger entry and maintain run-id index."""
        ledger_path = self.base_path / f"{entry.manifest_id}.jsonl"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{entry.run_id}.txt"
        pipeline = _resolve_ledger_pipeline(entry)
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry.to_dict(), sort_keys=True))
                handle.write("\n")
            run_index_path.write_text(entry.manifest_id, encoding="utf-8")
        except (OSError, TypeError, ValueError):
            _emit_ledger_append_metric(
                self.metrics,
                pipeline=pipeline,
                event_type=entry.event_type,
                status="failed",
            )
            raise
        _emit_ledger_append_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
            status="success",
        )

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
