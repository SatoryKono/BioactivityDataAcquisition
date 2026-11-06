"""Publish run manifests and finalized evidence to the live catalog."""

from __future__ import annotations

import errno
import json
import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

if sys.platform != "win32":
    import fcntl

from bioetl.domain.control_plane import RunManifest
from bioetl.domain.exceptions import StorageError
from bioetl.infrastructure.control_plane._file_run_manifest_persistence import (
    persist_manifest,
)
from bioetl.infrastructure.control_plane.file_run_manifest_store import (
    FileRunManifestStore,
)
from bioetl.infrastructure.storage.atomic import atomic_write_text

__all__ = [
    "LiveRootRecordResult",
    "copy_contract_evidence_to_live_catalog",
    "record_manifest_in_live_catalog",
    "snapshot_manifest_catalog",
]

_ALREADY_MAPPED = "run_id is already mapped to a different manifest_id"


def _is_already_mapped_error(exc: BaseException) -> bool:
    """True when a persist failure is the run-index conflict.

    The store wraps the conflict ``ValueError`` into ``StorageError``
    (``raise ... from error``), so the marker text appears both in the
    wrapper message and in its cause.
    """
    if _ALREADY_MAPPED in str(exc):
        return True
    cause = exc.__cause__
    return isinstance(cause, ValueError) and _ALREADY_MAPPED in str(cause)


_CATALOG_LOCKS: dict[str, threading.Lock] = {}
_CATALOG_LOCKS_GUARD = threading.Lock()


@dataclass(frozen=True, slots=True)
class LiveRootRecordResult:
    """Outcome of one new-run publication into the live catalog."""

    outcome: str
    catalog_snapshot: tuple[str, ...]


def snapshot_manifest_catalog(base_path: Path) -> tuple[str, ...]:
    """Return sorted manifest ids already stored under ``base_path``."""
    if not base_path.is_dir():
        return ()
    return tuple(
        sorted(
            path.stem
            for path in base_path.glob("*.json")
            if path.is_file() and not path.name.endswith(".contract-evidence.json")
        )
    )


def record_manifest_in_live_catalog(
    *,
    manifest: RunManifest,
    live_base: Path,
    source_base: Path,
) -> LiveRootRecordResult:
    """Publish one new manifest into the live catalog.

    Historical data trees are not scanned or copied. Different bytes for an
    existing manifest id stay in place. A run-id index advances only for the
    verified successor of the indexed manifest; the previous file stays.
    Catalog ids present before the write must still be present after it.

    The whole transaction is serialized across threads and processes that
    share the live root: the catalog update inside the store is a
    read-modify-write over shared index files, so two unsynchronized
    publishers can each lose the other's scope.
    """
    live = Path(live_base)
    with _live_catalog_lock(live):
        return _record_manifest_in_live_catalog(
            manifest=manifest,
            live_base=live,
            source_base=Path(source_base),
        )


def _record_manifest_in_live_catalog(
    *,
    manifest: RunManifest,
    live_base: Path,
    source_base: Path,
) -> LiveRootRecordResult:
    live = live_base
    source = source_base
    snapshot = snapshot_manifest_catalog(live)
    if live.resolve(strict=False) == source.resolve(strict=False):
        return LiveRootRecordResult("already_live", snapshot)
    if _kept_existing_manifest(live, manifest):
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("kept_existing", snapshot)
    if _already_recorded(live, manifest):
        _copy_own_contract_evidence(
            manifest.manifest_id, live_base=live, source_base=source
        )
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("already_recorded", snapshot)
    store = FileRunManifestStore(base_path=live)
    try:
        persist_manifest(
            store,
            manifest,
            atomic_writer=atomic_write_text,
            require_local_predecessor=False,
        )
    except (StorageError, ValueError) as exc:
        if not _is_already_mapped_error(exc):
            raise
        _assert_snapshot_preserved(live, snapshot)
        return LiveRootRecordResult("kept_existing", snapshot)
    _copy_own_contract_evidence(
        manifest.manifest_id, live_base=live, source_base=source
    )
    _assert_snapshot_preserved(live, snapshot)
    return LiveRootRecordResult("recorded", snapshot)


def _rendered_manifest(manifest: RunManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True)


def _normalized_manifest_text(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip("\n")


def _kept_existing_manifest(live_base: Path, manifest: RunManifest) -> bool:
    """True when a recorded live file must not be replaced."""
    target = live_base / f"{manifest.manifest_id}.json"
    if target.is_file():
        current = target.read_text(encoding="utf-8")
        if _normalized_manifest_text(current) != _normalized_manifest_text(
            _rendered_manifest(manifest)
        ):
            return True
    index = live_base / "_by_run_id" / f"{manifest.run_id}.txt"
    if not index.is_file():
        return False
    current_id = index.read_text(encoding="utf-8").strip()
    if not current_id or current_id == manifest.manifest_id:
        return False
    return not _verified_successor_of_indexed(live_base, manifest, current_id)


def _verified_successor_of_indexed(
    live_base: Path,
    manifest: RunManifest,
    indexed_id: str,
) -> bool:
    """True when this manifest is the next link of the indexed run."""
    predecessor_id = manifest.predecessor_manifest_id
    if predecessor_id != indexed_id:
        return False
    try:
        predecessor = FileRunManifestStore(base_path=live_base).get(indexed_id)
    except (OSError, TypeError, ValueError):
        return False
    return predecessor is not None and predecessor.run_id == manifest.run_id


def _already_recorded(live_base: Path, manifest: RunManifest) -> bool:
    target = live_base / f"{manifest.manifest_id}.json"
    index = live_base / "_by_run_id" / f"{manifest.run_id}.txt"
    if not target.is_file() or not index.is_file():
        return False
    if index.read_text(encoding="utf-8").strip() != manifest.manifest_id:
        return False
    current = target.read_text(encoding="utf-8")
    return _normalized_manifest_text(current) == _normalized_manifest_text(
        _rendered_manifest(manifest)
    )


def copy_contract_evidence_to_live_catalog(
    manifest_id: str,
    *,
    source_base: Path,
    live_base: Path,
) -> None:
    """Copy one created sidecar onto a manifest already stored in the live catalog.

    The sidecar is published when it is created, not only during the earlier
    manifest write. A missing live manifest is left untouched, and an existing
    sidecar is not replaced. The sidecar is attached only when the live
    manifest is byte-identical to the source manifest: a conflicting live
    manifest kept under the same id must not inherit another run's evidence.
    """
    live = Path(live_base)
    source = Path(source_base)
    if live.resolve(strict=False) == source.resolve(strict=False):
        return
    with _live_catalog_lock(live):
        if not (live / f"{manifest_id}.json").is_file():
            return
        if not _live_manifest_matches_source(
            manifest_id, live_base=live, source_base=source
        ):
            return
        _copy_own_contract_evidence(manifest_id, live_base=live, source_base=source)


def _live_manifest_matches_source(
    manifest_id: str,
    *,
    live_base: Path,
    source_base: Path,
) -> bool:
    """True when the live manifest file equals the source manifest file."""
    live_file = live_base / f"{manifest_id}.json"
    source_file = source_base / f"{manifest_id}.json"
    if not live_file.is_file() or not source_file.is_file():
        return False
    try:
        live_text = live_file.read_text(encoding="utf-8")
        source_text = source_file.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    return _normalized_manifest_text(live_text) == _normalized_manifest_text(
        source_text
    )


def _copy_own_contract_evidence(
    manifest_id: str,
    *,
    live_base: Path,
    source_base: Path,
) -> None:
    """Copy this publication's sidecar only. Predecessor files stay put."""
    name = f"{manifest_id}.contract-evidence.json"
    source = source_base / name
    destination = live_base / name
    if destination.exists() or not source.is_file():
        return
    atomic_write_text(destination, source.read_text(encoding="utf-8"))


def _assert_snapshot_preserved(base_path: Path, snapshot: tuple[str, ...]) -> None:
    missing = [
        manifest_id
        for manifest_id in snapshot
        if not (base_path / f"{manifest_id}.json").is_file()
    ]
    if missing:
        raise RuntimeError(
            "live manifest catalog lost recorded manifests: " + ", ".join(missing)
        )


def _catalog_thread_lock(key: str) -> threading.Lock:
    """Return the in-process lock that serializes one live root."""
    with _CATALOG_LOCKS_GUARD:
        lock = _CATALOG_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _CATALOG_LOCKS[key] = lock
        return lock


def _live_catalog_lock_path(live_base: Path) -> Path:
    """Return the sibling lock file for one live catalog root."""
    return live_base.with_name(live_base.name + ".live-catalog.lock")


@contextmanager
def _live_catalog_lock(live_base: Path) -> Iterator[None]:
    """Hold the thread lock and the sibling file lock for ``live_base``."""
    key = str(live_base.resolve(strict=False))
    with (
        _catalog_thread_lock(key),
        _catalog_file_lock(_live_catalog_lock_path(live_base)),
    ):
        yield


@contextmanager
def _catalog_file_lock(lock_path: Path) -> Iterator[None]:
    """Hold an exclusive lock file and always close its descriptor."""
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


def _acquire_exclusive_lock(lock_fd: int) -> None:
    """Take the exclusive interprocess lock for one open descriptor."""
    if sys.platform == "win32":
        import msvcrt

        _acquire_windows_lock(lock_fd, int(msvcrt.LK_LOCK))
        return
    fcntl.flock(lock_fd, fcntl.LOCK_EX)


def _release_exclusive_lock(lock_fd: int) -> None:
    """Release the lock acquired by ``_acquire_exclusive_lock``."""
    if sys.platform == "win32":
        import msvcrt

        _lock_byte(lock_fd, int(msvcrt.LK_UNLCK))
        return
    fcntl.flock(lock_fd, fcntl.LOCK_UN)


def _acquire_windows_lock(lock_fd: int, mode: int) -> None:
    """Retry a blocking Windows byte lock only after CRT ``EDEADLK``."""
    while True:
        try:
            _lock_byte(lock_fd, mode)
        except OSError as error:
            if error.errno != errno.EDEADLK:
                raise
            continue
        return


def _lock_byte(lock_fd: int, mode: int) -> None:
    """Lock one byte at the start of the lock file."""
    import msvcrt

    if os.fstat(lock_fd).st_size < 1:
        os.write(lock_fd, b"\0")
        os.lseek(lock_fd, 0, os.SEEK_SET)
    msvcrt.locking(lock_fd, mode, 1)
