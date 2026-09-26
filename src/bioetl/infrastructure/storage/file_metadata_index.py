"""Bounded process-local file projections, revalidated on every lookup.

Directory enumeration remains authoritative for additions and removals. Cached
values never outlive a changed file signature or a failed filesystem read.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Callable
from os import stat_result
from pathlib import Path
from threading import RLock

_MAX_BYTES = 16 * 1024 * 1024
_MAX_ENTRIES = 4096


def _signature(info: stat_result) -> tuple[int, ...]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
        info.st_mode,
    )


class FileMetadataIndex:
    """Share unchanged UTF-8 projections while bounding memory and concurrent I/O.

    Nanosecond timestamps, file identity, size and mode detect normal edits,
    replacement, and permission changes. This is an I/O optimization, not a
    cryptographic integrity check; callers still validate decoded identities.
    """

    def __init__(self, project: Callable[[str], str] = str) -> None:
        self._project = project
        self._entries: OrderedDict[str, tuple[tuple[int, ...], str, int]] = (
            OrderedDict()
        )
        self._bytes = 0
        self._lock = RLock()
        self._read_locks = tuple(RLock() for _ in range(32))

    def read(self, path: Path) -> str:
        """Return a validated projection; never return a stale value on failure."""
        key = str(path.absolute())
        with self._read_locks[hash(key) % len(self._read_locks)]:
            try:
                return self._read_current(path, key)
            except (OSError, ValueError, TypeError):
                with self._lock:
                    self._discard(key)
                raise

    def _read_current(self, path: Path, key: str) -> str:
        for _ in range(2):
            before = _signature(path.stat())
            with self._lock:
                cached = self._entries.get(key)
                if cached is not None and cached[0] == before:
                    self._entries.move_to_end(key)
                    return cached[1]
                self._discard(key)
            value = self._project(path.read_text(encoding="utf-8"))
            if _signature(path.stat()) == before:
                self._remember(key, before, value)
                return value
        raise OSError("Catalog file changed during metadata read")

    def _discard(self, key: str) -> None:
        previous = self._entries.pop(key, None)
        if previous is not None:
            self._bytes -= previous[2]

    def _remember(self, key: str, signature: tuple[int, ...], value: str) -> None:
        size = len(value.encode("utf-8"))
        if size > _MAX_BYTES:
            return
        with self._lock:
            self._discard(key)
            self._entries[key] = (signature, value, size)
            self._bytes += size
            while self._bytes > _MAX_BYTES or len(self._entries) > _MAX_ENTRIES:
                self._discard(next(iter(self._entries)))


# Shared by manifest stores created for selectors, recent runs and details.
catalog_text_index = FileMetadataIndex()
