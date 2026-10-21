"""Serialize one quarantine append across threads and local processes.

The in-process lock is a ``threading.Lock``. Other processes on the same
machine share a sibling lock file (``fcntl.flock`` or ``msvcrt.locking``).
The file lock is local and advisory. It does not cover writers on other hosts.
"""

from __future__ import annotations

import errno
import os
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

if sys.platform != "win32":
    import fcntl

__all__ = ["quarantine_append_lock", "quarantine_write_lock_path"]

_APPEND_LOCKS: dict[str, threading.Lock] = {}
_APPEND_LOCKS_GUARD = threading.Lock()
_LockByte = Callable[[int, int, int], object]


def quarantine_write_lock_path(base_path: str) -> Path:
    """Return the sibling lock file for one Delta table path."""
    table = Path(base_path)
    return table.with_name(table.name + ".write.lock")


@contextmanager
def quarantine_append_lock(base_path: str) -> Iterator[None]:
    """Hold the in-process lock and the sibling file lock for ``base_path``."""
    with _thread_lock(base_path), _file_lock(quarantine_write_lock_path(base_path)):
        yield


def _thread_lock(base_path: str) -> threading.Lock:
    """Return the in-process lock that serializes one quarantine path."""
    with _APPEND_LOCKS_GUARD:
        lock = _APPEND_LOCKS.get(base_path)
        if lock is None:
            lock = threading.Lock()
            _APPEND_LOCKS[base_path] = lock
        return lock


@contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
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

        _acquire_windows_lock(lock_fd, msvcrt.locking, int(msvcrt.LK_LOCK))
        return
    fcntl.flock(lock_fd, fcntl.LOCK_EX)


def _release_exclusive_lock(lock_fd: int) -> None:
    """Release the lock acquired by ``_acquire_exclusive_lock``."""
    if sys.platform == "win32":
        import msvcrt

        _lock_byte(lock_fd, msvcrt.locking, int(msvcrt.LK_UNLCK))
        return
    fcntl.flock(lock_fd, fcntl.LOCK_UN)


def _acquire_windows_lock(lock_fd: int, locking: _LockByte, mode: int) -> None:
    """Retry a blocking Windows byte lock only after CRT ``EDEADLK``."""
    while True:
        try:
            _lock_byte(lock_fd, locking, mode)
        except OSError as error:
            if error.errno != errno.EDEADLK:
                raise
            continue
        return


def _lock_byte(lock_fd: int, locking: _LockByte, mode: int) -> None:
    """Lock one byte at the start of the lock file."""
    if os.fstat(lock_fd).st_size < 1:
        os.write(lock_fd, b"\0")
        os.lseek(lock_fd, 0, os.SEEK_SET)
    locking(lock_fd, mode, 1)
