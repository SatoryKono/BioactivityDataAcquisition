"""Safety helpers for destructive Bronze cleanup operations.

Implements the FS-001 contract (#12102):
- strict ``YYYY-MM-DD`` date directory validation;
- artifact ownership allowlist (only files the writer itself produces);
- symlink/reparse-point rejection on every path component;
- root containment checks on fully-resolved paths;
- re-verification immediately before ``unlink``/``rmdir``.
"""

from __future__ import annotations

import errno
import os
import re
import secrets
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

__all__ = [
    "bronze_tree_lock",
    "candidate_is_safe",
    "date_dir_name_is_older",
    "destructive_cleanup_supported",
    "find_old_date_dirs",
    "is_fully_resolved",
    "is_owned_artifact",
    "is_within_root",
    "iter_safe_child_dirs",
    "real_root",
    "safe_named_child_dir",
    "safe_rmdir",
    "safe_unlink",
    "scan_dir_entries",
    "stat_is_link_or_reparse",
    "validate_scope_filter",
]

# Artifacts produced by BronzeWriter under a date directory:
# payload ``batch_<date>_<batch_id>.jsonl.zst``, its sidecar
# ``batch_<date>_<batch_id>.jsonl.zst.meta.json`` and the optional
# uncompressed copy ``batch_<date>_<batch_id>.jsonl``.
_BATCH_ARTIFACT = re.compile(
    r"^batch_(\d{4}-\d{2}-\d{2})_([0-9a-f]{8}-[0-9a-f]{4}-"
    r"[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(\.jsonl\.zst|\.jsonl\.zst\.meta\.json|\.jsonl)$"
)

_DATE_DIR_FORMAT = "%Y-%m-%d"

# Windows FILE_ATTRIBUTE_REPARSE_POINT — covers junctions, mount points and
# other reparse-point types, not just symlinks.
_REPARSE_POINT_ATTR = 0x400

# POSIX anchored operations: dir_fd support is unavailable on Windows.
_O_DIRECTORY = getattr(os, "O_DIRECTORY", 0)
_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_ANCHORED_OPS = bool(
    _O_DIRECTORY
    and _O_NOFOLLOW
    and os.unlink in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
    and os.open in os.supports_dir_fd
    and os.rename in os.supports_dir_fd
    and os.rmdir in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
)


def destructive_cleanup_supported() -> bool:
    """Only POSIX handle-relative operations with advisory locking qualify."""
    if not _ANCHORED_OPS or os.name == "nt":
        return False
    try:
        import fcntl
    except ImportError:
        return False
    return hasattr(fcntl, "flock")


@contextmanager
def bronze_tree_lock(base_path: Path, *, exclusive: bool) -> Iterator[None]:
    """Coordinate all application writers and cleaners for one Bronze root.

    This is advisory. The operator must exclude uncooperative same-user writers.
    """
    if not destructive_cleanup_supported():
        if exclusive:
            raise NotImplementedError(
                "Bronze destructive cleanup requires POSIX dir_fd/no-follow and flock"
            )
        yield
        return
    import fcntl

    root_real = real_root(base_path)
    root_fd = os.open(root_real, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    try:
        lock_fd = os.open(
            ".bronze-cleanup.lock",
            os.O_CREAT | os.O_RDWR | _O_NOFOLLOW,
            0o600,
            dir_fd=root_fd,
        )
        try:
            if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
                raise OSError("Bronze cleanup lock is not a regular file")
            fcntl.flock(  # type: ignore[attr-defined]  # POSIX-only runtime gate
                lock_fd,
                (fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH),  # type: ignore[attr-defined]
            )
            yield
        finally:
            os.close(lock_fd)
    finally:
        os.close(root_fd)


def real_root(base_path: Path) -> Path:
    """Return the fully-resolved trusted root for containment checks."""
    return Path(os.path.realpath(base_path))


def is_within_root(path: Path, root_real: Path) -> bool:
    """True when the resolved path stays beneath the trusted root."""
    try:
        return Path(os.path.realpath(path)).is_relative_to(root_real)
    except (OSError, ValueError):
        return False


def is_fully_resolved(path: Path, root_abs: Path, root_real: Path) -> bool:
    """True when no component below the trusted root resolves through a link."""
    try:
        # abspath is required: Path.resolve() would collapse the very links
        # this check is meant to detect.
        relative = Path(os.path.abspath(path)).relative_to(root_abs)  # noqa: PTH100
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(
            root_real / relative
        )
    except (OSError, ValueError):
        return False


def stat_is_link_or_reparse(st: os.stat_result) -> bool:
    """True for symlinks and Windows reparse points (junctions, mounts)."""
    if stat.S_ISLNK(st.st_mode):
        return True
    return bool(getattr(st, "st_file_attributes", 0) & _REPARSE_POINT_ATTR)


def _entry_is_link_or_reparse(entry: os.DirEntry[str]) -> bool:
    if entry.is_symlink():
        return True
    try:
        return stat_is_link_or_reparse(entry.stat(follow_symlinks=False))
    except OSError:
        return True


def is_owned_artifact(
    name: str,
    *,
    date_name: str | None = None,
    payload_names: set[str] | None = None,
) -> bool:
    """Match a canonical writer UUID/date and require sidecar/copy association."""
    match = _BATCH_ARTIFACT.fullmatch(name)
    if match is None:
        return False
    artifact_date, batch_id, _suffix = match.groups()
    try:
        valid_date = (
            datetime.strptime(artifact_date, _DATE_DIR_FORMAT).strftime(
                _DATE_DIR_FORMAT
            )
            == artifact_date
        )
    except ValueError:
        return False
    if not valid_date:
        return False
    if date_name is not None and artifact_date != date_name:
        return False
    if str(UUID(batch_id)) != batch_id:
        return False
    if payload_names is None:
        return True
    return f"batch_{artifact_date}_{batch_id}.jsonl.zst" in payload_names


def date_dir_name_is_older(name: str, cutoff_str: str) -> bool:
    """True for canonical ``YYYY-MM-DD`` names strictly older than cutoff."""
    try:
        parsed = datetime.strptime(name, _DATE_DIR_FORMAT).date()
    except ValueError:
        return False
    if parsed.strftime(_DATE_DIR_FORMAT) != name:
        return False
    return name < cutoff_str


def validate_scope_filter(value: str | None, label: str) -> None:
    """Reject scope filters that could broaden cleanup beyond a named dir."""
    if value is None:
        return
    if not value or not value.replace("_", "").isalnum():
        raise ValueError(
            f"Invalid {label} filter for Bronze cleanup: {value!r}. "
            "Use alphanumeric characters and underscores only."
        )


def scan_dir_entries(parent: Path) -> list[os.DirEntry[str]] | None:
    """Snapshot directory entries; None when the directory is unreadable."""
    try:
        with os.scandir(parent) as it:
            return list(it)
    except OSError:
        return None


def iter_safe_child_dirs(
    parent: Path,
    *,
    on_skip: Callable[[str, str], None] | None = None,
) -> list[Path]:
    """List direct child directories without following links/reparse points."""
    entries = scan_dir_entries(parent)
    if entries is None:
        _notify_skip(on_skip, parent, "scan_error")
        return []
    dirs: list[Path] = []
    for entry in entries:
        try:
            if _entry_is_link_or_reparse(entry):
                _notify_skip(on_skip, entry.path, "link_or_reparse")
                continue
            if entry.is_dir(follow_symlinks=False):
                dirs.append(Path(entry.path))
            else:
                _notify_skip(on_skip, entry.path, "not_a_directory")
        except OSError:
            _notify_skip(on_skip, entry.path, "stat_error")
    return dirs


def _notify_skip(
    on_skip: Callable[[str, str], None] | None, path: object, reason: str
) -> None:
    if on_skip is not None:
        on_skip(str(path), reason)


def safe_named_child_dir(
    parent: Path,
    name: str,
    root_real: Path,
    *,
    on_skip: Callable[[str, str], None] | None = None,
) -> Path | None:
    """Resolve an explicitly named child dir, refusing links/escapes."""
    child = parent / name
    try:
        st = child.lstat()
    except FileNotFoundError:
        _notify_skip(on_skip, child, "missing_scope")
        return None
    except OSError:
        _notify_skip(on_skip, child, "stat_error")
        return None
    if not stat.S_ISDIR(st.st_mode) or stat_is_link_or_reparse(st):
        _notify_skip(on_skip, child, "link_or_reparse")
        return None
    if not is_within_root(child, root_real):
        _notify_skip(on_skip, child, "outside_root")
        return None
    return child


def find_old_date_dirs(
    base_path: Path,
    *,
    flat_structure: bool,
    cutoff_str: str,
    provider: str | None = None,
    entity: str | None = None,
    on_skip: Callable[[str, str], None] | None = None,
    on_flat_filter: Callable[[], None] | None = None,
) -> list[Path]:
    """Find canonical date dirs older than cutoff in flat or nested layout."""
    validate_scope_filter(provider, "provider")
    validate_scope_filter(entity, "entity")
    if not base_path.exists():
        return []
    if flat_structure:
        return _flat_old_date_dirs(
            base_path, cutoff_str, provider, entity, on_skip, on_flat_filter
        )
    return _nested_old_date_dirs(
        base_path, real_root(base_path), cutoff_str, provider, entity, on_skip
    )


def _flat_old_date_dirs(
    base_path: Path,
    cutoff_str: str,
    provider: str | None,
    entity: str | None,
    on_skip: Callable[[str, str], None] | None,
    on_flat_filter: Callable[[], None] | None,
) -> list[Path]:
    if provider or entity:
        if on_flat_filter is not None:
            on_flat_filter()
        return []
    return _old_date_children(base_path, cutoff_str, on_skip)


def _nested_old_date_dirs(
    base_path: Path,
    root_real: Path,
    cutoff_str: str,
    provider: str | None,
    entity: str | None,
    on_skip: Callable[[str, str], None] | None,
) -> list[Path]:
    old_dirs: list[Path] = []
    for provider_dir in _scope_child_dirs(base_path, provider, root_real, on_skip):
        for entity_dir in _scope_child_dirs(provider_dir, entity, root_real, on_skip):
            old_dirs.extend(_old_date_children(entity_dir, cutoff_str, on_skip))
    return old_dirs


def _old_date_children(
    parent: Path,
    cutoff_str: str,
    on_skip: Callable[[str, str], None] | None,
) -> list[Path]:
    return [
        date_dir
        for date_dir in iter_safe_child_dirs(parent, on_skip=on_skip)
        if date_dir_name_is_older(date_dir.name, cutoff_str)
    ]


def _scope_child_dirs(
    parent: Path,
    name: str | None,
    root_real: Path,
    on_skip: Callable[[str, str], None] | None,
) -> list[Path]:
    """Resolve a named scope dir or enumerate all safe child dirs."""
    if name is None:
        return iter_safe_child_dirs(parent, on_skip=on_skip)
    resolved = safe_named_child_dir(parent, name, root_real, on_skip=on_skip)
    return [resolved] if resolved is not None else []


class _CleanupConflict(Exception):
    """A candidate or directory component changed during destructive apply."""


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (left.st_dev, left.st_ino) == (right.st_dev, right.st_ino)


def candidate_is_safe(
    path: Path,
    root_abs: Path,
    root_real: Path,
    expected: os.stat_result,
    *,
    directory: bool = False,
) -> bool:
    """Nonmutating eligibility used by dry-run and apply planning."""
    if destructive_cleanup_supported():
        try:
            with _anchored_parent(path, root_abs, root_real) as (
                _root_fd,
                parent_fd,
                name,
                _chain,
            ):
                actual = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                return (
                    _same_identity(actual, expected)
                    and not stat_is_link_or_reparse(actual)
                    and (
                        stat.S_ISDIR(actual.st_mode)
                        if directory
                        else stat.S_ISREG(actual.st_mode)
                    )
                )
        except (OSError, _CleanupConflict):
            return False
    if not is_fully_resolved(path, root_abs, root_real) or not is_within_root(
        path, root_real
    ):
        return False
    try:
        actual = path.lstat()
    except OSError:
        return False
    return (
        _same_identity(actual, expected)
        and not stat_is_link_or_reparse(actual)
        and (
            stat.S_ISDIR(actual.st_mode) if directory else stat.S_ISREG(actual.st_mode)
        )
    )


@contextmanager
def _anchored_parent(
    path: Path, root_abs: Path, root_real: Path
) -> Iterator[tuple[int, int, str, list[tuple[int, int, str]]]]:
    """Open every relative parent component without following a link."""
    if not destructive_cleanup_supported():
        raise NotImplementedError("Bronze destructive cleanup has no safe handle API")
    try:
        parts = Path(os.path.abspath(path)).relative_to(root_abs).parts  # noqa: PTH100
    except ValueError as exc:
        raise _CleanupConflict from exc
    if not parts or any(part in ("", ".", "..") for part in parts):
        raise _CleanupConflict
    fds: list[int] = []
    chain: list[tuple[int, int, str]] = []
    try:
        root_fd = os.open(root_real, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
        fds.append(root_fd)
        parent_fd = root_fd
        for name in parts[:-1]:
            child_fd = os.open(
                name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=parent_fd
            )
            fds.append(child_fd)
            chain.append((parent_fd, child_fd, name))
            parent_fd = child_fd
        if not _chain_is_stable(root_fd, root_abs, chain):
            raise _CleanupConflict
        yield root_fd, parent_fd, parts[-1], chain
    finally:
        for fd in reversed(fds):
            os.close(fd)


def _chain_is_stable(
    root_fd: int, root_abs: Path, chain: list[tuple[int, int, str]]
) -> bool:
    try:
        if not _same_identity(os.fstat(root_fd), root_abs.stat()):
            return False
        for parent_fd, child_fd, name in chain:
            named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if stat_is_link_or_reparse(named) or not _same_identity(
                named, os.fstat(child_fd)
            ):
                return False
    except OSError:
        return False
    return True


@contextmanager
def _private_stage(
    root_fd: int,
    on_stage_error: Callable[[str, OSError], None] | None = None,
) -> Iterator[int]:
    """Isolate a target name before checking its identity and deleting it."""
    name = f".bronze-cleanup-stage-{secrets.token_hex(16)}"
    os.mkdir(name, 0o700, dir_fd=root_fd)
    stage_fd = os.open(name, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW, dir_fd=root_fd)
    try:
        yield stage_fd
    finally:
        os.close(stage_fd)
        try:
            os.rmdir(name, dir_fd=root_fd)
        except OSError as exc:
            # A conflicted artifact may remain in the stage; expose its name.
            if on_stage_error is None:
                raise
            on_stage_error(name, exc)


def _restore_staged(name: str, stage_fd: int, parent_fd: int) -> None:
    """Restore a refused artifact only when its original name is still free."""
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        os.rename(name, name, src_dir_fd=stage_fd, dst_dir_fd=parent_fd)


def safe_unlink(
    file_path: Path,
    root_abs: Path,
    root_real: Path,
    expected: os.stat_result | None = None,
    *,
    on_stage_error: Callable[[str, OSError], None] | None = None,
) -> bool:
    """Delete only the planned inode after atomic isolation under the root."""
    try:
        with _anchored_parent(file_path, root_abs, root_real) as (
            root_fd,
            parent_fd,
            name,
            chain,
        ):
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                stat_is_link_or_reparse(current)
                or not stat.S_ISREG(current.st_mode)
                or (expected is not None and not _same_identity(expected, current))
            ):
                return False
            with _private_stage(root_fd, on_stage_error) as stage_fd:
                os.rename(name, name, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
                staged = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                if not _same_identity(current, staged) or not _chain_is_stable(
                    root_fd, root_abs, chain
                ):
                    _restore_staged(name, stage_fd, parent_fd)
                    return False
                os.unlink(name, dir_fd=stage_fd)
                return True
    except (FileNotFoundError, NotADirectoryError, _CleanupConflict):
        return False


def safe_rmdir(
    dir_path: Path,
    root_abs: Path,
    root_real: Path,
    expected: os.stat_result | None = None,
    *,
    on_stage_error: Callable[[str, OSError], None] | None = None,
) -> bool:
    """Remove only the planned empty directory after atomic isolation."""
    try:
        with _anchored_parent(dir_path, root_abs, root_real) as (
            root_fd,
            parent_fd,
            name,
            chain,
        ):
            current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                stat_is_link_or_reparse(current)
                or not stat.S_ISDIR(current.st_mode)
                or (expected is not None and not _same_identity(expected, current))
            ):
                return False
            with _private_stage(root_fd, on_stage_error) as stage_fd:
                os.rename(name, name, src_dir_fd=parent_fd, dst_dir_fd=stage_fd)
                staged = os.stat(name, dir_fd=stage_fd, follow_symlinks=False)
                if not _same_identity(current, staged) or not _chain_is_stable(
                    root_fd, root_abs, chain
                ):
                    _restore_staged(name, stage_fd, parent_fd)
                    return False
                try:
                    os.rmdir(name, dir_fd=stage_fd)
                except OSError as exc:
                    _restore_staged(name, stage_fd, parent_fd)
                    if exc.errno in (errno.ENOTEMPTY, errno.EEXIST):
                        return False
                    raise
                return True
    except (FileNotFoundError, NotADirectoryError, _CleanupConflict):
        return False
