"""File-backed run-ledger persistence."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
    slice_ledger_entries_after,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunLedgerStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LEDGER_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY
_RUN_LEDGER_MESSAGE_PREFIX = "Run ledger"


class _RunLedgerCorruptionError(ValueError):
    """Raised when persisted JSONL ledger contents are structurally corrupted."""


def _is_truthy_env(value: str | None) -> bool:
    """Return whether one environment variable value enables a feature."""
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _should_fsync_control_plane_writes() -> bool:
    """Keep durable flushes unless Windows E2E explicitly relaxes them."""
    if os.name != "nt":
        return True
    if not _is_truthy_env(os.environ.get("BIOETL_TEST_MODE")):
        return True
    required_profile = os.environ.get(
        "BIOETL_PIPELINE__CONTROL_PLANE__REQUIRED_PERSISTENCE_PROFILE"
    )
    return (required_profile or "").strip().lower() != "degraded_observable"


def _flush_file_descriptor(file_descriptor: int) -> None:
    """Flush one control-plane file descriptor when durable writes are required."""
    if not _should_fsync_control_plane_writes():
        return
    os.fsync(file_descriptor)


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
        "bioetl_control_plane_ledger_appends_total",
        1,
        {
            "pipeline": pipeline,
            "event_type": event_type,
            "status": status,
        },
    )


def _emit_ledger_append_duration_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    event_type: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Emit one run-ledger append duration metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.observe_histogram(
        "bioetl_control_plane_ledger_append_duration_seconds",
        duration_seconds,
        {
            "pipeline": pipeline,
            "event_type": event_type,
            "status": status,
        },
    )


def _emit_terminal_event_metric(
    metrics: MetricsPort | None,
    *,
    pipeline: str,
    event_type: str,
) -> None:
    """Mirror persisted terminal outcomes into one crash-safe aggregate family."""
    if metrics is None:
        return
    if event_type == RUN_FINISHED_EVENT:
        terminal_status = "success"
    elif event_type == RUN_FAILED_EVENT:
        terminal_status = "failed"
    elif event_type == RUN_SHUTDOWN_EVENT:
        terminal_status = "shutdown"
    else:
        return
    metrics.increment_counter(
        "bioetl_control_plane_terminal_events_total",
        1,
        {
            "pipeline": pipeline,
            "terminal_status": terminal_status,
        },
    )


def _has_idempotent_duplicate(
    entries: list[RunLedgerEntry],
    *,
    idempotency_key: str | None,
) -> bool:
    """Return whether a logical event has already been persisted."""
    if idempotency_key is None:
        return False
    return any(entry.idempotency_key == idempotency_key for entry in entries)


def _truncate_ledger_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback to one known-good byte offset."""
    if not path.exists():
        return
    file_descriptor = os.open(path, os.O_RDWR)
    try:
        os.ftruncate(file_descriptor, offset)
        _flush_file_descriptor(file_descriptor)
    finally:
        os.close(file_descriptor)


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
        _flush_file_descriptor(file_descriptor)
        return checkpoint_size
    except OSError:
        if bytes_written > 0:
            try:
                os.ftruncate(file_descriptor, checkpoint_size)
                _flush_file_descriptor(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os.close(file_descriptor)


def _ensure_entries_match_manifest_and_run_identity(
    *,
    entries: list[RunLedgerEntry],
    manifest_id: str,
) -> None:
    """Fail closed when one manifest ledger contains mixed identity anchors."""
    if not entries:
        return
    if any(entry.manifest_id != manifest_id for entry in entries):
        raise _RunLedgerCorruptionError(
            f"Run ledger file '{manifest_id}.jsonl' is corrupted: "
            "entries contain a different manifest_id"
        )
    run_ids = {str(entry.run_id) for entry in entries}
    if len(run_ids) > 1:
        raise _RunLedgerCorruptionError(
            f"Run ledger file '{manifest_id}.jsonl' is corrupted: "
            "entries contain multiple run_id values"
        )


def _iter_jsonl_payloads_strict(
    *,
    ledger_path: Path,
    raw_text: str,
) -> list[dict[str, object]]:
    """Parse JSONL objects and fail closed on truncated or invalid content."""
    if not raw_text.strip():
        return []
    if not raw_text.endswith(("\n", "\r")):
        raise _RunLedgerCorruptionError(
            f"Run ledger file '{ledger_path}' is corrupted: truncated tail line"
        )

    payloads: list[dict[str, object]] = []
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise _RunLedgerCorruptionError(
                f"Run ledger file '{ledger_path}' is corrupted at line "
                f"{line_number}: {error.msg}"
            ) from error
        if not isinstance(payload, dict):
            raise _RunLedgerCorruptionError(
                f"Run ledger file '{ledger_path}' is corrupted at line "
                f"{line_number}: payload must be a JSON object"
            )
        payloads.append({str(key): value for key, value in payload.items()})
    return payloads


@dataclass(slots=True)
class FileRunLedgerStore(RunLedgerPort):
    """Append ledger entries to one JSONL file per manifest."""

    base_path: Path
    metrics: MetricsPort | None = None

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one JSONL ledger entry and maintain run-id index."""
        started_at = perf_counter()
        ledger_path = self.base_path / f"{entry.manifest_id}.jsonl"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{entry.run_id}.txt"
        pipeline = _resolve_ledger_pipeline(entry)
        payload = (json.dumps(entry.to_dict(), sort_keys=True) + "\n").encode("utf-8")
        append_checkpoint_size: int | None = None
        try:
            self.base_path.mkdir(parents=True, exist_ok=True)
            run_index_dir.mkdir(parents=True, exist_ok=True)
            existing_manifest_id = self._load_manifest_id_for_run_id(entry.run_id)
            if (
                existing_manifest_id is not None
                and existing_manifest_id != entry.manifest_id
            ):
                raise _RunLedgerCorruptionError(
                    "run_id is already mapped to a different manifest_id: "
                    f"{existing_manifest_id}"
                )
            if _has_idempotent_duplicate(
                self._load_entries(entry.manifest_id),
                idempotency_key=entry.idempotency_key,
            ):
                atomic_write_text(run_index_path, entry.manifest_id)
                _emit_ledger_append_metric(
                    self.metrics,
                    pipeline=pipeline,
                    event_type=entry.event_type,
                    status="duplicate",
                )
                _emit_ledger_append_duration_metric(
                    self.metrics,
                    pipeline=pipeline,
                    event_type=entry.event_type,
                    status="duplicate",
                    duration_seconds=perf_counter() - started_at,
                )
                return
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
            _emit_ledger_append_duration_metric(
                self.metrics,
                pipeline=pipeline,
                event_type=entry.event_type,
                status="failed",
                duration_seconds=perf_counter() - started_at,
            )
            raise build_storage_error(
                message_prefix=_RUN_LEDGER_MESSAGE_PREFIX,
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
        _emit_ledger_append_duration_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
            status="success",
            duration_seconds=perf_counter() - started_at,
        )
        _emit_terminal_event_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
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
        except (OSError, TypeError, ValueError) as error:
            status = "failed"
            raise build_storage_error(
                message_prefix=_RUN_LEDGER_MESSAGE_PREFIX,
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
                return []
            if any(entry.manifest_id != manifest_id for entry in entries):
                raise _RunLedgerCorruptionError(
                    "Run ledger index corruption: run-id index points to "
                    f"manifest '{manifest_id}' whose ledger entries carry a different manifest_id"
                )
            if any(entry.run_id != run_id for entry in entries):
                raise _RunLedgerCorruptionError(
                    "Run ledger index corruption: run-id index points to "
                    f"manifest '{manifest_id}' whose ledger entries belong to a different run_id"
                )
            return entries
        except (OSError, TypeError, ValueError) as error:
            status = "failed"
            raise build_storage_error(
                message_prefix=_RUN_LEDGER_MESSAGE_PREFIX,
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
        except _RunLedgerCorruptionError as error:
            status = "failed"
            raise build_storage_error(
                message_prefix=_RUN_LEDGER_MESSAGE_PREFIX,
                operation="list_entries_after",
                path=self.base_path / f"{manifest_id}.jsonl",
                error=error,
                manifest_id=manifest_id,
                after_entry_id=after_entry_id,
            ) from error
        except ValueError:
            status = "failed"
            raise
        except (OSError, TypeError) as error:
            status = "failed"
            raise build_storage_error(
                message_prefix=_RUN_LEDGER_MESSAGE_PREFIX,
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
        entries = [
            RunLedgerEntry.from_dict(payload)
            for payload in _iter_jsonl_payloads_strict(
                ledger_path=ledger_path,
                raw_text=raw_text,
            )
        ]
        _ensure_entries_match_manifest_and_run_identity(
            entries=entries,
            manifest_id=manifest_id,
        )
        return entries

    def _load_manifest_id_for_run_id(self, run_id: RunID) -> str | None:
        """Return the indexed manifest identifier for one run when present."""
        run_index_path = self.base_path / "_by_run_id" / f"{run_id}.txt"
        if not run_index_path.exists():
            return None
        manifest_id = run_index_path.read_text(encoding="utf-8").strip()
        return manifest_id or None
