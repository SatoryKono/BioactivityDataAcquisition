"""Shared Bronze cleanup capability and identity primitives."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

_REPARSE_POINT_ATTR = 0x400
_STAGE_PREFIX = ".bronze-cleanup-stage-"
_STAGE_JOURNAL = "origin.json"
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)
_ANCHORED_OPS = bool(
    _O_DIRECTORY
    and _O_NOFOLLOW
    and _O_NONBLOCK
    and os.unlink in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.open in os.supports_dir_fd
    and os.rename in os.supports_dir_fd
    and os.rmdir in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
)


class _CleanupConflict(Exception):
    """A candidate or directory component changed during destructive apply."""


@dataclass(frozen=True, slots=True)
class BronzeRootLease:
    """The root inode held by one cooperative writer or cleaner lock."""

    path: Path
    fd: int | None

    @property
    def writer_path(self) -> Path:
        """Address writes through the locked inode, even if its name is replaced."""
        if self.fd is None:
            return self.path
        locked = os.fstat(self.fd)
        for directory in ("/proc/self/fd", "/dev/fd"):
            candidate = Path(directory) / str(self.fd)
            try:
                opened = candidate.stat()
            except OSError:
                continue
            if (opened.st_dev, opened.st_ino) == (locked.st_dev, locked.st_ino):
                return candidate
        raise NotImplementedError("Bronze writer requires a path to its locked root fd")


def destructive_cleanup_supported() -> bool:
    """Only POSIX handle-relative operations with advisory locking qualify."""
    if not _ANCHORED_OPS or os.name == "nt":
        return False
    try:
        import fcntl
    except ImportError:
        return False
    return hasattr(fcntl, "flock")


def stat_is_link_or_reparse(st: os.stat_result) -> bool:
    """True for symlinks and Windows reparse points (junctions, mounts)."""
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT_ATTR)
