"""File-backed run-ledger persistence."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING, cast

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import slice_ledger_entries_after
from bioetl.domain.exceptions import StorageError
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunLedgerStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LEDGER_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY


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


def _build_storage_error(
    *,
    operation: str,
    path: Path,
    error: Exception,
    **context: object,
) -> StorageError:
    """Normalize ledger persistence failures under the shared storage taxonomy."""
    wrapped = StorageError(f"Run ledger {operation} failed for '{path}': {error}")
    return cast(
        "StorageError",
        wrapped.with_context(
            operation=operation,
            path=str(path),
            original_error=str(error),
            **context,
        ),
    )


def _truncate_ledger_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback to one known-good byte offset."""
    if not path.exists():
        return
    with path.open("r+b") as handle:
        handle.truncate(offset)
        handle.flush()
        os.fsync(handle.fileno())


def _append_jsonl_payload(path: Path, payload: bytes) -> int:
    """Append one full JSONL payload with rollback on partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os.open(path, _LEDGER_APPEND_OPEN_FLAGS, 0o666)
    bytes_written = 0
    checkpoint_size = 0
    try:
        checkpoint_size = os.fstat(file_descriptor).st_size
        while bytes_written < len(payload):
            written = os.write(file_descriptor, payload[bytes_written:])
            if written <= 0:
                raise OSError("Ledger append produced an empty write")
            bytes_written += written
        os.fsync(file_descriptor)
        return checkpoint_size
    except OSError:
        if bytes_written > 0:
            try:
                os.ftruncate(file_descriptor, checkpoint_size)
                os.fsync(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os.close(file_descriptor)


def _iter_complete_jsonl_payloads(raw_text: str) -> list[dict[str, object]]:
    """Parse complete JSONL objects while tolerating one truncated tail line."""
    stripped_lines = [line for line in raw_text.splitlines() if line.strip()]
    if not stripped_lines:
        return []

    complete_lines = stripped_lines
    if raw_text and not raw_text.endswith(("\n", "\r")):
        complete_lines = stripped_lines[:-1]

    payloads: list[dict[str, object]] = []
    for line in complete_lines:
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise ValueError("Ledger payload must be a JSON object")
        payloads.append({str(key): value for key, value in payload.items()})
    return payloads


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
        payload = (json.dumps(entry.to_dict(), sort_keys=True) + "\n").encode("utf-8")
        append_checkpoint_size: int | None = None
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            append_checkpoint_size = _append_jsonl_payload(ledger_path, payload)
            atomic_write_text(run_index_path, entry.manifest_id)
        except (OSError, TypeError, ValueError) as error:
            if append_checkpoint_size is not None:
                with suppress(OSError):
                    _truncate_ledger_to_offset(
                        ledger_path,
                        offset=append_checkpoint_size,
                    )
            _emit_ledger_append_metric(
                self.metrics,
                pipeline=pipeline,
                event_type=entry.event_type,
                status="failed",
            )
            raise _build_storage_error(
                operation="append",
                path=ledger_path,
                error=error,
                manifest_id=entry.manifest_id,
                run_id=str(entry.run_id),
                event_type=entry.event_type,
            ) from error
        _emit_ledger_append_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
            status="success",
        )

    def list_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Return all entries for one manifest in append order."""
        started_at = perf_counter()
        status = "success"
        try:
            entries = self._load_entries(manifest_id)
            if not entries:
                status = "miss"
            return entries
        except StorageError:
            status = "failed"
            raise
        except (OSError, TypeError, ValueError) as error:
            status = "failed"
            raise _build_storage_error(
                operation="list_entries",
                path=self.base_path / f"{manifest_id}.jsonl",
                error=error,
                manifest_id=manifest_id,
            ) from error
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="ledger",
                operation="list_entries",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        """Resolve run-id index to manifest ledger file."""
        started_at = perf_counter()
        status = "success"
        try:
            run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
            if not run_index_path.exists():
                status = "miss"
                return []
            manifest_id = run_index_path.read_text(encoding="utf-8").strip()
            if not manifest_id:
                status = "miss"
                return []
            entries = self._load_entries(manifest_id)
            if not entries:
                status = "miss"
            return entries
        except StorageError:
            status = "failed"
            raise
        except (OSError, TypeError, ValueError) as error:
            status = "failed"
            raise _build_storage_error(
                operation="list_entries_by_run_id",
                path=self.base_path / "_by_run_id" / f"{run_id}.txt",
                error=error,
                run_id=str(run_id),
            ) from error
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="ledger",
                operation="list_entries_by_run_id",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def list_entries_after(
        self,
        manifest_id: str,
        after_entry_id: str | None,
    ) -> list[RunLedgerEntry]:
        """Return append-ordered entries strictly after one checkpoint watermark."""
        started_at = perf_counter()
        status = "success"
        try:
            entries = self._load_entries(manifest_id)
            if not entries:
                status = "miss"
                return []
            return list(slice_ledger_entries_after(entries, after_entry_id))
        except StorageError:
            status = "failed"
            raise
        except ValueError:
            status = "failed"
            raise
        except (OSError, TypeError) as error:
            status = "failed"
            raise _build_storage_error(
                operation="list_entries_after",
                path=self.base_path / f"{manifest_id}.jsonl",
                error=error,
                manifest_id=manifest_id,
                after_entry_id=after_entry_id,
            ) from error
        finally:
            emit_control_plane_read_metrics(
                self.metrics,
                store="ledger",
                operation="list_entries_after",
                status=status,
                duration_seconds=perf_counter() - started_at,
            )

    def _load_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Load ledger entries for one manifest without emitting public metrics."""
        ledger_path = self.base_path / f"{manifest_id}.jsonl"
        if not ledger_path.exists():
            return []
        raw_text = ledger_path.read_text(encoding="utf-8")
        return [
            RunLedgerEntry.from_dict(payload)
            for payload in _iter_complete_jsonl_payloads(raw_text)
        ]
