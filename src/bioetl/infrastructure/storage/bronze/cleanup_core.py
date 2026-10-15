"""Shared Bronze cleanup capability and identity primitives."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPARSE_POINT_ATTR = 0x400
_STAGE_PREFIX = ".bronze-cleanup-stage-"
_DONE_PREFIX = ".bronze-cleanup-done-"
_GROUP_STAGE_PREFIX = ".bronze-group-stage-"
_GROUP_JOURNAL_DIR = ".bronze-group-journals"
_CLEANUP_LOCK_NAME = ".bronze-cleanup.lock"
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


_DIR_XATTR_BY_DEV: dict[int, bool] = {}
_XATTR_PROBE_TAG = b"user.bioetl.fs001-capability-probe"


def _xattr_apis() -> tuple[Any, Any, Any | None] | None:  # Any: os xattr callables.
    setter = os.__dict__.get("setxattr")
    getter = os.__dict__.get("getxattr")
    if setter is None or getter is None:
        return None
    return setter, getter, os.__dict__.get("removexattr")


def _xattr_probe_anchor(base_path: Path) -> tuple[int, str] | None:
    """Return ``(st_dev, probe_parent)`` for the Bronze volume, if reachable."""
    try:
        anchor = Path(os.path.abspath(base_path))  # noqa: PTH100
        while not anchor.exists() and anchor.parent != anchor:
            anchor = anchor.parent
        if not anchor.exists():
            return None
        cache_key = int(anchor.stat().st_dev)
        parent = str(anchor if anchor.is_dir() else anchor.parent)
        return cache_key, parent
    except OSError:
        return None


def _default_temp_device() -> int | None:
    """Device id for the default temp volume without creating a probe directory."""
    import tempfile

    try:
        return int(Path(tempfile.gettempdir()).stat().st_dev)
    except OSError:
        return None


def _run_directory_xattr_probe(probe_dir: str | None, cache_key: int) -> bool:
    """Create one probe directory on ``probe_dir`` and cache the result by device."""
    import tempfile

    apis = _xattr_apis()
    if apis is None:
        return False
    setter, getter, remover = apis
    try:
        with tempfile.TemporaryDirectory(
            prefix="bioetl-xattr-probe-", dir=probe_dir
        ) as tmp:
            fd = os.open(tmp, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
            try:
                create_flag = getattr(os, "XATTR_CREATE", 1)
                setter(fd, _XATTR_PROBE_TAG, b"1", flags=create_flag)
                supported = bool(getter(fd, _XATTR_PROBE_TAG) == b"1")
                if remover is not None:
                    remover(fd, _XATTR_PROBE_TAG)
                _DIR_XATTR_BY_DEV[cache_key] = supported
                return supported
            finally:
                os.close(fd)
    except OSError:
        _DIR_XATTR_BY_DEV[cache_key] = False
        return False


def _directory_xattr_supported(base_path: Path | None = None) -> bool:
    """Require directory user-xattr on the target volume before durable intent."""
    if _xattr_apis() is None:
        return False
    if base_path is not None:
        resolved = _xattr_probe_anchor(base_path)
        if resolved is None:
            return False
        cache_key, probe_dir = resolved
        cached = _DIR_XATTR_BY_DEV.get(cache_key)
        if cached is not None:
            return cached
        return _run_directory_xattr_probe(probe_dir, cache_key)
    default_key = _default_temp_device()
    if default_key is None:
        return False
    cached = _DIR_XATTR_BY_DEV.get(default_key)
    if cached is not None:
        return cached
    return _run_directory_xattr_probe(None, default_key)


def _visible_pending_group_markers(base_path: Path) -> bool:
    """Fail-closed reserved journal/stage visibility without a pinned root fd."""
    try:
        names = [entry.name for entry in base_path.iterdir()]
    except OSError:
        return False
    if any(
        name.startswith((_GROUP_STAGE_PREFIX, _STAGE_PREFIX, _DONE_PREFIX))
        for name in names
    ):
        return True
    if _GROUP_JOURNAL_DIR not in names:
        return False
    try:
        return any((base_path / _GROUP_JOURNAL_DIR).iterdir())
    except OSError:
        return True


def shared_lease_without_caps(base_path: Path) -> BronzeRootLease:
    """Shared lease when caps are absent; refuse visible pending group work."""
    if _visible_pending_group_markers(base_path):
        raise OSError("Bronze operation refused while group recovery is pending")
    return BronzeRootLease(base_path, None)


def _platform_cleanup_supported() -> bool:
    """POSIX dir_fd/no-follow, flock, and pinned fd view — without volume xattr."""
    if not _ANCHORED_OPS or os.name == "nt":
        return False
    try:
        import fcntl
    except ImportError:
        return False
    return hasattr(fcntl, "flock") and _fd_view_supported()


def destructive_cleanup_supported() -> bool:
    """Platform gates plus default-temp xattr; prefer per-volume checks at lock."""
    return _platform_cleanup_supported() and _directory_xattr_supported()


def stat_is_link_or_reparse(st: os.stat_result) -> bool:
    """True for symlinks and Windows reparse points (junctions, mounts)."""
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT_ATTR)


def is_reserved_bronze_maintenance_name(name: str) -> bool:
    """Owned journal/stage/lock names are not cleanup discovery targets."""
    return name in {_GROUP_JOURNAL_DIR, _CLEANUP_LOCK_NAME} or name.startswith(
        (_GROUP_STAGE_PREFIX, _STAGE_PREFIX, _DONE_PREFIX)
    )


def _pending_group_operation(root_fd: int) -> bool:
    """Recognize durable group work without following an untrusted directory."""
    names = os.listdir(root_fd)
    if any(name.startswith(_GROUP_STAGE_PREFIX) for name in names):
        return True
    if _GROUP_JOURNAL_DIR not in names:
        return False
    fd = os.open(
        _GROUP_JOURNAL_DIR,
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


@contextmanager
def bronze_tree_lock(
    base_path: Path,
    *,
    exclusive: bool,
    allow_group_recovery: bool = False,
    create_lock: bool = True,
) -> Iterator[BronzeRootLease]:
    """Advisory writer/cleaner lock; ``create_lock=False`` is non-mutating dry-run."""
    caps = _platform_cleanup_supported() and _directory_xattr_supported(base_path)
    if not caps:
        if exclusive:
            raise NotImplementedError(
                "Bronze destructive cleanup requires POSIX dir_fd/no-follow, "
                "flock, and a verified root fd view"
            )
        yield shared_lease_without_caps(base_path)
        return
    import fcntl

    root_path = base_path if exclusive else Path(os.path.realpath(base_path))
    root_real, root_fd = open_bronze_root_no_follow(root_path)
    try:
        flock_fn: Callable[[int, int], None] = fcntl.__dict__["flock"]
        yield from _locked_bronze_root(
            root_real,
            root_fd,
            exclusive=exclusive,
            allow_group_recovery=allow_group_recovery,
            create_lock=create_lock,
            flock=flock_fn,
            lock_ex=int(fcntl.__dict__["LOCK_EX"]),
            lock_sh=int(fcntl.__dict__["LOCK_SH"]),
        )
    finally:
        os.close(root_fd)


def _locked_bronze_root(
    root_real: Path,
    root_fd: int,
    *,
    exclusive: bool,
    allow_group_recovery: bool,
    create_lock: bool,
    flock: Callable[[int, int], None],
    lock_ex: int,
    lock_sh: int,
) -> Iterator[BronzeRootLease]:
    flags = os.O_RDWR | _O_NOFOLLOW | _O_NONBLOCK
    if create_lock:
        flags |= os.O_CREAT
    try:
        lock_fd = os.open(".bronze-cleanup.lock", flags, 0o600, dir_fd=root_fd)
    except FileNotFoundError:
        if exclusive or create_lock:
            raise
        yield _shared_lease_after_pending_check(root_real, root_fd)
        return
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise OSError("Bronze cleanup lock is not a regular file")
        flock(lock_fd, lock_ex if exclusive else lock_sh)
        yield _shared_lease_after_pending_check(
            root_real,
            root_fd,
            exclusive=exclusive,
            allow_group_recovery=allow_group_recovery,
        )
    finally:
        os.close(lock_fd)


def _shared_lease_after_pending_check(
    root_real: Path,
    root_fd: int,
    *,
    exclusive: bool = False,
    allow_group_recovery: bool = False,
) -> BronzeRootLease:
    lease = BronzeRootLease(root_real, root_fd)
    _ = lease.writer_path
    if _pending_group_operation(root_fd) and not (exclusive and allow_group_recovery):
        raise OSError("Bronze operation refused while group recovery is pending")
    if not exclusive and any(
        name.startswith((_STAGE_PREFIX, _DONE_PREFIX)) for name in os.listdir(root_fd)
    ):
        raise OSError("Bronze writer refused while cleanup recovery is pending")
    return lease
