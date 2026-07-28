# pyright: reportArgumentType=false
# Boundary object/payload typing residual at this module.
"""Private helpers for file-backed run-ledger persistence."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import (
    RUN_FAILED_EVENT,
    RUN_FINISHED_EVENT,
    RUN_SHUTDOWN_EVENT,
)
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


class RunLedgerCorruptionError(ValueError):
    """Raised when persisted JSONL ledger contents are structurally corrupted."""


class _LedgerOSModule(Protocol):
    """Narrow filesystem operations used by crash-safe ledger appends."""

    O_RDWR: int

    def open(self, path: Path, flags: int, mode: int = 0o777) -> int: ...

    def ftruncate(self, file_descriptor: int, length: int) -> None: ...

    def close(self, file_descriptor: int) -> None: ...

    def fstat(self, file_descriptor: int) -> os.stat_result: ...

    def write(self, file_descriptor: int, payload: bytes) -> int: ...


def resolve_ledger_pipeline(entry: RunLedgerEntry) -> str:
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


def emit_ledger_append_metric(
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


def emit_ledger_append_duration_metric(
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


def emit_terminal_event_metric(
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


def has_idempotent_duplicate(
    entries: list[RunLedgerEntry],
    *,
    idempotency_key: str | None,
) -> bool:
    """Return whether a logical event has already been persisted."""
    if idempotency_key is None:
        return False
    return any(entry.idempotency_key == idempotency_key for entry in entries)


def truncate_ledger_to_offset(
    path: Path,
    *,
    offset: int,
    os_module: _LedgerOSModule = os,
    flush_file_descriptor: Callable[[int], None],
) -> None:
    """Best-effort rollback to one known-good byte offset."""
    if not path.exists():
        return
    file_descriptor = os_module.open(path, os_module.O_RDWR)
    try:
        os_module.ftruncate(file_descriptor, offset)
        flush_file_descriptor(file_descriptor)
    finally:
        os_module.close(file_descriptor)


def append_jsonl_payload(
    path: Path,
    payload: bytes,
    *,
    open_flags: int,
    os_module: _LedgerOSModule = os,
    flush_file_descriptor: Callable[[int], None],
) -> int:
    """Append one full JSONL payload with rollback on partial writes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    file_descriptor = os_module.open(path, open_flags, 0o666)
    bytes_written = 0
    checkpoint_size = 0
    try:
        checkpoint_size = os_module.fstat(file_descriptor).st_size
        while bytes_written < len(payload):
            written = os_module.write(file_descriptor, payload[bytes_written:])
            if written <= 0:
                raise OSError("Ledger append produced an empty write")
            bytes_written += written
        flush_file_descriptor(file_descriptor)
        return checkpoint_size
    except OSError:
        if bytes_written > 0:
            try:
                os_module.ftruncate(file_descriptor, checkpoint_size)
                flush_file_descriptor(file_descriptor)
            except OSError:
                pass
        raise
    finally:
        os_module.close(file_descriptor)


def ensure_entries_match_manifest_and_run_identity(
    *,
    entries: list[RunLedgerEntry],
    manifest_id: str,
) -> None:
    """Fail closed when one manifest ledger contains mixed identity anchors."""
    if not entries:
        return
    if any(entry.manifest_id != manifest_id for entry in entries):
        raise RunLedgerCorruptionError(
            f"Run ledger file '{manifest_id}.jsonl' is corrupted: "
            "entries contain a different manifest_id"
        )
    run_ids = {str(entry.run_id) for entry in entries}
    if len(run_ids) > 1:
        raise RunLedgerCorruptionError(
            f"Run ledger file '{manifest_id}.jsonl' is corrupted: "
            "entries contain multiple run_id values"
        )


def ensure_entries_match_run_index(
    *,
    entries: list[RunLedgerEntry],
    manifest_id: str,
    run_id: RunID,
) -> None:
    """Fail closed when one run-id index points at mismatched ledger entries."""
    if any(entry.manifest_id != manifest_id for entry in entries):
        raise RunLedgerCorruptionError(
            "Run ledger index corruption: run-id index points to "
            f"manifest '{manifest_id}' whose ledger entries carry a different manifest_id"
        )
    if any(entry.run_id != run_id for entry in entries):
        raise RunLedgerCorruptionError(
            "Run ledger index corruption: run-id index points to "
            f"manifest '{manifest_id}' whose ledger entries belong to a different run_id"
        )


def iter_jsonl_payloads_strict(
    *,
    ledger_path: Path,
    raw_text: str,
) -> list[dict[str, object]]:
    """Parse JSONL objects and fail closed on truncated or invalid content."""
    if not raw_text.strip():
        return []
    if not raw_text.endswith(("\n", "\r")):
        raise RunLedgerCorruptionError(
            f"Run ledger file '{ledger_path}' is corrupted: truncated tail line"
        )

    payloads: list[dict[str, object]] = []
    for line_number, line in enumerate(raw_text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise RunLedgerCorruptionError(
                f"Run ledger file '{ledger_path}' is corrupted at line "
                f"{line_number}: {error.msg}"
            ) from error
        if not isinstance(payload, dict):
            raise RunLedgerCorruptionError(
                f"Run ledger file '{ledger_path}' is corrupted at line "
                f"{line_number}: payload must be a JSON object"
            )
        payloads.append({str(key): value for key, value in payload.items()})
    return payloads
