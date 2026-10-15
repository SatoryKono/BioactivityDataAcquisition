"""Shared Bronze cleanup capability and identity primitives."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

_REPARSE_POINT_ATTR = 0x400
_STAGE_PREFIX = ".bronze-cleanup-stage-"
_DONE_PREFIX = ".bronze-cleanup-done-"
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
        """Route writes through the locked inode, even if its name is replaced."""
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


def open_bronze_root_no_follow(base_path: Path) -> tuple[Path, int]:
    """Pin every component of the configured root without following links."""
    root_abs = Path(os.path.abspath(base_path))  # noqa: PTH100 - preserve links
    flags = os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW
    fd = os.open(root_abs.anchor, flags)
    try:
        for name in root_abs.parts[1:]:
            next_fd = os.open(name, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        named = root_abs.lstat()
        opened = os.fstat(fd)
        if stat_is_link_or_reparse(named) or (
            named.st_dev,
            named.st_ino,
        ) != (opened.st_dev, opened.st_ino):
            raise OSError("Bronze root changed while opening its components")
        return root_abs, fd
    except BaseException:
        os.close(fd)
        raise


def valid_bronze_scope_name(value: str) -> bool:
    """The provider/entity naming contract shared by writes and cleanup."""
    return bool(value) and value.replace("_", "").isalnum()


def _fd_view_supported() -> bool:
    """Require a verified pathname to an open directory for pinned writer I/O."""
    try:
        fd = os.open("/", os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    except OSError:
        return False
    try:
        opened = os.fstat(fd)
        for directory in ("/proc/self/fd", "/dev/fd"):
            try:
                viewed = (Path(directory) / str(fd)).stat()
            except OSError:
                continue
            if (viewed.st_dev, viewed.st_ino) == (opened.st_dev, opened.st_ino):
                return True
        return False
    finally:
        os.close(fd)


_DIR_XATTR_FS: bool | None = None


def _directory_xattr_supported() -> bool:
    """Require directory user-xattr before publishing a durable group intent."""
    global _DIR_XATTR_FS
    setter = os.__dict__.get("setxattr")
    getter = os.__dict__.get("getxattr")
    remover = os.__dict__.get("removexattr")
    if setter is None or getter is None:
        return False
    if _DIR_XATTR_FS is not None:
        return _DIR_XATTR_FS
    import tempfile

    probe_tag = b"user.bioetl.fs001-capability-probe"
    try:
        with tempfile.TemporaryDirectory(prefix="bioetl-xattr-probe-") as tmp:
            fd = os.open(tmp, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
            try:
                create_flag = getattr(os, "XATTR_CREATE", 1)
                setter(fd, probe_tag, b"1", flags=create_flag)
                supported = getter(fd, probe_tag) == b"1"
                if remover is not None:
                    remover(fd, probe_tag)
                _DIR_XATTR_FS = supported
                return supported
            finally:
                os.close(fd)
    except OSError:
        _DIR_XATTR_FS = False
        return False


def destructive_cleanup_supported() -> bool:
    """Require anchored ops, flock, pinned writer I/O, and directory xattr."""
    if not _ANCHORED_OPS or os.name == "nt":
        return False
    try:
        import fcntl
    except ImportError:
        return False
    return (
        hasattr(fcntl, "flock")
        and _fd_view_supported()
        and _directory_xattr_supported()
    )


def stat_is_link_or_reparse(st: os.stat_result) -> bool:
    """True for symlinks and Windows reparse points (junctions, mounts)."""
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT_ATTR)


def _pending_group_operation(root_fd: int) -> bool:
    """Recognize durable group work without following an untrusted directory."""
    names = os.listdir(root_fd)
    if any(name.startswith(".bronze-group-stage-") for name in names):
        return True
    if ".bronze-group-journals" not in names:
        return False
    fd = os.open(
        ".bronze-group-journals",
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | _O_NOFOLLOW,
        dir_fd=root_fd,
    )
    try:
        # Visible emptiness after unlink is not durable until the directory fsyncs.
        if os.listdir(fd):  # noqa: PTH208 - pinned directory fd
            return True
        os.fsync(fd)
        return bool(os.listdir(fd))  # noqa: PTH208 - pinned directory fd
    finally:
        os.close(fd)


def _finish_private_stage(
    root_fd: int,
    stage_fd: int,
    name: str,
    relative: Path,
    on_stage_error: Callable[[str, OSError], None] | None,
) -> None:
    """Report post-commit durability failures without losing removal counts."""
    stage_error: OSError | None = None
    marker = name.replace(_STAGE_PREFIX, _DONE_PREFIX, 1)
    marked_complete = False
    try:
        if relative.name not in os.listdir(stage_fd):
            os.rename(
                _STAGE_JOURNAL,
                marker,
                src_dir_fd=stage_fd,
                dst_dir_fd=root_fd,
            )
            marked_complete = True
            os.fsync(stage_fd)
            os.fsync(root_fd)
    except OSError as exc:
        stage_error = exc
    try:
        owned = os.fstat(stage_fd)
        named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if (owned.st_dev, owned.st_ino) != (named.st_dev, named.st_ino):
            raise OSError("Bronze cleanup stage replaced before retirement")
        os.rmdir(name, dir_fd=root_fd)
        os.fsync(root_fd)
    except OSError as exc:
        stage_error = stage_error or exc
    finally:
        os.close(stage_fd)
    if marked_complete and stage_error is None:
        try:
            os.unlink(marker, dir_fd=root_fd)
            os.fsync(root_fd)
        except OSError as exc:
            stage_error = exc
    if stage_error is not None:
        if on_stage_error is None:
            raise stage_error
        on_stage_error(name, stage_error)


def _entry_is_link_or_reparse(entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    try:
        return stat_is_link_or_reparse(entry.stat(follow_symlinks=False))
    except OSError:
        return True
