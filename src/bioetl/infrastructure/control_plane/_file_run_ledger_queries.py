# Host attrs/methods provided by concrete composition.
"""Read-side mixin for file-backed run-ledger persistence."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path
from time import perf_counter
from typing import Any, cast

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import slice_ledger_entries_after
from bioetl.domain.ports import MetricsPort
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane._file_run_ledger_helpers import (
    LEDGER_APPEND_LOCK,
    RunLedgerCorruptionError,
    ensure_entries_match_manifest_and_run_identity,
    ensure_entries_match_run_index,
    iter_jsonl_payloads_strict,
)
from bioetl.infrastructure.control_plane._read_metrics import (
    emit_control_plane_read_metrics,
)
from bioetl.infrastructure.errors import build_storage_error
from bioetl.infrastructure.storage.atomic import AtomicWriteError, atomic_write_text

_SUCCESSOR_PUBLISH_ERRORS = (AtomicWriteError, OSError, TypeError, ValueError)

_RUN_LEDGER_MESSAGE_PREFIX = "Run ledger"


def _ensure_entries_match_run_chain(
    *,
    entries: list[RunLedgerEntry],
    manifest_ids: set[str],
    run_id: RunID,
) -> None:
    """Fail closed when a successor chain contains a foreign identity."""
    if any(entry.manifest_id not in manifest_ids for entry in entries):
        raise RunLedgerCorruptionError(
            "Run ledger index corruption: run-id index chain contains "
            "an entry whose manifest_id is outside the successor chain"
        )
    if any(entry.run_id != run_id for entry in entries):
        raise RunLedgerCorruptionError(
            "Run ledger index corruption: run-id index points to "
            "ledger entries that belong to a different run_id"
        )


def _rollback_successor_ledger_publish(
    *,
    pointer_path: Path,
    pointer_created: bool,
    run_index_path: Path,
    previous_index: str | None,
    predecessor_ledger: Path,
    created_predecessor_ledger: bool,
) -> None:
    """Undo a successor publish that did not finish both index writes."""
    if pointer_created:
        pointer_path.unlink(missing_ok=True)
    if previous_index is None:
        run_index_path.unlink(missing_ok=True)
    else:
        atomic_write_text(run_index_path, previous_index)
    if created_predecessor_ledger:
        predecessor_ledger.unlink(missing_ok=True)


def _next_predecessor_id(base_path: Path, manifest_id: str) -> str | None:
    """Return the predecessor id named by one pointer file.

    A missing pointer file is a terminal manifest. An empty pointer, or a
    pointer whose predecessor ledger file is gone, is persisted corruption.
    """
    pointer = base_path / "_predecessors" / f"{manifest_id}.txt"
    if not pointer.is_file():
        return None
    predecessor_id = pointer.read_text(encoding="utf-8").strip()
    if not predecessor_id:
        raise RunLedgerCorruptionError(
            f"successor pointer for manifest {manifest_id!r} is empty"
        )
    ledger_path = base_path / f"{predecessor_id}.jsonl"
    if not ledger_path.is_file():
        raise RunLedgerCorruptionError(
            f"predecessor ledger file is missing for manifest {predecessor_id!r}"
        )
    return predecessor_id


class FileRunLedgerQueriesMixin:
    """Query and load helpers for ``FileRunLedgerStore``."""

    base_path: Path = cast(Any, None)  # Any: host attr default (PD3)
    metrics: MetricsPort | None = cast(Any, None)  # Any: host attr default (PD3)

    def record_manifest_successor(
        self,
        *,
        run_id: RunID,
        predecessor_manifest_id: str,
        successor_manifest_id: str,
    ) -> None:
        """Move the run index onto a successor and keep the predecessor link.

        Later appends use the successor id. ``list_entries_by_run_id`` walks
        the pointer files so earlier events stay visible for the same run.
        """
        with LEDGER_APPEND_LOCK:
            self._record_manifest_successor_locked(
                run_id=run_id,
                predecessor_manifest_id=predecessor_manifest_id,
                successor_manifest_id=successor_manifest_id,
            )

    def _record_manifest_successor_locked(
        self,
        *,
        run_id: RunID,
        predecessor_manifest_id: str,
        successor_manifest_id: str,
    ) -> None:
        """Publish one successor pointer while holding the writer lock."""
        predecessor = predecessor_manifest_id.strip()
        successor = successor_manifest_id.strip()
        if not predecessor or not successor or predecessor == successor:
            raise ValueError(
                "successor ledger rebind requires two distinct manifest ids"
            )
        self.base_path.mkdir(parents=True, exist_ok=True)
        indexed = self._load_manifest_id_for_run_id(run_id)
        if indexed not in {None, predecessor, successor}:
            raise RunLedgerCorruptionError(
                f"run_id is already mapped to a different manifest_id: {indexed}"
            )
        pointer_dir = self.base_path / "_predecessors"
        pointer_dir.mkdir(parents=True, exist_ok=True)
        pointer_path = pointer_dir / f"{successor}.txt"
        pointer_existed = pointer_path.is_file()
        if pointer_existed:
            existing = pointer_path.read_text(encoding="utf-8").strip()
            if existing != predecessor:
                raise RunLedgerCorruptionError(
                    "successor ledger pointer already names a different "
                    f"predecessor: {existing}"
                )
        run_index_dir = self.base_path / "_by_run_id"
        run_index_dir.mkdir(parents=True, exist_ok=True)
        run_index_path = run_index_dir / f"{run_id}.txt"
        previous_index = (
            run_index_path.read_text(encoding="utf-8")
            if run_index_path.is_file()
            else None
        )
        predecessor_ledger = self.base_path / f"{predecessor}.jsonl"
        created_predecessor_ledger = False
        try:
            if not predecessor_ledger.is_file():
                atomic_write_text(predecessor_ledger, "")
                created_predecessor_ledger = True
            atomic_write_text(pointer_path, predecessor)
            atomic_write_text(run_index_path, successor)
        except _SUCCESSOR_PUBLISH_ERRORS:
            with suppress(*_SUCCESSOR_PUBLISH_ERRORS):
                _rollback_successor_ledger_publish(
                    pointer_path=pointer_path,
                    pointer_created=not pointer_existed,
                    run_index_path=run_index_path,
                    previous_index=previous_index,
                    predecessor_ledger=predecessor_ledger,
                    created_predecessor_ledger=created_predecessor_ledger,
                )
            raise

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
            chain = self._predecessor_chain(manifest_id)
            entries: list[RunLedgerEntry] = []
            for item_id in reversed(chain):
                entries.extend(self._load_entries(item_id))
            if not entries:
                status = "miss"
                return []
            if len(chain) == 1:
                ensure_entries_match_run_index(
                    entries=entries,
                    manifest_id=manifest_id,
                    run_id=run_id,
                )
            else:
                _ensure_entries_match_run_chain(
                    entries=entries,
                    manifest_ids=set(chain),
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
        """Return append-ordered entries strictly after one checkpoint watermark.

        The suffix spans the predecessor chain and any published successors, so
        a checkpoint that still names the predecessor does not drop events
        written to the successor ledger file.
        """
        started_at = perf_counter()
        status = "success"
        try:
            entries = self._ledger_chain_entries(manifest_id)
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

    def _direct_successor_id(self, manifest_id: str) -> str | None:
        """Return the single successor that names this manifest, if any."""
        pointer_dir = self.base_path / "_predecessors"
        if not pointer_dir.is_dir():
            return None
        matches: list[str] = []
        for pointer in sorted(pointer_dir.glob("*.txt")):
            named = pointer.read_text(encoding="utf-8").strip()
            if named == manifest_id:
                matches.append(pointer.name.removesuffix(".txt"))
        if len(matches) > 1:
            raise RunLedgerCorruptionError(
                f"manifest {manifest_id!r} has multiple successor pointers"
            )
        return matches[0] if matches else None

    def _ledger_chain_entries(self, manifest_id: str) -> list[RunLedgerEntry]:
        """Load oldest-first entries for one manifest, its past, and successors."""
        oldest_first = list(reversed(self._predecessor_chain(manifest_id)))
        seen = set(oldest_first)
        cursor = manifest_id
        while True:
            successor = self._direct_successor_id(cursor)
            if successor is None:
                break
            if successor in seen:
                raise RunLedgerCorruptionError(
                    f"successor pointer cycle includes manifest {successor!r}"
                )
            seen.add(successor)
            oldest_first.append(successor)
            cursor = successor
        entries: list[RunLedgerEntry] = []
        for item_id in oldest_first:
            entries.extend(self._load_entries(item_id))
        return entries

    def _predecessor_chain(self, manifest_id: str) -> tuple[str, ...]:
        """Return newest-first manifest ids linked by successor pointer files."""
        chain: list[str] = []
        seen: set[str] = set()
        cursor: str | None = manifest_id
        while cursor is not None:
            if cursor in seen:
                raise RunLedgerCorruptionError(
                    f"successor pointer cycle includes manifest {cursor!r}"
                )
            seen.add(cursor)
            chain.append(cursor)
            cursor = _next_predecessor_id(self.base_path, cursor)
        return tuple(chain)

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
