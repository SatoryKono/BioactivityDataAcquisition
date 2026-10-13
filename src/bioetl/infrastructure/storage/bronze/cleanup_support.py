"""Safety helpers for destructive Bronze cleanup operations.

Implements the FS-001 contract (#12102):
- strict ``YYYY-MM-DD`` date directory validation;
- artifact ownership allowlist (only files the writer itself produces);
- symlink/reparse-point rejection on every path component;
- root containment checks on fully-resolved paths;
- re-verification immediately before ``unlink``/``rmdir``.
"""

from __future__ import annotations

import os
import re
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from .cleanup_core import (
    _O_DIRECTORY,
    _O_NOFOLLOW,
    _CleanupConflict,
    destructive_cleanup_supported,
    stat_is_link_or_reparse,
)

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


@contextmanager
def bronze_tree_lock(base_path: Path, *, exclusive: bool) -> Iterator[Path]:
    """Coordinate all application writers and cleaners for one Bronze root.

    This is advisory. The operator must exclude uncooperative same-user writers.
    """
    if not destructive_cleanup_supported():
        if exclusive:
            raise NotImplementedError(
                "Bronze destructive cleanup requires POSIX dir_fd/no-follow and flock"
            )
        yield base_path
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
            # Windows typeshed lacks POSIX-only members even behind this gate.
            fcntl.__dict__["flock"](
                lock_fd,
                fcntl.__dict__["LOCK_EX" if exclusive else "LOCK_SH"],
            )
            if exclusive:
                _recover_stages(root_fd, root_real)
            yield root_real
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


from .cleanup_posix import (  # noqa: E402 - destructive helpers depend on discovery primitives
    _anchored_parent,
    _recover_stages,
    _same_identity,
    safe_rmdir,
    safe_unlink,
)
from .cleanup_posix import (  # noqa: E402 - compatibility import after primitives
    _private_stage as _private_stage,
)
