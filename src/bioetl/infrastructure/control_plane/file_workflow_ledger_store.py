"""File-backed workflow-ledger persistence."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from bioetl.domain.control_plane import WorkflowLedgerEntry
from bioetl.domain.ports import WorkflowLedgerPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._durability import (
    flush_control_plane_file_descriptor,
)
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileWorkflowLedgerStore"]

_LEDGER_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY


def _append_jsonl_payload(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os.open(path, _LEDGER_APPEND_OPEN_FLAGS, 0o666)
    bytes_written = 0
    checkpoint_size = 0
    try:
        checkpoint_size = os.fstat(file_descriptor).st_size
        while bytes_written < len(payload):
            written = os.write(file_descriptor, payload[bytes_written:])
            if written <= 0:
                raise OSError("Workflow ledger append produced an empty write")
            bytes_written += written
        flush_control_plane_file_descriptor(file_descriptor)
    except OSError:
        if bytes_written > 0:
            try:
                os.ftruncate(file_descriptor, checkpoint_size)
                flush_control_plane_file_descriptor(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os.close(file_descriptor)


@dataclass(slots=True)
class FileWorkflowLedgerStore(WorkflowLedgerPort):
    """Append workflow-ledger entries to one JSONL file per manifest."""

    base_path: Path
    metrics: object | None = None

    def append(self, entry: WorkflowLedgerEntry) -> None:
        """Append one workflow-ledger entry and maintain the run-id index."""
        ledger_path = self.base_path / f"{entry.manifest_id}.jsonl"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{entry.workflow_run_id}.txt"
        payload = (json.dumps(entry.to_dict(), sort_keys=True) + "\n").encode("utf-8")
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            existing_manifest_id = self._load_manifest_id_for_run_id(
                entry.workflow_run_id
            )
            if (
                existing_manifest_id is not None
                and existing_manifest_id != entry.manifest_id
            ):
                raise ValueError(
                    "workflow_run_id is already mapped to a different manifest_id: "
                    f"{existing_manifest_id}"
                )
            _append_jsonl_payload(ledger_path, payload)
            if not run_index_path.exists():
                atomic_write_text(run_index_path, entry.manifest_id)
        except (OSError, TypeError, ValueError) as error:
            raise build_storage_error(
                message_prefix="Workflow ledger",
                operation="append",
                path=ledger_path,
                error=error,
                manifest_id=entry.manifest_id,
                run_id=str(entry.workflow_run_id),
            ) from error

    def list_entries(self, manifest_id: str) -> list[WorkflowLedgerEntry]:
        """Load all ledger entries for one manifest."""
        started_at = perf_counter()
        status = "success"
        try:
            entries = self._load_entries(manifest_id)
            if not entries:
                status = "miss"
            return entries
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_ledger",
                operation="list_entries",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_entries_by_run_id(
        self, workflow_run_id: RunID
    ) -> list[WorkflowLedgerEntry]:
        """Load all workflow-ledger entries linked to a workflow run identifier."""
        started_at = perf_counter()
        status = "success"
        try:
            manifest_id = self._load_manifest_id_for_run_id(workflow_run_id)
            if not manifest_id:
                status = "miss"
                return []
            return self._load_entries(manifest_id)
        except (OSError, TypeError, ValueError):
            status = "failed"
            raise
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="workflow_ledger",
                operation="list_entries_by_run_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _load_entries(self, manifest_id: str) -> list[WorkflowLedgerEntry]:
        ledger_path = self.base_path / f"{manifest_id}.jsonl"
        if not ledger_path.exists():
            return []
        raw_text = ledger_path.read_text(encoding="utf-8")
        entries: list[WorkflowLedgerEntry] = []
        for line in raw_text.splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if not isinstance(payload, dict):
                raise ValueError("Workflow ledger payload must be a JSON object")
            entries.append(WorkflowLedgerEntry.from_dict(payload))
        return entries

    def _load_manifest_id_for_run_id(self, workflow_run_id: RunID) -> str | None:
        run_index_path = self.base_path / "_by_run_id" / f"{workflow_run_id}.txt"
        if not run_index_path.exists():
            return None
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        return manifest_id or None
