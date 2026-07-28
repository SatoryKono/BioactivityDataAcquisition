# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods provided by concrete composition.
"""Read-side mixin for file-backed run-ledger persistence."""

from __future__ import annotations

from pathlib import Path
from time import perf_counter

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import slice_ledger_entries_after
from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    RunLedgerCorruptionError,
    ensure_entries_match_manifest_and_run_identity,
    ensure_entries_match_run_index,
    iter_jsonl_payloads_strict,
)
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error

_RUN_LEDGER_MESSAGE_PREFIX = "Run ledger"


class FileRunLedgerQueriesMixin:
    """Query and load helpers for ``FileRunLedgerStore``."""

    base_path: Path
    metrics: MetricsPort | None

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
            self._emit_read_observation(
                operation="list_entries",
                status=status,
                started_at=started_at,
            )

    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]:
        """Resolve run-id index to manifest ledger file."""
        started_at = perf_counter()
        status = "success"
        try:
            manifest_id = self._load_manifest_id_for_run_id(run_id)
            if manifest_id is None:
                status = "miss"
                return []
            entries = self._load_entries(manifest_id)
            if not entries:
                status = "miss"
                return []
            ensure_entries_match_run_index(
                entries=entries,
                manifest_id=manifest_id,
                run_id=run_id,
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
            self._emit_read_observation(
                operation="list_entries_by_run_id",
                status=status,
                started_at=started_at,
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
        except RunLedgerCorruptionError as error:
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
            self._emit_read_observation(
                operation="list_entries_after",
                status=status,
                started_at=started_at,
            )

    def _load_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Load ledger entries for one manifest without emitting public metrics."""
        ledger_path = self.base_path / f"{manifest_id}.jsonl"
        if not ledger_path.exists():
            return []
        raw_text = ledger_path.read_text(encoding="utf-8")
        entries = [
            RunLedgerEntry.from_dict(payload)
            for payload in iter_jsonl_payloads_strict(
                ledger_path=ledger_path,
                raw_text=raw_text,
            )
        ]
        ensure_entries_match_manifest_and_run_identity(
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

    def _emit_read_observation(
        self,
        *,
        operation: str,
        status: str,
        started_at: float,
    ) -> None:
        emit_control_plane_read_metrics(
            self.metrics,
            store="ledger",
            operation=operation,
            status=status,
            duration_seconds=perf_counter() - started_at,
        )
