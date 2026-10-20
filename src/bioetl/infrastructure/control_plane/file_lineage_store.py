"""File-backed lineage fragment persistence."""

from __future__ import annotations

import errno
import json
import os
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, override

from bioetl.domain.lineage import LineageGraphFragment
from bioetl.domain.ports import LineageStorePort
from bioetl.infrastructure.control_plane._durability import (
    flush_control_plane_file_descriptor,
)
from bioetl.infrastructure.control_plane._file_lineage_index import (
    LineageIndexCorruptionError,
    append_jsonl_payload,
    build_stored_fragment_id,
    load_fragment_ids,
    stable_key_filename,
    truncate_index_to_offset,
)
from bioetl.infrastructure.control_plane._file_lineage_queries import (
    FileLineageQueriesMixin,
)
from bioetl.infrastructure.storage.atomic import AtomicWriteError, atomic_write_text

if sys.platform != "win32":
    import fcntl

__all__ = ["FileLineageStore"]

if TYPE_CHECKING:
    from bioetl.domain.ports import MetricsPort


_LINEAGE_APPEND_OPEN_FLAGS = os.O_APPEND | os.O_CREAT | os.O_WRONLY
_LineageIndexCorruptionError = LineageIndexCorruptionError
_SAVE_FAILURES = (AtomicWriteError, OSError, TypeError, ValueError)


def _save_lock_path(base_path: Path) -> Path:
    """Return the per-root lock path outside the lifecycle-managed lineage tree."""
    return base_path.parent / f".{base_path.name}.save.lock"


def _lock_byte_range(
    lock_fd: int,
    *,
    locking: Callable[[int, int, int], object],
    mode: int,
) -> None:
    """Lock one byte at the start of a lock file, initializing an empty file."""
    os.lseek(lock_fd, 0, os.SEEK_SET)
    if os.fstat(lock_fd).st_size < 1:
        os.write(lock_fd, b"\0")
        os.lseek(lock_fd, 0, os.SEEK_SET)
    locking(lock_fd, mode, 1)


def _acquire_msvcrt_lock(
    lock_fd: int,
    *,
    locking: Callable[[int, int, int], object],
    lock_mode: int,
) -> None:
    """Retry a blocking Windows byte lock only after CRT ``EDEADLOCK``.

    ``LK_LOCK`` already waits about ten seconds. ``EACCES`` and every other
    locking error propagate immediately so a permission failure cannot spin.
    """
    while True:
        try:
            _lock_byte_range(lock_fd, locking=locking, mode=lock_mode)
        except OSError as error:
            if error.errno != errno.EDEADLOCK:
                raise
            continue
        return


def _acquire_exclusive_lock(lock_fd: int) -> None:
    """Take an interprocess exclusive lock for one lineage root."""
    if sys.platform == "win32":
        import msvcrt

        _acquire_msvcrt_lock(
            lock_fd,
            locking=msvcrt.locking,
            lock_mode=int(msvcrt.LK_LOCK),
        )
        return
    fcntl.flock(lock_fd, fcntl.LOCK_EX)


def _release_exclusive_lock(lock_fd: int) -> None:
    """Release the lock acquired by ``_acquire_exclusive_lock``."""
    if sys.platform == "win32":
        import msvcrt

        _lock_byte_range(lock_fd, locking=msvcrt.locking, mode=int(msvcrt.LK_UNLCK))
        return
    fcntl.flock(lock_fd, fcntl.LOCK_UN)


@contextmanager
def _exclusive_base_lock(lock_path: Path) -> Iterator[None]:
    """Hold one exclusive per-root lock and always close its descriptor."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR)
    try:
        _acquire_exclusive_lock(lock_fd)
        try:
            yield
        finally:
            with suppress(OSError):
                _release_exclusive_lock(lock_fd)
    finally:
        os.close(lock_fd)


def _attach_rollback_notes(
    error: BaseException,
    rollback_errors: Sequence[BaseException],
) -> None:
    """Record incomplete restorations on the original save error."""
    for rollback_error in rollback_errors:
        error.add_note(f"Incomplete lineage rollback: {rollback_error!r}")


def _stable_key_filename(key: str) -> str:
    """Return a filesystem-safe filename stem for one semantic key."""
    return stable_key_filename(key)


def _build_stored_fragment_id(fragment: LineageGraphFragment) -> str:
    """Return one occurrence-scoped stored fragment identity."""
    return build_stored_fragment_id(fragment)


def _load_fragment_ids(index_path: Path, *, key: str) -> list[str]:
    """Load fragment identifiers from one JSONL index file."""
    return load_fragment_ids(index_path, key=key)


def _truncate_index_to_offset(path: Path, *, offset: int) -> None:
    """Best-effort rollback of one lineage index file to a known-good offset."""
    truncate_index_to_offset(
        path,
        offset=offset,
        os_module=os,
        flush_file_descriptor=flush_control_plane_file_descriptor,
    )


def _append_jsonl_payload(path: Path, payload: bytes) -> int:
    """Append one full JSONL payload with public-module patch points."""
    return append_jsonl_payload(
        path,
        payload,
        open_flags=_LINEAGE_APPEND_OPEN_FLAGS,
        os_module=os,
        flush_file_descriptor=flush_control_plane_file_descriptor,
    )


@dataclass(slots=True)
class FileLineageStore(FileLineageQueriesMixin, LineageStorePort):
    """Persist lineage graph fragments under the control-plane output tree."""

    base_path: Path
    metrics: MetricsPort | None = None

    @override
    def save(self, fragment: LineageGraphFragment) -> None:
        """Persist one fragment JSON and maintain lightweight lookup indexes."""
        fragments_dir = self.base_path / "fragments"
        fragments_dir.mkdir(parents=True, exist_ok=True)

        with _exclusive_base_lock(_save_lock_path(self.base_path)):
            stored_fragment_id = (
                fragment.stored_fragment_id or _build_stored_fragment_id(fragment)
            )
            persisted_fragment = replace(
                fragment, stored_fragment_id=stored_fragment_id
            )
            fragment_path = self._fragment_path(stored_fragment_id)
            existing_fragment_payload = (
                fragment_path.read_text(encoding="utf-8")
                if fragment_path.exists()
                else None
            )
            index_rollbacks: list[tuple[Path, int]] = []
            try:
                atomic_write_text(
                    fragment_path,
                    json.dumps(persisted_fragment.to_dict(), indent=2, sort_keys=True),
                )
                self._fragment_indexes(fragment, stored_fragment_id, index_rollbacks)
            except _SAVE_FAILURES as error:
                rollback_errors = self._rollback_save(
                    fragment_path=fragment_path,
                    existing_fragment_payload=existing_fragment_payload,
                    index_rollbacks=index_rollbacks,
                )
                if rollback_errors:
                    _attach_rollback_notes(error, rollback_errors)
                raise

    def _fragment_indexes(
        self,
        fragment: LineageGraphFragment,
        stored_fragment_id: str,
        index_rollbacks: list[tuple[Path, int]],
    ) -> None:
        """Append lookup indexes, recording each checkpoint before the next write."""
        index_rollbacks.append(
            self._append_index(
                self._semantic_fragment_index_path(fragment.fragment_id),
                key=fragment.fragment_id,
                fragment_id=stored_fragment_id,
            )
        )
        if fragment.run_id is not None:
            index_rollbacks.append(
                self._append_index(
                    self._run_index_path(fragment.run_id),
                    key=fragment.run_id,
                    fragment_id=stored_fragment_id,
                )
            )
        if fragment.manifest_id is not None:
            index_rollbacks.append(
                self._append_index(
                    self._manifest_index_path(fragment.manifest_id),
                    key=fragment.manifest_id,
                    fragment_id=stored_fragment_id,
                )
            )
        for node in fragment.nodes:
            index_rollbacks.append(
                self._append_index(
                    self._node_index_path(node.node_id),
                    key=node.node_id,
                    fragment_id=stored_fragment_id,
                )
            )

    def _rollback_save(
        self,
        *,
        fragment_path: Path,
        existing_fragment_payload: str | None,
        index_rollbacks: list[tuple[Path, int]],
    ) -> list[Exception]:
        """Restore fragment and indexes after a failed save. Returns list of rollback errors if any."""
        errors: list[Exception] = []
        for index_path, checkpoint_offset in reversed(index_rollbacks):
            try:
                _truncate_index_to_offset(index_path, offset=checkpoint_offset)
            except OSError as e:
                errors.append(e)
        if existing_fragment_payload is None:
            try:
                if fragment_path.exists():
                    fragment_path.unlink()
            except OSError as e:
                errors.append(e)
        else:
            try:
                atomic_write_text(fragment_path, existing_fragment_payload)
            except (AtomicWriteError, OSError) as error:
                errors.append(error)
        return errors

    def _fragment_path(self, fragment_id: str) -> Path:
        """Resolve the fragment JSON path for one fragment identifier."""
        return (
            self.base_path / "fragments" / f"{_stable_key_filename(fragment_id)}.json"
        )

    @override
    def _run_index_path(self, run_id: str) -> Path:
        """Resolve the run-id index path."""
        return self.base_path / "_by_run_id" / f"{_stable_key_filename(run_id)}.jsonl"

    @override
    def _semantic_fragment_index_path(self, fragment_id: str) -> Path:
        """Resolve the semantic-fragment index path."""
        return (
            self.base_path
            / "_by_fragment_id"
            / f"{_stable_key_filename(fragment_id)}.jsonl"
        )

    @override
    def _manifest_index_path(self, manifest_id: str) -> Path:
        """Resolve the manifest-id index path."""
        return (
            self.base_path
            / "_by_manifest_id"
            / f"{_stable_key_filename(manifest_id)}.jsonl"
        )

    @override
    def _node_index_path(self, node_id: str) -> Path:
        """Resolve the node-id index path."""
        return self.base_path / "_by_node_id" / f"{_stable_key_filename(node_id)}.jsonl"

    def _append_index(
        self, index_path: Path, *, key: str, fragment_id: str
    ) -> tuple[Path, int]:
        """Append one fragment identifier to a JSONL lookup index."""
        checkpoint_offset = _append_jsonl_payload(
            index_path,
            (
                json.dumps(
                    {"key": key, "fragment_id": fragment_id},
                    sort_keys=True,
                )
                + "\n"
            ).encode("utf-8"),
        )
        return index_path, checkpoint_offset

    @override
    def _load_from_index(
        self,
        index_path: Path,
        *,
        key: str,
    ) -> list[LineageGraphFragment]:
        """Load fragments referenced by one lookup index."""
        fragments: list[LineageGraphFragment] = []
        for fragment_id in self._load_fragment_ids(index_path, key=key):
            fragment = self._load_fragment(fragment_id)
            if fragment is not None:
                fragments.append(fragment)
        return fragments

    @override
    def _load_fragment_ids(self, index_path: Path, *, key: str) -> list[str]:
        return _load_fragment_ids(index_path, key=key)

    @override
    def _load_fragment(self, fragment_id: str) -> LineageGraphFragment | None:
        """Load one fragment payload without emitting public lookup metrics."""
        fragment_path = self._fragment_path(fragment_id)
        if not fragment_path.exists():
            return None
        payload = json.loads(fragment_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Lineage fragment payload must be a JSON object")
        fragment = LineageGraphFragment.from_dict(payload)
        stored_fragment_id = fragment.stored_fragment_id
        if stored_fragment_id is not None:
            return fragment if stored_fragment_id == fragment_id else None
        return fragment if fragment.fragment_id == fragment_id else None
