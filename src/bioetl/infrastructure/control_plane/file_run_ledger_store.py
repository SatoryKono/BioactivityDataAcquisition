# pyright: reportArgumentType=false

from __future__ import annotations

import json
import os
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import RunLedgerPort
from bioetl.infrastructure.control_plane._durability import (
    should_fsync_control_plane_writes,
)
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    RunLedgerCorruptionError,
    append_jsonl_payload,
    emit_ledger_append_duration_metric,
    emit_ledger_append_metric,
    emit_terminal_event_metric,
    has_idempotent_duplicate,
    resolve_ledger_pipeline,
    truncate_ledger_to_offset,
)
from bioetl.infrastructure.control_plane._file_run_ledger_queries import (
    FileRunLedgerQueriesMixin,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = ["FileRunLedgerStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LEDGER_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY
_RUN_LEDGER_MESSAGE_PREFIX = "Run ledger"
_RunLedgerCorruptionError = RunLedgerCorruptionError


def _should_fsync_control_plane_writes() -> bool:
    """Keep durable flushes unless Windows test runs explicitly relax them."""
    return should_fsync_control_plane_writes(os_name=os.name)


def _flush_file_descriptor(file_descriptor: int) -> None:
    """Flush one control-plane file descriptor when durable writes are required."""
    if not _should_fsync_control_plane_writes():
        return
    os.fsync(file_descriptor)


def _append_jsonl_payload(path: Path, payload: bytes) -> int:
    """Append one full JSONL payload with public-module patch points."""
    return append_jsonl_payload(
        path,
        payload,
        open_flags=_LEDGER_APPEND_OPEN_FLAGS,
        os_module=os,
        flush_file_descriptor=_flush_file_descriptor,
    )


def _truncate_ledger_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback to one known-good byte offset."""
    truncate_ledger_to_offset(
        path,
        offset=offset,
        os_module=os,
        flush_file_descriptor=_flush_file_descriptor,
    )


@dataclass(slots=True)
class FileRunLedgerStore(FileRunLedgerQueriesMixin, RunLedgerPort):
    """Append ledger entries to one JSONL file per manifest."""

    base_path: Path
    metrics: MetricsPort | None = None

    def append(self, entry: RunLedgerEntry) -> None:
        """Append one JSONL ledger entry and maintain run-id index."""
        started_at = perf_counter()
        ledger_path = self.base_path / f"{entry.manifest_id}.jsonl"
        run_index_dir = self.base_path / "_by_run_id"
        run_index_path = run_index_dir / f"{entry.run_id}.txt"
        pipeline = resolve_ledger_pipeline(entry)
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
                raise RunLedgerCorruptionError(
                    "run_id is already mapped to a different manifest_id: "
                    f"{existing_manifest_id}"
                )
            if has_idempotent_duplicate(
                self._load_entries(entry.manifest_id),
                idempotency_key=entry.idempotency_key,
            ):
                atomic_write_text(run_index_path, entry.manifest_id)
                self._emit_append_observation(
                    entry=entry,
                    pipeline=pipeline,
                    status="duplicate",
                    started_at=started_at,
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
            self._emit_append_observation(
                entry=entry,
                pipeline=pipeline,
                status="failed",
                started_at=started_at,
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
        self._emit_append_observation(
            entry=entry,
            pipeline=pipeline,
            status="success",
            started_at=started_at,
        )
        emit_terminal_event_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
        )

    def _emit_append_observation(
        self,
        *,
        entry: RunLedgerEntry,
        pipeline: str,
        status: str,
        started_at: float,
    ) -> None:
        emit_ledger_append_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
            status=status,
        )
        emit_ledger_append_duration_metric(
            self.metrics,
            pipeline=pipeline,
            event_type=entry.event_type,
            status=status,
            duration_seconds=perf_counter() - started_at,
        )
