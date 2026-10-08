"""Safety helpers for destructive Bronze cleanup operations.

Implements the FS-001 contract (#12102):
- strict ``YYYY-MM-DD`` date directory validation;
- artifact ownership allowlist (only files the writer itself produces);
- symlink/reparse-point rejection on every path component;
- root containment checks on fully-resolved paths;
- re-verification immediately before ``unlink``/``rmdir``.
"""

from __future__ import annotations

import fnmatch
import os
import stat
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

__all__ = [
    "date_dir_name_is_older",
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
_OWNED_ARTIFACT_PATTERNS = (
    "batch_*.jsonl.zst",
    "batch_*.jsonl.zst.meta.json",
    "batch_*.jsonl",
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
)


def real_root(base_path: Path) -> Path:
    """Return the fully-resolved trusted root for containment checks."""
    return Path(os.path.realpath(base_path))


def is_within_root(path: Path, root_real: Path) -> bool:
    """True when the resolved path stays beneath the trusted root."""
    try:
        return Path(os.path.realpath(path)).is_relative_to(root_real)
    except (OSError, ValueError):
        return False


def is_fully_resolved(path: Path) -> bool:
    """True when no path component resolves through a link/reparse."""
    try:
        # abspath is required: Path.resolve() would collapse the very links
        # this check is meant to detect.
        return os.path.normcase(os.path.realpath(path)) == os.path.normcase(
            os.path.abspath(path)  # noqa: PTH100
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


def is_owned_artifact(name: str) -> bool:
    """True when a filename matches the Bronze write contract."""
    return any(fnmatch.fnmatch(name, pattern) for pattern in _OWNED_ARTIFACT_PATTERNS)


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
    except OSError:
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


def safe_unlink(file_path: Path, root_real: Path) -> bool:
    """Unlink a file after re-verifying it is a real file inside the root."""
    if _ANCHORED_OPS:
        return _unlink_anchored(file_path, root_real)
    return _unlink_bounded_verify(file_path, root_real)


def _unlink_anchored(file_path: Path, root_real: Path) -> bool:
    """POSIX path: verify parent chain, then unlink via an anchored dir_fd."""
    if not is_fully_resolved(file_path.parent) or not is_within_root(
        file_path.parent, root_real
    ):
        return False
    try:
        parent_fd = os.open(file_path.parent, os.O_RDONLY | _O_DIRECTORY | _O_NOFOLLOW)
    except OSError:
        return False
    try:
        st = os.stat(file_path.name, dir_fd=parent_fd, follow_symlinks=False)
        if stat_is_link_or_reparse(st) or not stat.S_ISREG(st.st_mode):
            return False
        os.unlink(file_path.name, dir_fd=parent_fd)
        return True
    except OSError:
        return False
    finally:
        os.close(parent_fd)


def _unlink_bounded_verify(file_path: Path, root_real: Path) -> bool:
    """Windows path: bounded re-verify immediately before unlink."""
    try:
        st = file_path.lstat()
    except OSError:
        return False
    if stat_is_link_or_reparse(st) or not stat.S_ISREG(st.st_mode):
        return False
    if not is_fully_resolved(file_path.parent) or not is_within_root(
        file_path, root_real
    ):
        return False
    try:
        file_path.unlink()
        return True
    except OSError:
        return False


def safe_rmdir(dir_path: Path, root_real: Path) -> bool:
    """Remove a directory only when it is real, empty, and inside the root."""
    try:
        st = dir_path.lstat()
    except OSError:
        return False
    if stat_is_link_or_reparse(st) or not stat.S_ISDIR(st.st_mode):
        return False
    entries = scan_dir_entries(dir_path)
    if entries is None or entries:
        return False
    if not is_fully_resolved(dir_path) or not is_within_root(dir_path, root_real):
        return False
    try:
        dir_path.rmdir()
        return True
    except OSError:
        return False
