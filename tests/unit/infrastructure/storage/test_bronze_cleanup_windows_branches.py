"""Windows coverage for Bronze cleanup branches that POSIX jobs skip.

The emulator maps directory fds onto a real temp tree and forwards file
fds to the host ``os`` module. It does not replace process-wide ``os``.
"""

from __future__ import annotations

import errno
import json
import os
import pathlib
import sys
import types
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace

import pytest
from bioetl.infrastructure.storage.bronze import (
    cleanup_core,
    cleanup_metrics,
    cleanup_posix,
)
from bioetl.infrastructure.storage.bronze import cleanup_group_apply as apply_mod
from bioetl.infrastructure.storage.bronze import cleanup_group_schema as schema
from bioetl.infrastructure.storage.bronze import cleanup_planner as planner
from bioetl.infrastructure.storage.bronze import cleanup_preview_mixin as preview_mod
from bioetl.infrastructure.storage.bronze import cleanup_support as support
from bioetl.infrastructure.storage.bronze import read_cleanup_mixin as read_cleanup
from bioetl.infrastructure.storage.bronze.cleanup_core import BronzeRootLease
from bioetl.infrastructure.storage.bronze.cleanup_group_apply import BronzeGroupCleanup
from bioetl.infrastructure.storage.bronze.cleanup_group_schema import (
    GroupJournalConflict,
    GroupJournalFailure,
    GroupRecoveryResult,
    GroupSpec,
)
from bioetl.infrastructure.storage.bronze.cleanup_preview_mixin import (
    BronzeCleanupPreviewMixin,
)

pytestmark = pytest.mark.unit

_BATCH = "12345678-1234-5678-9abc-def012345678"
_DATE = "2020-01-01"
_CUTOFF = "2021-01-01"
_DIGEST = "ab" * 32


class _PathProxy:
    def __init__(self, bridge: DirFdBridge) -> None:
        self._bridge = bridge

    def abspath(self, path: str) -> str:
        hook = self._bridge.abspath_hook
        if hook is not None:
            return hook(path)
        return os.path.abspath(path)

    def __getattr__(self, name: str):
        return getattr(os.path, name)


class DirFdBridge:
    """dir_fd-capable os stand-in backed by a real temporary tree."""

    def __init__(self) -> None:
        self._real = os
        self._dirs: dict[int, Path] = {}
        self._files: dict[int, int] = {}
        self._next = 10_000_000
        self.name = os.name
        self.path = _PathProxy(self)
        self.fstat_hook: Callable[[int, os.stat_result], object] | None = None
        self.write_override: Callable[[int, bytes], int | None] | None = None
        self.fail_open: Callable[[object, int, int | None], bool] | None = None
        self.rename_error: Callable[[Path, Path], int] | None = None
        self.rmdir_error: Callable[[Path], int] | None = None
        self.unlink_error: Callable[[Path], int] | None = None
        self.stat_error: Callable[[Path], bool] | None = None
        self.stat_lie: Callable[[Path], bool] | None = None
        self.lie_stat: os.stat_result | None = None
        self.eloop_names: set[str] = set()
        self.abspath_hook: Callable[[str], str] | None = None
        self.geteuid: Callable[[], int] | None = None

    def __getattr__(self, name: str):
        return getattr(self._real, name)

    def bind_dir(self, path: Path) -> int:
        fd = self._alloc()
        self._dirs[fd] = Path(path)
        return fd

    def resolve(self, path: object, dir_fd: int | None) -> Path:
        name = Path(path)
        if dir_fd is None:
            return name
        directory = self._dirs.get(dir_fd)
        if directory is not None:
            return directory / name
        if dir_fd in self._files:
            raise NotADirectoryError(errno.ENOTDIR, "not a directory", str(path))
        raise OSError(errno.EBADF, "bad file descriptor")

    def open(self, path, flags, mode=0o777, *, dir_fd=None):
        self._reject_open(path, flags, dir_fd)
        resolved = self.resolve(path, dir_fd)
        self._reject_eloop(resolved)
        if _is_dir(resolved):
            return self.bind_dir(resolved)
        return self._open_real(resolved, flags, mode)

    def mkdir(self, path, mode=0o777, *, dir_fd=None) -> None:
        self._real.mkdir(self.resolve(path, dir_fd), mode)

    def rmdir(self, path, *, dir_fd=None) -> None:
        resolved = self.resolve(path, dir_fd)
        self._raise_code(self.rmdir_error, resolved)
        self._real.rmdir(resolved)

    def unlink(self, path, *, dir_fd=None) -> None:
        resolved = self.resolve(path, dir_fd)
        self._raise_code(self.unlink_error, resolved)
        self._real.unlink(resolved)

    def rename(self, src, dst, *, src_dir_fd=None, dst_dir_fd=None) -> None:
        source = self.resolve(src, src_dir_fd)
        dest = self.resolve(dst, dst_dir_fd)
        self._raise_code(self.rename_error, source, dest)
        self._real.rename(source, dest)

    def stat(self, path, *, dir_fd=None, follow_symlinks=True):
        resolved = self.resolve(path, dir_fd)
        if self.stat_error is not None and self.stat_error(resolved):
            raise OSError(errno.EIO, "stat", str(resolved))
        if (
            self.stat_lie is not None
            and self.lie_stat is not None
            and self.stat_lie(resolved)
        ):
            return self.lie_stat
        if follow_symlinks:
            return self._real.stat(resolved)
        return self._real.lstat(resolved)

    def listdir(self, path=None):
        if isinstance(path, int):
            directory = self._dirs.get(path)
            if directory is None:
                raise NotADirectoryError(errno.ENOTDIR, "not a directory")
            return self._real.listdir(directory)
        return self._real.listdir(path)

    def read(self, fd: int, size: int) -> bytes:
        return self._real.read(self._files[fd], size)

    def write(self, fd: int, data: bytes) -> int:
        if self.write_override is not None:
            overridden = self.write_override(fd, data)
            if overridden is not None:
                return overridden
        return self._real.write(self._files[fd], data)

    def close(self, fd: int) -> None:
        if fd in self._dirs:
            del self._dirs[fd]
            return
        real = self._files.pop(fd, None)
        if real is None:
            raise OSError(errno.EBADF, "bad file descriptor")
        self._real.close(real)

    def dup(self, fd: int) -> int:
        directory = self._dirs.get(fd)
        if directory is not None:
            return self.bind_dir(directory)
        real = self._files.get(fd)
        if real is None:
            raise OSError(errno.EBADF, "bad file descriptor")
        return self._bind_file(self._real.dup(real))

    def fstat(self, fd: int):
        if fd in self._dirs:
            current = self._real.stat(self._dirs[fd])
        elif fd in self._files:
            current = self._real.fstat(self._files[fd])
        else:
            raise OSError(errno.EBADF, "bad file descriptor")
        if self.fstat_hook is not None:
            return self.fstat_hook(fd, current)
        return current

    def fsync(self, fd: int) -> None:
        if fd in self._dirs:
            return
        self._real.fsync(self._files[fd])

    def _alloc(self) -> int:
        fd = self._next
        self._next += 1
        return fd

    def _bind_file(self, real_fd: int) -> int:
        fd = self._alloc()
        self._files[fd] = real_fd
        return fd

    def _open_real(self, resolved: Path, flags: int, mode: int) -> int:
        creating = bool(flags & os.O_CREAT)
        if not creating and not resolved.is_file():
            raise FileNotFoundError(errno.ENOENT, "not found", str(resolved))
        return self._bind_file(self._real.open(os.fspath(resolved), flags, mode))

    def _reject_open(self, path, flags: int, dir_fd: int | None) -> None:
        if self.fail_open is not None and self.fail_open(path, flags, dir_fd):
            raise OSError(errno.EIO, "open", str(path))

    def _reject_eloop(self, resolved: Path) -> None:
        if resolved.name in self.eloop_names and resolved.exists():
            raise OSError(errno.ELOOP, "too many links", str(resolved))

    @staticmethod
    def _raise_code(hook, *paths: Path) -> None:
        if hook is None:
            return
        code = hook(*paths)
        if code:
            raise OSError(code, "hook", str(paths[0]))


class _BlockFcntl:
    def find_spec(self, name, path, target=None):
        if name == "fcntl":
            raise ImportError("fcntl unavailable")
        return None


class _Planner(planner.BronzeCleanupPlannerMixin):
    def __init__(self, flat: bool) -> None:
        self._flat_structure = flat
        self.skips: list[tuple[str, str]] = []

    def _log_cleanup_skip(self, path: str, reason: str) -> None:
        self.skips.append((path, reason))

    def _resolve_bronze_path(self, provider, entity, date_str, filename) -> str:
        if self._flat_structure:
            return f"{date_str}/{filename}"
        return f"{provider}/{entity}/{date_str}/{filename}"


class _Preview(BronzeCleanupPreviewMixin):
    def __init__(self, base: Path, flat: bool) -> None:
        self.base_path = base
        self._flat_structure = flat


class _BoomEntry:
    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = str(path)

    def stat(self, follow_symlinks: bool = True):
        raise OSError("stat")


class _StatEntry:
    def __init__(self, name: str, path: Path, *, boom: bool) -> None:
        self.name = name
        self.path = str(path)
        self._boom = boom

    def stat(self, follow_symlinks: bool = True):
        if self._boom:
            raise OSError("stat")
        return Path(self.path).stat(follow_symlinks=follow_symlinks)

    def is_symlink(self) -> bool:
        return False

    def is_dir(self, follow_symlinks: bool = True) -> bool:
        return Path(self.path).is_dir()


class _Scan:
    def __init__(self, entries) -> None:
        self._entries = entries

    def __enter__(self):
        return iter(self._entries)

    def __exit__(self, *args) -> bool:
        return False


class _Journal:
    def __init__(self) -> None:
        self.pending_result = []
        self.recover_result: GroupRecoveryResult | OSError = GroupRecoveryResult(
            removed=1, removed_bytes=4
        )
        self.begin_result: str | Exception = "op"
        self.date_fd = 0

    def pending(self):
        return self.pending_result

    def recover_with_result(self, operation: str):
        if isinstance(self.recover_result, Exception):
            raise self.recover_result
        return self.recover_result

    def begin(self, spec, hook=None, *, expected_members=None, expected_date=None):
        if isinstance(self.begin_result, Exception):
            raise self.begin_result
        return self.begin_result

    def _date(self, relative: str):
        fd = self.date_fd
        return _Date(fd)


class _Date:
    def __init__(self, fd: int) -> None:
        self._fd = fd

    def __enter__(self):
        return self._fd, []

    def __exit__(self, *args) -> bool:
        return False


class _Metrics:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int, dict[str, str]]] = []

    def increment_counter(self, name: str, value: int, labels: dict[str, str]) -> None:
        self.calls.append((name, value, labels))


def _abs(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _touch(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _viewed_fd(path: Path) -> int | None:
    parts = path.parts
    if len(parts) < 4 or parts[-2] != "fd" or parts[-3] not in {"self", "dev"}:
        return None
    try:
        return int(parts[-1])
    except ValueError:
        return None


def _patch_fd_view(monkeypatch: pytest.MonkeyPatch, bridge: DirFdBridge) -> None:
    real_stat = pathlib.Path.stat

    def patched(self: Path, *, follow_symlinks: bool = True):
        viewed = _viewed_fd(self)
        if viewed is not None:
            return bridge.fstat(viewed)
        return real_stat(self, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(pathlib.Path, "stat", patched)


def _arm(monkeypatch: pytest.MonkeyPatch, *modules: types.ModuleType) -> DirFdBridge:
    bridge = DirFdBridge()
    chosen = modules or (cleanup_posix, cleanup_core, support)
    for module in chosen:
        monkeypatch.setattr(module, "os", bridge)
    for module in (cleanup_posix, cleanup_core, support):
        monkeypatch.setattr(
            module, "destructive_cleanup_supported", lambda *_a, **_k: True
        )
    # bronze_tree_lock binds platform + volume xattr through cleanup_core names.
    monkeypatch.setattr(cleanup_core, "_platform_cleanup_supported", lambda: True)
    monkeypatch.setattr(
        cleanup_core, "_directory_xattr_supported", lambda *_a, **_k: True
    )
    _patch_fd_view(monkeypatch, bridge)
    return bridge


def _install_fcntl(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    module = types.ModuleType("fcntl")
    module.flock = lambda fd, operation: None
    module.LOCK_EX = 1
    module.LOCK_SH = 2
    monkeypatch.setitem(sys.modules, "fcntl", module)
    return module


def _leftovers(root: Path) -> list[str]:
    return sorted(
        path.name for path in root.iterdir() if path.name.startswith(".bronze-cleanup-")
    )


def _owned_tree(root: Path, *, flat: bool) -> Path:
    date_dir = root / _DATE if flat else root / "prov" / "ent" / _DATE
    date_dir.mkdir(parents=True)
    payload = date_dir / f"batch_{_DATE}_{_BATCH}.jsonl.zst"
    payload.write_bytes(b"payload")
    (date_dir / f"{payload.name}.meta.json").write_bytes(b"meta")
    return date_dir


def _spec(**overrides) -> GroupSpec:
    values = {
        "provider": "prov",
        "entity": "ent",
        "date": _DATE,
        "batch_id": _BATCH,
        "cutoff": _CUTOFF,
        "flat_structure": False,
    }
    values.update(overrides)
    return GroupSpec(**values)


def _member() -> dict[str, object]:
    return {"dev": 1, "ino": 2, "size": 3, "sha256": _DIGEST}


_OPERATION_SEQ = 0


def _operation() -> str:
    global _OPERATION_SEQ
    _OPERATION_SEQ += 1
    return f"{_OPERATION_SEQ:032x}"


def _body(operation: str, **overrides) -> dict[str, object]:
    spec = _spec()
    body: dict[str, object] = {
        "schema": schema._SCHEMA_VERSION,
        "operation_id": operation,
        "state": "prepared",
        "scope": {
            "provider": spec.provider,
            "entity": spec.entity,
            "date": spec.date,
            "batch_id": spec.batch_id,
            "cutoff": spec.cutoff,
            "flat_structure": spec.flat_structure,
        },
        "relative_date": spec.relative_date().as_posix(),
        "root": [1, 2],
        "chain": [[1, 2]],
        "names": spec.names(),
        "members": {"payload": _member(), "sidecar": _member()},
        "staged": [],
        "removed": [],
        "stage": None,
    }
    body.update(overrides)
    return body


def _cleanup(journal: _Journal, root: Path, *, flat: bool = False):
    obj = object.__new__(BronzeGroupCleanup)
    skips: list[tuple[str, str]] = []
    obj.journal = journal
    obj.root = root
    obj.cutoff = _CUTOFF
    obj.flat = flat
    obj.on_skip = lambda path, reason: skips.append((path, reason))
    obj.skips = skips
    return obj


def _plan_for(root: Path, path: Path):
    identity = path.stat()
    candidate = planner._CleanupCandidate(path, identity)
    return planner._CleanupDatePlan(root, identity, [candidate], True)


def _marker(root: Path, suffix: str, payload: bytes) -> Path:
    path = root / f".bronze-cleanup-done-{suffix}"
    path.write_bytes(payload)
    return path


def _origin(relative: str, dev: int, ino: int) -> bytes:
    return json.dumps({"relative": relative, "dev": dev, "ino": ino}).encode()


# --- posix / core destructive paths -----------------------------------------


def test_safe_unlink_and_rmdir_retire_stage(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf", "gone")
    folder = root / "empty"
    folder.mkdir()
    root_fd = bridge.bind_dir(root)
    assert cleanup_posix.safe_unlink(leaf, root, root, root_fd=root_fd) is True
    assert cleanup_posix.safe_rmdir(folder, root, root, root_fd=root_fd) is True
    assert not leaf.exists()
    assert not folder.exists()
    assert _leftovers(root) == []


def test_safe_unlink_opens_root_when_fd_missing(tmp_path: Path, monkeypatch) -> None:
    _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    assert cleanup_posix.safe_unlink(leaf, root, root) is True
    assert not leaf.exists()
    assert _leftovers(root) == []


def test_unlink_rejects_link_directory_identity_and_missing(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    other = _touch(root / "other")
    folder = root / "folder"
    folder.mkdir()
    root_fd = bridge.bind_dir(root)
    monkeypatch.setattr(cleanup_posix, "stat_is_link_or_reparse", lambda _st: True)
    assert cleanup_posix.safe_unlink(leaf, root, root, root_fd=root_fd) is False
    monkeypatch.setattr(cleanup_posix, "stat_is_link_or_reparse", lambda _st: False)
    assert cleanup_posix.safe_unlink(folder, root, root, root_fd=root_fd) is False
    assert (
        cleanup_posix.safe_unlink(leaf, root, root, other.stat(), root_fd=root_fd)
        is False
    )
    assert (
        cleanup_posix.safe_unlink(root / "missing", root, root, root_fd=root_fd)
        is False
    )
    assert leaf.exists()
    assert folder.exists()


def test_unlink_rejects_escape_and_parent_segment(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path / "root")
    root.mkdir()
    outside = _touch(tmp_path / "outside")
    leaf = _touch(root / "leaf")
    root_fd = bridge.bind_dir(root)
    assert cleanup_posix.safe_unlink(outside, root, root, root_fd=root_fd) is False

    def hooked(path: str) -> str:
        absolute = os.path.abspath(path)
        return str(Path(absolute).parent / "gap" / ".." / Path(absolute).name)

    bridge.abspath_hook = hooked
    assert cleanup_posix.safe_unlink(leaf, root, root, root_fd=root_fd) is False
    assert leaf.exists()
    assert outside.exists()


def test_unlink_returns_false_when_chain_or_stat_breaks(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "sub" / "leaf")
    other = _touch(root / "other")
    root_fd = bridge.bind_dir(root)

    def lie(fd: int, current):
        directory = bridge._dirs.get(fd)
        if directory is not None and directory == root:
            return other.stat()
        return current

    bridge.fstat_hook = lie
    assert cleanup_posix.safe_unlink(leaf, root, root, root_fd=root_fd) is False
    bridge.fstat_hook = None
    bridge.stat_error = lambda resolved: resolved.name == "sub"
    assert cleanup_posix.safe_unlink(leaf, root, root, root_fd=root_fd) is False
    assert leaf.exists()


def test_unlink_propagates_rename_failure(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    bridge.rename_error = lambda _src, _dst: errno.EACCES
    with pytest.raises(OSError):
        cleanup_posix.safe_unlink(leaf, root, root, root_fd=bridge.bind_dir(root))
    assert leaf.exists()


def test_rmdir_restores_when_directory_stays_busy(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    folder = root / "leaf"
    folder.mkdir()
    bridge.rmdir_error = lambda resolved: (
        errno.ENOTEMPTY if resolved.name == "leaf" else 0
    )
    assert (
        cleanup_posix.safe_rmdir(folder, root, root, root_fd=bridge.bind_dir(root))
        is False
    )
    assert folder.is_dir()
    assert _leftovers(root) == []


def test_rmdir_propagates_unexpected_removal_error(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    folder = root / "leaf"
    folder.mkdir()
    bridge.rmdir_error = lambda resolved: errno.EIO if resolved.name == "leaf" else 0
    with pytest.raises(OSError):
        cleanup_posix.safe_rmdir(folder, root, root, root_fd=bridge.bind_dir(root))
    assert folder.is_dir()


def test_private_stage_rejects_oversize_and_short_write(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    identity = _touch(root / "leaf").stat()
    root_fd = bridge.bind_dir(root)
    with pytest.raises(OSError, match="journal limit"):
        with cleanup_posix._private_stage(root_fd, Path("p" * 5000), identity):
            pass
    bridge.write_override = lambda _fd, _data: 0
    with pytest.raises(OSError, match="no progress"):
        with cleanup_posix._private_stage(root_fd, Path("leaf"), identity):
            pass
    assert _leftovers(root) == []


def test_private_stage_rmdirs_when_open_fails(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    identity = _touch(root / "leaf").stat()

    def fail_open(path, flags, _dir_fd) -> bool:
        text = str(path)
        return ".bronze-cleanup-stage-" in text and not flags & os.O_CREAT

    bridge.fail_open = fail_open
    with pytest.raises(OSError):
        with cleanup_posix._private_stage(
            bridge.bind_dir(root), Path("leaf"), identity
        ):
            pass
    assert _leftovers(root) == []


def test_private_stage_keeps_incomplete_directory(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    identity = _touch(root / "leaf").stat()
    with pytest.raises(RuntimeError, match="stop"):
        with cleanup_posix._private_stage(
            bridge.bind_dir(root), Path("leaf"), identity
        ):
            raise RuntimeError("stop")
    assert any(name.startswith(".bronze-cleanup-stage-") for name in _leftovers(root))


def test_stage_error_is_reported_or_raised(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    seen: list[OSError] = []
    bridge.unlink_error = lambda resolved: (
        errno.EIO if resolved.name.startswith(".bronze-cleanup-done-") else 0
    )
    assert (
        cleanup_posix.safe_unlink(
            leaf,
            root,
            root,
            on_stage_error=lambda _name, exc: seen.append(exc),
            root_fd=bridge.bind_dir(root),
        )
        is True
    )
    assert seen
    assert not leaf.exists()
    leaf = _touch(root / "leaf")
    with pytest.raises(OSError):
        cleanup_posix.safe_unlink(leaf, root, root, root_fd=bridge.bind_dir(root))


def test_post_rename_identity_mismatch_restores_file(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf", "keep")
    other = _touch(root / "other")
    bridge.lie_stat = other.stat()
    bridge.stat_lie = lambda resolved: ".bronze-cleanup-stage-" in resolved.parent.name
    assert (
        cleanup_posix.safe_unlink(leaf, root, root, root_fd=bridge.bind_dir(root))
        is False
    )
    assert leaf.read_text(encoding="utf-8") == "keep"
    assert _leftovers(root) == []


def test_restore_staged_occupied_and_free(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    parent = _touch(root / "leaf", "parent")
    stage = root / "stage"
    stage.mkdir()
    root_fd = bridge.bind_dir(root)
    stage_fd = bridge.bind_dir(stage)
    cleanup_posix._restore_staged("leaf", stage_fd, root_fd)
    assert parent.read_text(encoding="utf-8") == "parent"
    parent.unlink()
    _touch(stage / "leaf", "staged")
    cleanup_posix._restore_staged("leaf", stage_fd, root_fd)
    assert (root / "leaf").read_text(encoding="utf-8") == "staged"


def test_recover_completed_marker_shapes(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    root_fd = bridge.bind_dir(root)
    rejected = root / ".bronze-cleanup-done-zz"
    rejected.write_text("x", encoding="utf-8")
    with pytest.raises(OSError, match="Invalid"):
        cleanup_posix._recover_completed_stages(root_fd)
    rejected.unlink()
    suffix = "ab" * 16
    marker = _marker(root, suffix, b"not-json")
    with pytest.raises(OSError, match="invalid origin"):
        cleanup_posix._recover_completed_stages(root_fd)
    marker.write_bytes(b"x" * 4097)
    with pytest.raises(OSError, match="oversized"):
        cleanup_posix._recover_completed_stages(root_fd)
    marker.unlink()
    (root / f".bronze-cleanup-done-{suffix}").mkdir()
    with pytest.raises(OSError, match="non-file"):
        cleanup_posix._recover_completed_stages(root_fd)


def test_recover_completed_removes_empty_stage_and_bare_marker(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    suffix = "cd" * 16
    stage = root / f".bronze-cleanup-stage-{suffix}"
    stage.mkdir()
    _marker(root, suffix, _origin("leaf", 1, 2))
    cleanup_posix._recover_completed_stages(bridge.bind_dir(root))
    assert not stage.exists()
    assert _leftovers(root) == []
    _marker(root, suffix, _origin("leaf", 1, 2))
    cleanup_posix._recover_completed_stages(bridge.bind_dir(root))
    assert _leftovers(root) == []


def test_recover_completed_rejects_nonempty_stage(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    suffix = "ef" * 16
    stage = root / f".bronze-cleanup-stage-{suffix}"
    _touch(stage / "leaf")
    _marker(root, suffix, _origin("leaf", 1, 2))
    with pytest.raises(OSError, match="not empty"):
        cleanup_posix._recover_completed_stages(bridge.bind_dir(root))


def test_recover_stages_renames_back_and_drops_finished(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    (root / "sub").mkdir()
    stage = root / ".bronze-cleanup-stage-restore"
    staged = _touch(stage / "leaf", "back")
    st = staged.stat()
    (stage / "origin.json").write_bytes(_origin("sub/leaf", st.st_dev, st.st_ino))
    cleanup_posix._recover_stages(bridge.bind_dir(root), root)
    assert (root / "sub" / "leaf").read_text(encoding="utf-8") == "back"
    assert not stage.exists()

    finished = root / ".bronze-cleanup-stage-finished"
    finished.mkdir()
    (finished / "origin.json").write_bytes(_origin("sub/gone", 1, 2))
    cleanup_posix._recover_stages(bridge.bind_dir(root), root)
    assert not finished.exists()
    assert (root / "sub" / "leaf").is_file()


def test_recover_stages_rejects_changed_or_occupied_origin(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    (root / "sub").mkdir()
    stage = root / ".bronze-cleanup-stage-bad"
    staged = _touch(stage / "leaf")
    (stage / "origin.json").write_bytes(
        _origin("sub/leaf", staged.stat().st_dev, staged.stat().st_ino + 1)
    )
    with pytest.raises(OSError, match="identity"):
        cleanup_posix._recover_stages(bridge.bind_dir(root), root)
    _touch(root / "sub" / "leaf", "occupied")
    (stage / "origin.json").write_bytes(
        _origin("sub/leaf", staged.stat().st_dev, staged.stat().st_ino)
    )
    with pytest.raises(OSError, match="occupied"):
        cleanup_posix._recover_stages(bridge.bind_dir(root), root)


def test_missing_journal_and_bad_origin_records(tmp_path: Path, monkeypatch) -> None:
    bridge = _arm(monkeypatch)
    root = _abs(tmp_path)
    stage = root / ".bronze-cleanup-stage-empty"
    stage.mkdir()
    with pytest.raises(OSError, match="no origin"):
        cleanup_posix._recover_stages(bridge.bind_dir(root), root)
    (stage / "origin.json").mkdir()
    with pytest.raises(OSError, match="non-file"):
        cleanup_posix._load_stage_origin(bridge.bind_dir(stage), stage.name)
    record = stage / "origin.json"
    if record.is_dir():
        record.rmdir()
    record.write_bytes(b"{}")
    with pytest.raises(OSError, match="invalid origin"):
        cleanup_posix._parse_stage_origin(b"{", stage.name)
    with pytest.raises(OSError, match="invalid origin"):
        cleanup_posix._parse_stage_origin(_origin("a/../b", 1, 2), stage.name)
    with pytest.raises(OSError, match="invalid origin"):
        cleanup_posix._parse_stage_origin(
            json.dumps({"relative": "leaf", "dev": "1", "ino": 2}).encode(),
            stage.name,
        )


def test_anchored_parent_requires_destructive_support(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cleanup_posix, "destructive_cleanup_supported", lambda *_a, **_k: False
    )
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    with pytest.raises(NotImplementedError):
        with cleanup_posix._anchored_parent(leaf, root, root):
            pass


def test_core_fd_view_and_destructive_gate(tmp_path: Path, monkeypatch) -> None:
    root = _abs(tmp_path)
    assert BronzeRootLease(root, None).writer_path == root
    bridge = DirFdBridge()
    monkeypatch.setattr(cleanup_core, "os", bridge)
    fd = bridge.bind_dir(root)
    with pytest.raises(NotImplementedError):
        _ = BronzeRootLease(root, fd).writer_path
    _patch_fd_view(monkeypatch, bridge)
    viewed = BronzeRootLease(root, fd).writer_path
    assert viewed.parts[-1] == str(fd)
    opened, opened_fd = cleanup_core.open_bronze_root_no_follow(root)
    assert opened == root
    bridge.close(opened_fd)
    monkeypatch.setattr(cleanup_core, "_ANCHORED_OPS", True)
    bridge.name = "posix"
    monkeypatch.delitem(sys.modules, "fcntl", raising=False)
    monkeypatch.setattr(sys, "meta_path", [_BlockFcntl(), *sys.meta_path])
    assert cleanup_core.destructive_cleanup_supported() is False


def test_destructive_gate_flock_and_fd_view(tmp_path: Path, monkeypatch) -> None:
    _ = tmp_path
    bridge = DirFdBridge()
    bridge.name = "posix"
    monkeypatch.setattr(cleanup_core, "os", bridge)
    monkeypatch.setattr(cleanup_core, "_ANCHORED_OPS", True)
    monkeypatch.setattr(cleanup_core, "_directory_xattr_supported", lambda: True)
    bare = types.ModuleType("fcntl")
    monkeypatch.setitem(sys.modules, "fcntl", bare)
    assert cleanup_core.destructive_cleanup_supported() is False
    _install_fcntl(monkeypatch)
    assert cleanup_core.destructive_cleanup_supported() is False
    _patch_fd_view(monkeypatch, bridge)
    assert cleanup_core.destructive_cleanup_supported() is True
    monkeypatch.setattr(cleanup_core, "_directory_xattr_supported", lambda: False)
    assert cleanup_core.destructive_cleanup_supported() is False


def test_pending_group_operation_and_entry_classification(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = DirFdBridge()
    monkeypatch.setattr(cleanup_core, "os", bridge)
    root = _abs(tmp_path)
    root_fd = bridge.bind_dir(root)
    assert cleanup_core._pending_group_operation(root_fd) is False
    (root / ".bronze-group-journals").mkdir()
    assert cleanup_core._pending_group_operation(root_fd) is False
    _touch(root / ".bronze-group-journals" / "row")
    assert cleanup_core._pending_group_operation(root_fd) is True
    (root / ".bronze-group-stage-1").mkdir()
    assert cleanup_core._pending_group_operation(root_fd) is True
    assert cleanup_core.valid_bronze_scope_name("ab_1") is True
    assert cleanup_core.valid_bronze_scope_name("") is False
    assert cleanup_core.valid_bronze_scope_name("a.b") is False

    class _Link:
        def is_symlink(self) -> bool:
            return True

    class _Broken:
        def is_symlink(self) -> bool:
            return False

        def stat(self, follow_symlinks: bool = False):
            raise OSError("stat")

    assert cleanup_core._entry_is_link_or_reparse(_Link()) is True
    assert cleanup_core._entry_is_link_or_reparse(_Broken()) is True
    link_stat = SimpleNamespace(
        st_mode=os.stat(root).st_mode | 0o120000, st_file_attributes=0
    )
    # Mode bits from a real directory are not a symlink. Build S_IFLNK directly.
    link_stat = SimpleNamespace(st_mode=0o120000, st_file_attributes=0)
    assert cleanup_core.stat_is_link_or_reparse(link_stat) is True
    reparse = SimpleNamespace(st_mode=0o100644, st_file_attributes=0x400)
    assert cleanup_core.stat_is_link_or_reparse(reparse) is True


def test_writer_scope_skips_reserved_journal_without_retained_counter(
    tmp_path: Path,
) -> None:
    root = _abs(tmp_path)
    (root / ".bronze-group-journals").mkdir()
    (root / "chembl").mkdir()
    skips: list[tuple[str, str]] = []

    def on_skip(path: str, reason: str) -> None:
        skips.append((path, reason))

    children = support.iter_writer_scope_dirs(root, on_skip=on_skip)
    assert [child.name for child in children] == ["chembl"]
    assert any(reason == "reserved_maintenance" for _path, reason in skips)
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    mixin = type(
        "_SkipMixin",
        (),
        {
            "_log_cleanup_skip": staticmethod(lambda *_a, **_k: None),
            "_record_cleanup_discovery_skip": (
                read_cleanup.BronzeWriterReadCleanupMixin._record_cleanup_discovery_skip
            ),
        },
    )()
    for _path, reason in skips:
        mixin._record_cleanup_discovery_skip(stats, _path, reason)
    assert stats["directories_skipped"] == 0


def test_support_names_dates_and_nondestructive_candidates(tmp_path: Path) -> None:
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    assert support.date_dir_name_is_older(_DATE, _CUTOFF) is True
    assert support.date_dir_name_is_older("not-a-date", _CUTOFF) is False
    assert support.date_dir_name_is_older("2020-1-1", _CUTOFF) is False
    payload = f"batch_{_DATE}_{_BATCH}.jsonl.zst"
    assert support.is_owned_artifact(payload, date_name=_DATE) is True
    assert support.is_owned_artifact("notes.txt") is False
    with pytest.raises(ValueError):
        support.validate_scope_filter("a.b", "provider")
    support.validate_scope_filter(None, "provider")
    assert support.candidate_is_safe(root / "missing", root, root, leaf.stat()) is False
    outside = _touch(tmp_path.parent / "outside-bronze-cleanup")
    try:
        assert support.candidate_is_safe(outside, root, root, outside.stat()) is False
    finally:
        outside.unlink()


def test_support_tree_walk_and_flat_filter(tmp_path: Path) -> None:
    root = _abs(tmp_path)
    date_dir = root / "prov" / "ent" / _DATE
    date_dir.mkdir(parents=True)
    _touch(root / "prov" / "notes.txt")
    (root / "prov" / "bad.name").mkdir()
    skips: list[tuple[str, str]] = []
    found = support.find_old_date_dirs(
        root,
        flat_structure=False,
        cutoff_str=_CUTOFF,
        on_skip=lambda path, reason: skips.append((path, reason)),
    )
    assert any(path.name == _DATE for path in found)
    assert skips
    flat_root = _abs(tmp_path / "flat")
    (flat_root / _DATE).mkdir(parents=True)
    called: list[int] = []
    assert (
        support.find_old_date_dirs(
            flat_root,
            flat_structure=True,
            cutoff_str=_CUTOFF,
            provider="prov",
            on_flat_filter=lambda: called.append(1),
        )
        == []
    )
    assert called == [1]
    assert (
        support.find_old_date_dirs(
            tmp_path / "absent", flat_structure=False, cutoff_str=_CUTOFF
        )
        == []
    )
    assert (
        support.safe_named_child_dir(root, "missing", root, on_skip=lambda *_a: None)
        is None
    )


def test_bronze_tree_lock_success_pending_and_directory_lock(
    tmp_path: Path, monkeypatch
) -> None:
    bridge = _arm(monkeypatch)
    _install_fcntl(monkeypatch)
    root = _abs(tmp_path)
    with support.bronze_tree_lock(root, exclusive=True) as lease:
        assert lease.fd is not None
        assert lease.writer_path.parts[-1] == str(lease.fd)
    (root / ".bronze-group-stage-1").mkdir()
    with pytest.raises(OSError, match="group recovery"):
        with support.bronze_tree_lock(root, exclusive=True):
            pass
    with support.bronze_tree_lock(
        root, exclusive=True, allow_group_recovery=True
    ) as lease:
        assert lease.fd is not None
    (root / ".bronze-group-stage-1").rmdir()
    (root / ".bronze-cleanup-stage-open").mkdir()
    with pytest.raises(OSError, match="cleanup recovery"):
        with support.bronze_tree_lock(root, exclusive=False):
            pass
    lock = root / ".bronze-cleanup.lock"
    if lock.exists():
        lock.unlink()
    lock.mkdir()
    with pytest.raises(OSError, match="not a regular file"):
        with support.bronze_tree_lock(root, exclusive=True, allow_group_recovery=True):
            pass


def test_bronze_tree_lock_nondestructive_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cleanup_core, "_platform_cleanup_supported", lambda: False)
    monkeypatch.setattr(
        cleanup_core, "_directory_xattr_supported", lambda *_a, **_k: False
    )
    with pytest.raises(NotImplementedError):
        with support.bronze_tree_lock(tmp_path, exclusive=True):
            pass
    with support.bronze_tree_lock(tmp_path, exclusive=False) as lease:
        assert lease.fd is None
        assert lease.writer_path == tmp_path
    pending = tmp_path / "pending-markers"
    pending.mkdir()
    (pending / ".bronze-group-stage-1").mkdir()
    with pytest.raises(OSError, match="group recovery"):
        with support.bronze_tree_lock(pending, exclusive=False):
            pass
    legacy = tmp_path / "legacy-stage"
    legacy.mkdir()
    (legacy / ".bronze-cleanup-stage-1").mkdir()
    with pytest.raises(OSError, match="group recovery"):
        with support.bronze_tree_lock(legacy, exclusive=False):
            pass


def test_find_old_date_dirs_notifies_invalid_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Non-calendar partitions are retained and reported as invalid_date skips."""
    monkeypatch.setattr(support, "root_components_safe", lambda _path: True)
    entity = tmp_path / "prov" / "ent"
    entity.mkdir(parents=True)
    (entity / "2024-99-99").mkdir()
    (entity / "2020-01-01").mkdir()
    (entity / "2022-06-01").mkdir()
    skips: list[tuple[str, str]] = []
    found = support.find_old_date_dirs(
        tmp_path,
        flat_structure=False,
        cutoff_str="2021-01-01",
        on_skip=lambda path, reason: skips.append((path, reason)),
    )
    assert [path.name for path in found] == ["2020-01-01"]
    assert (entity / "2024-99-99").is_dir()
    assert (entity / "2022-06-01").is_dir()
    assert any(
        path.endswith("2024-99-99") and reason == "invalid_date"
        for path, reason in skips
    )


def test_dry_run_lock_does_not_create_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Read-only preview must not create ``.bronze-cleanup.lock``."""
    _arm(monkeypatch)
    _install_fcntl(monkeypatch)
    root = _abs(tmp_path)
    lock = root / ".bronze-cleanup.lock"
    assert not lock.exists()
    with support.bronze_tree_lock(root, exclusive=False, create_lock=False) as lease:
        assert lease.fd is not None
    assert not lock.exists()


def test_directory_xattr_cache_skips_repeat_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Argumentless capability checks reuse a warmed device cache."""
    cleanup_core._DIR_XATTR_BY_DEV.clear()
    probes: list[object] = []

    def fake_probe(probe_dir: str | None, cache_key: int) -> bool:
        probes.append((probe_dir, cache_key))
        cleanup_core._DIR_XATTR_BY_DEV[cache_key] = True
        return True

    monkeypatch.setattr(
        cleanup_core,
        "_xattr_apis",
        lambda: (lambda *_a, **_k: None, lambda *_a, **_k: b"1", None),
    )
    monkeypatch.setattr(cleanup_core, "_run_directory_xattr_probe", fake_probe)
    monkeypatch.setattr(cleanup_core, "_default_temp_device", lambda: 42)
    assert cleanup_core._directory_xattr_supported() is True
    assert cleanup_core._directory_xattr_supported() is True
    assert probes == [(None, 42)]
    cleanup_core._DIR_XATTR_BY_DEV.clear()


def test_xattr_cache_keeps_only_unsupported_errno(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only ENOTSUP and EOPNOTSUPP pin a negative directory-xattr cache."""
    cleanup_core._DIR_XATTR_BY_DEV.clear()
    real_open = os.open
    real_close = os.close
    setter_calls = 0
    pending: OSError | None = None

    def fake_open(path, flags, *args, **kwargs):
        # Directory removal reopens the same prefix with different flags.
        probe_flags = os.O_RDONLY | cleanup_core._O_DIRECTORY | cleanup_core._O_NOFOLLOW
        if (
            isinstance(path, str)
            and "bioetl-xattr-probe-" in path
            and flags == probe_flags
        ):
            return 7
        return real_open(path, flags, *args, **kwargs)

    def fake_close(fd, *args, **kwargs):
        if fd == 7:
            return None
        return real_close(fd, *args, **kwargs)

    def setter(*_args, **_kwargs) -> None:
        nonlocal setter_calls
        setter_calls += 1
        if pending is not None:
            raise pending

    monkeypatch.setattr(os, "open", fake_open)
    monkeypatch.setattr(os, "close", fake_close)
    monkeypatch.setattr(
        cleanup_core,
        "_xattr_apis",
        lambda: (setter, lambda *_args, **_kwargs: b"1", None),
    )
    monkeypatch.setattr(
        cleanup_core, "_xattr_probe_anchor", lambda _path: (42, str(tmp_path))
    )
    try:
        for code in (errno.EMFILE, errno.ENOSPC, errno.EACCES):
            pending = OSError(code, "transient xattr probe")
            before = setter_calls
            assert cleanup_core._directory_xattr_supported(tmp_path) is False
            assert setter_calls == before + 1
            assert 42 not in cleanup_core._DIR_XATTR_BY_DEV
        pending = OSError("transient xattr probe")
        assert pending.errno is None
        before = setter_calls
        assert cleanup_core._directory_xattr_supported(tmp_path) is False
        assert setter_calls == before + 1
        assert 42 not in cleanup_core._DIR_XATTR_BY_DEV
        pending = None
        assert cleanup_core._directory_xattr_supported(tmp_path) is True
        assert cleanup_core._DIR_XATTR_BY_DEV[42] is True
        warmed = setter_calls
        assert cleanup_core._directory_xattr_supported(tmp_path) is True
        assert setter_calls == warmed
        cleanup_core._DIR_XATTR_BY_DEV.clear()
        for code in (errno.ENOTSUP, errno.EOPNOTSUPP):
            pending = OSError(code, "xattr unsupported")
            before = setter_calls
            assert cleanup_core._directory_xattr_supported(tmp_path) is False
            assert cleanup_core._DIR_XATTR_BY_DEV[42] is False
            assert setter_calls == before + 1
            assert cleanup_core._directory_xattr_supported(tmp_path) is False
            assert setter_calls == before + 1
            cleanup_core._DIR_XATTR_BY_DEV.clear()
    finally:
        cleanup_core._DIR_XATTR_BY_DEV.clear()


def test_candidate_is_safe_uses_anchored_parent(tmp_path: Path, monkeypatch) -> None:
    _arm(monkeypatch)
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf")
    assert support.candidate_is_safe(leaf, root, root, leaf.lstat()) is True
    assert (
        support.candidate_is_safe(root / "missing", root, root, leaf.lstat()) is False
    )


# --- planner ----------------------------------------------------------------


def test_planner_keeps_owned_pair_nested_and_flat(tmp_path: Path) -> None:
    root = _abs(tmp_path / "nested")
    date_dir = _owned_tree(root, flat=False)
    nested = _Planner(False)
    plan = nested._plan_old_dir_files(date_dir, root, root)
    assert plan.removable is True
    assert len(plan.files) == 2
    stats = nested._empty_cleanup_stats()
    nested._record_cleanup_plan(stats, plan)
    assert stats["directories_planned"] == 1
    assert stats["files_planned"] == 2

    flat_root = _abs(tmp_path / "flat")
    flat_date = _owned_tree(flat_root, flat=True)
    flat = _Planner(True)
    flat_plan = flat._plan_old_dir_files(flat_date, flat_root, flat_root)
    assert flat_plan.removable is True
    assert len(flat_plan.files) == 2


def test_planner_skips_unknown_entries_and_conflicts(
    tmp_path: Path, monkeypatch
) -> None:
    root = _abs(tmp_path)
    date_dir = _owned_tree(root, flat=False)
    _touch(date_dir / "notes.txt", "nope")
    (date_dir / "nested").mkdir()
    actor = _Planner(False)
    plan = actor._plan_old_dir_files(date_dir, root, root)
    assert plan.removable is False
    assert plan.files_skipped >= 1
    assert plan.directories_skipped == 1
    stats = actor._empty_cleanup_stats()
    actor._record_cleanup_plan(stats, plan)
    assert stats["directories_skipped"] >= 1
    assert any(reason == "unknown_artifact" for _path, reason in actor.skips)
    assert any(reason == "unknown_directory" for _path, reason in actor.skips)

    def only_directories(*_args, directory: bool = False, **_kwargs) -> bool:
        return directory

    monkeypatch.setattr(planner, "candidate_is_safe", only_directories)
    conflicted = _Planner(False)
    conflict_plan = conflicted._plan_old_dir_files(date_dir, root, root)
    assert conflict_plan.files_conflicted >= 1
    assert any(reason == "candidate_conflict" for _path, reason in conflicted.skips)


def test_planner_failed_directory_scan_and_snapshot(
    tmp_path: Path, monkeypatch
) -> None:
    root = _abs(tmp_path)
    actor = _Planner(False)
    missing = actor._plan_old_dir_files(root / "missing", root, root)
    assert missing.directories_failed == 1
    date_dir = _owned_tree(root, flat=False)
    monkeypatch.setattr(planner, "scan_dir_entries", lambda _parent: None)
    failed = actor._plan_old_dir_files(date_dir, root, root)
    assert failed.directories_failed == 1
    monkeypatch.setattr(planner, "candidate_is_safe", lambda *_a, **_k: False)
    conflicted = actor._plan_old_dir_files(date_dir, root, root)
    assert conflicted.directories_conflicted == 1
    plan = planner._CleanupDatePlan(date_dir, None, [], False)
    identities = actor._snapshot_cleanup_identities(
        date_dir, [_BoomEntry("x", date_dir / "x")], plan
    )
    assert identities == {}
    assert plan.files_failed == 1


# --- preview / metrics ------------------------------------------------------


def test_preview_counts_old_and_sentinel_dates(tmp_path: Path) -> None:
    base = _abs(tmp_path)
    for name in (_DATE, "9999-12-31", "2099-01-01"):
        _touch(base / "prov" / "ent" / name / "row.txt")
    (base / "prov" / "ent" / "notes").mkdir()
    view = _Preview(base, False)
    counted = view.preview_cleanup()
    assert counted["exists"] is True
    assert counted["file_count"] == 3
    assert view.preview_cleanup(provider="prov", entity="ent")["file_count"] == 3
    assert view.preview_cleanup(provider="missing")["exists"] is False
    assert view._resolve_bronze_preview_root("prov", "ent") == base / "prov" / "ent"
    assert view._resolve_bronze_preview_root("prov", None) == base / "prov"
    flat = _Preview(base, True)
    assert flat._resolve_bronze_preview_root("prov", "ent") == base
    early = flat.preview_cleanup(provider="prov")
    assert early["file_count"] == 0
    assert early["exists"] is False


def test_preview_missing_invalid_and_unsafe_root(tmp_path: Path, monkeypatch) -> None:
    missing = _Preview(tmp_path / "absent", False).preview_cleanup()
    assert missing["exists"] is False
    assert missing["file_count"] == 0
    with pytest.raises(ValueError, match="provider"):
        _Preview(tmp_path, False).preview_cleanup(provider="a.b")
    base = _abs(tmp_path / "base")
    base.mkdir()
    monkeypatch.setattr(preview_mod, "root_components_safe", lambda _path: False)
    unsafe = _Preview(base, False).preview_cleanup()
    assert unsafe["exists"] is False
    assert unsafe["file_count"] == 0


def test_preview_scan_stat_and_budget_failures(tmp_path: Path, monkeypatch) -> None:
    base = _abs(tmp_path)
    _touch(base / "prov" / "ent" / _DATE / "row.txt")
    monkeypatch.setattr(
        preview_mod.os,
        "scandir",
        lambda _parent: (_ for _ in ()).throw(OSError("scan")),
    )
    assert _Preview(base, False).preview_cleanup()["file_count"] == 0
    monkeypatch.undo()
    monkeypatch.setattr(preview_mod, "candidate_is_safe", lambda *_a, **_k: False)
    assert _Preview(base, False).preview_cleanup()["file_count"] == 0
    assert (
        BronzeCleanupPreviewMixin._count_preview_date_files(
            base / "missing-date", base, base, [0]
        )
        == 0
    )
    parent = base / "prov"
    entry = _StatEntry("ent", parent / "ent", boom=True)

    def fake_scan(_parent):
        return _Scan([entry])

    monkeypatch.setattr(preview_mod.os, "scandir", fake_scan)
    assert (
        list(BronzeCleanupPreviewMixin._iter_bounded_dirs(parent, [0], scope=True))
        == []
    )
    monkeypatch.setattr(preview_mod, "_PREVIEW_MAX_ENTRIES", 0)
    with pytest.raises(ValueError, match="100000"):
        _Preview(base, False).preview_cleanup()


def test_metrics_emit_every_nonzero_outcome() -> None:
    port = _Metrics()
    result = {
        "files_skipped": 1,
        "bytes_skipped": 2,
        "files_conflicted": 3,
        "bytes_conflicted": 4,
        "files_failed": 5,
        "bytes_failed": 6,
        "directories_skipped": 7,
        "directories_conflicted": 8,
        "directories_failed": 9,
    }
    cleanup_metrics.emit_cleanup_outcome_metrics(port, result)
    assert len(port.calls) == 9
    assert {name for name, _value, _labels in port.calls} >= {
        "bioetl_bronze_cleanup_files_skipped_total",
        "bioetl_bronze_cleanup_directories_failed_total",
    }


# --- schema -----------------------------------------------------------------


def test_group_spec_names_and_relative_date() -> None:
    spec = _spec()
    names = spec.names()
    assert names["payload"] == f"batch_{_DATE}_{_BATCH}.jsonl.zst"
    assert spec.relative_date().as_posix() == f"prov/ent/{_DATE}"
    assert _spec(flat_structure=True).relative_date().as_posix() == _DATE
    with pytest.raises(ValueError, match="provider"):
        _spec(provider="a.b").names()
    with pytest.raises(ValueError, match="date"):
        _spec(date="2020-13-40").names()
    with pytest.raises(ValueError, match="older"):
        _spec(date=_CUTOFF, cutoff=_CUTOFF).names()
    with pytest.raises(ValueError, match="batch"):
        _spec(batch_id="not-a-uuid").names()
    with pytest.raises(ValueError, match="layout"):
        _spec(flat_structure=1).relative_date()


def test_schema_record_validation_success_and_rejections() -> None:
    operation = _operation()
    body = _body(operation)
    schema._validate_record_body(body, operation)
    decoded = schema._decode_record(schema._record_bytes(body), operation)
    assert decoded["operation_id"] == operation
    assert decoded["removed"] == []
    assert schema._unique_pairs([("a", 1)]) == {"a": 1}
    with pytest.raises(ValueError, match="duplicate"):
        schema._unique_pairs([("a", 1), ("a", 2)])
    with pytest.raises(GroupJournalConflict, match="size"):
        schema._record_bytes({"k": "x" * 20000})
    with pytest.raises(ValueError, match="schema"):
        schema._validate_record_body({"schema": 3}, operation)
    legacy = _body(operation, schema=3)
    legacy.pop("removed")
    schema._validate_record_body(legacy, operation)
    assert legacy["removed"] == []
    assert legacy["schema"] == 4
    rewritten = schema._decode_record(schema._record_bytes(legacy), operation)
    assert rewritten["schema"] == 4
    assert rewritten["removed"] == []
    accounted = _body(
        operation,
        staged=["payload", "sidecar"],
        removed=["payload"],
        stage={"dev": 1, "ino": 2, "token": operation},
    )
    schema._validate_record_body(accounted, operation)
    with pytest.raises(ValueError, match="removed before staged"):
        schema._validate_staged(
            _body(operation, staged=["payload"], removed=["sidecar"]),
            {"payload": _member(), "sidecar": _member()},
        )
    uppercase = "AA" * 16
    bad_op = _body(uppercase)
    with pytest.raises(ValueError, match="operation ID"):
        schema._validate_record_body(bad_op, uppercase)
    with pytest.raises(ValueError, match="schema"):
        schema._validate_record_body(_body(operation, schema=1), operation)
    mismatch = _body(operation, relative_date="nope")
    with pytest.raises(ValueError, match="writer path"):
        schema._validated_scope(mismatch)
    with pytest.raises(ValueError, match="scope"):
        schema._validated_scope(_body(operation, scope={"provider": "prov"}))


def test_schema_member_stage_and_chain_rejections() -> None:
    operation = _operation()
    with pytest.raises(ValueError, match="identity fields"):
        schema._validate_member_identity({"dev": 1})
    with pytest.raises(ValueError, match="identity values"):
        schema._validate_member_identity(
            {"dev": -1, "ino": 1, "size": 1, "sha256": _DIGEST}
        )
    with pytest.raises(ValueError, match="identity digest"):
        schema._validate_member_identity(
            {"dev": 1, "ino": 1, "size": 1, "sha256": "ZZ" * 32}
        )
    members = {"payload": _member()}
    with pytest.raises(ValueError, match="members"):
        schema._validate_members(
            _body(operation, members={}),
            schema._spec().names() if False else _spec().names(),
        )
    body = _body(operation, members=members, staged=["sidecar"])
    with pytest.raises(ValueError, match="staged"):
        schema._validate_staged(body, members)
    body = _body(
        operation,
        state="completed",
        members={"payload": _member(), "sidecar": _member()},
        staged=["payload"],
        stage={"dev": 1, "ino": 2, "token": _operation()},
    )
    with pytest.raises(ValueError, match="incomplete"):
        schema._validate_staged(body, body["members"])
    with pytest.raises(ValueError, match="root chain"):
        schema._validate_chain(_body(operation, chain=[]))
    with pytest.raises(ValueError, match="directory identity"):
        schema._validate_chain(_body(operation, root=[-1, 1], chain=[[-1, 1]]))
    with pytest.raises(ValueError, match="unassociated"):
        schema._validate_stage(_body(operation, staged=["payload"]))
    with pytest.raises(ValueError, match="stage association"):
        schema._validate_stage(_body(operation, stage={"dev": 1}))
    with pytest.raises(GroupJournalConflict, match="invalid"):
        schema._decode_record(b"", operation)
    with pytest.raises(GroupJournalConflict, match="invalid"):
        schema._decode_record(b"{}", operation)


def test_operation_id_uid_digest_and_association(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(GroupJournalConflict, match="operation"):
        schema._require_operation_id("AA" * 16)
    schema._require_operation_id(_operation())
    monkeypatch.delattr(schema.os, "geteuid", raising=False)
    with pytest.raises(NotImplementedError):
        schema._effective_uid()
    assert schema._optional_copy_digest_valid(None) is True
    assert schema._optional_copy_digest_valid(_DIGEST) is True
    assert schema._optional_copy_digest_valid("nope") is False
    spec = _spec()
    members = {"payload": _member(), "copy": _member()}
    metadata = {
        "provider": spec.provider,
        "entity": spec.entity,
        "batch_id": spec.batch_id,
        "cleanup_association": {
            "schema": 1,
            "payload_sha256": _DIGEST,
            "copy_sha256": _DIGEST,
        },
    }
    schema._validate_association(metadata, spec, members)
    metadata["provider"] = "other"
    with pytest.raises(GroupJournalConflict, match="unassociated"):
        schema._validate_association(metadata, spec, members)
    failure = GroupJournalFailure("op", 1, "unlink", 2, 3, 4)
    assert failure.removed == 1
    assert failure.phase == "unlink"
    assert failure.possibly_unlinked_bytes == 4
    assert "durably_removed=1" in str(failure)


def test_schema_member_io(tmp_path: Path, monkeypatch) -> None:
    bridge = DirFdBridge()
    monkeypatch.setattr(schema, "os", bridge)
    bridge.geteuid = lambda: 4
    assert schema._effective_uid() == 4
    root = _abs(tmp_path)
    leaf = _touch(root / "leaf", "payload-bytes")
    parent = bridge.bind_dir(root)
    found = schema._fingerprint(parent, "leaf")
    assert found["size"] == leaf.stat().st_size
    assert len(found["sha256"]) == 64
    assert schema._exists(parent, "leaf") is True
    assert schema._exists(parent, "missing") is False
    assert schema._identity(parent)[0] == root.stat().st_dev
    out = bridge.open("out", os.O_WRONLY | os.O_CREAT, dir_fd=parent)
    schema._write_all(out, b"abc")
    bridge.close(out)
    assert (root / "out").read_bytes() == b"abc"
    out = bridge.open("out", os.O_WRONLY | os.O_CREAT, dir_fd=parent)
    bridge.write_override = lambda _fd, _data: 0
    with pytest.raises(OSError, match="short"):
        schema._write_all(out, b"abc")
    bridge.close(out)

    def extra_link(_fd, current):
        return SimpleNamespace(
            st_mode=current.st_mode,
            st_nlink=2,
            st_dev=current.st_dev,
            st_ino=current.st_ino,
            st_size=current.st_size,
            st_mtime_ns=current.st_mtime_ns,
            st_ctime_ns=current.st_ctime_ns,
        )

    bridge.fstat_hook = extra_link
    with pytest.raises(GroupJournalConflict, match="regular"):
        schema._fingerprint(parent, "leaf")
    seen = {"n": 0}

    def changed(_fd, current):
        seen["n"] += 1
        size = current.st_size + (1 if seen["n"] > 1 else 0)
        return SimpleNamespace(
            st_mode=current.st_mode,
            st_nlink=1,
            st_dev=current.st_dev,
            st_ino=current.st_ino,
            st_size=size,
            st_mtime_ns=current.st_mtime_ns,
            st_ctime_ns=current.st_ctime_ns,
        )

    bridge.fstat_hook = changed
    with pytest.raises(GroupJournalConflict, match="changed"):
        schema._fingerprint(parent, "leaf")
    bridge.fstat_hook = None
    monkeypatch.setattr(schema, "stat_is_link_or_reparse", lambda _st: True)
    with pytest.raises(GroupJournalConflict, match="regular"):
        schema._open_regular_member(parent, "leaf")
    monkeypatch.setattr(schema, "stat_is_link_or_reparse", lambda _st: False)
    (root / "dir").mkdir()
    with pytest.raises(GroupJournalConflict, match="regular"):
        schema._open_regular_member(parent, "dir")
    bridge.eloop_names.add("leaf")
    with pytest.raises(GroupJournalConflict, match="regular"):
        schema._open_regular_member(parent, "leaf")
    bridge.eloop_names.clear()
    bridge.fail_open = lambda _path, _flags, _dir_fd: True
    with pytest.raises(OSError) as caught:
        schema._open_regular_member(parent, "leaf")
    assert not isinstance(caught.value, GroupJournalConflict)
    assert caught.value.errno != errno.ELOOP


# --- apply ------------------------------------------------------------------


def _apply_case(tmp_path: Path, monkeypatch, *, flat: bool):
    bridge = DirFdBridge()
    monkeypatch.setattr(apply_mod, "os", bridge)
    root = _abs(tmp_path)
    if flat:
        date_dir = root / _DATE
        relative_root = root
    else:
        date_dir = root / "prov" / "ent" / _DATE
        relative_root = root
    date_dir.mkdir(parents=True)
    group = f"batch_{_DATE}_{_BATCH}"
    payload = _touch(date_dir / f"{group}.jsonl.zst", "payload")
    journal = _Journal()
    journal.date_fd = bridge.bind_dir(date_dir)
    meta = {
        "provider": "prov",
        "entity": "ent",
    }
    (date_dir / f"{group}.jsonl.zst.meta.json").write_text(
        json.dumps(meta), encoding="utf-8"
    )
    actor = _cleanup(journal, relative_root, flat=flat)
    plan = _plan_for(date_dir, payload)
    return actor, plan, journal, date_dir


def test_apply_flat_and_nested_specs(tmp_path: Path, monkeypatch) -> None:
    actor, plan, journal, _date_dir = _apply_case(tmp_path, monkeypatch, flat=True)
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    actor.apply(plan, stats)
    assert stats["files_removed"] == 1
    assert journal.begin_result == "op"

    nested, nested_plan, _journal, _date_dir = _apply_case(
        tmp_path / "nested", monkeypatch, flat=False
    )
    nested_stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    nested.apply(nested_plan, nested_stats)
    assert nested_stats["files_removed"] == 1


def test_apply_rejects_bad_sidecars_and_begin_errors(
    tmp_path: Path, monkeypatch
) -> None:
    actor, plan, journal, date_dir = _apply_case(tmp_path, monkeypatch, flat=True)
    group = f"batch_{_DATE}_{_BATCH}"
    meta_path = date_dir / f"{group}.jsonl.zst.meta.json"
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    meta_path.write_text("[]", encoding="utf-8")
    actor.apply(plan, stats)
    assert stats["files_conflicted"] == 1
    meta_path.write_text(json.dumps({"provider": 1, "entity": "ent"}), encoding="utf-8")
    actor.apply(plan, stats)
    assert stats["files_conflicted"] == 2
    meta_path.write_bytes(b"x" * (schema._MAX_SIDECAR + 1))
    actor.apply(plan, stats)
    assert stats["files_conflicted"] == 3
    meta_path.write_text(
        json.dumps({"provider": "prov", "entity": "ent"}), encoding="utf-8"
    )
    journal.begin_result = GroupJournalConflict("bad")
    actor.apply(plan, stats)
    assert stats["files_conflicted"] == 4
    journal.begin_result = OSError("io")
    actor.apply(plan, stats)
    assert stats["files_failed"] == 1
    journal.begin_result = TypeError("type")
    actor.apply(plan, stats)
    assert stats["files_conflicted"] == 5


def test_apply_nonflat_relative_mismatch_is_conflict(
    tmp_path: Path, monkeypatch
) -> None:
    _bridge = DirFdBridge()
    monkeypatch.setattr(apply_mod, "os", _bridge)
    root = _abs(tmp_path)
    date_dir = root / "only" / _DATE
    payload = _touch(date_dir / f"batch_{_DATE}_{_BATCH}.jsonl.zst")
    actor = _cleanup(_Journal(), root, flat=False)
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    actor.apply(_plan_for(date_dir, payload), stats)
    assert stats["files_conflicted"] == 1
    assert actor.skips


def test_resume_scope_filters_and_recovery(tmp_path: Path) -> None:
    root = _abs(tmp_path)
    journal = _Journal()
    actor = _cleanup(journal, root, flat=False)
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    journal.pending_result = [("op", _spec(date=_CUTOFF), 2, 8)]
    assert actor.resume(stats, None, None) is False
    assert stats["directories_skipped"] == 1
    journal.pending_result = [("op", _spec(provider="other"), 2, 8)]
    assert actor.resume(stats, "prov", None) is False
    journal.pending_result = [("op", _spec(flat_structure=True), 2, 8)]
    assert actor.resume(stats, None, None) is False
    flat = _cleanup(journal, root, flat=True)
    journal.pending_result = [("op", _spec(), 2, 8)]
    flat_stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    assert flat.resume(flat_stats, "prov", None) is False
    journal.pending_result = [("op", _spec(), 2, 8)]
    journal.recover_result = GroupJournalConflict("conflict")
    ok_stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    assert actor.resume(ok_stats, "prov", "ent") is False
    assert ok_stats["files_conflicted"] == 2
    assert ok_stats["directories_conflicted"] == 1
    journal.recover_result = OSError("io")
    failed = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    assert actor.resume(failed, "prov", "ent") is False
    assert failed["files_failed"] == 2
    journal.recover_result = GroupRecoveryResult(removed=2, removed_bytes=8)
    done = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    assert actor.resume(done, "prov", "ent") is True
    assert done["files_removed"] == 2
    assert done["bytes_freed"] == 8

    def boom(self):
        raise OSError("pending")

    journal.pending = boom.__get__(journal, _Journal)
    pending = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    assert actor.resume(pending, None, None) is False
    assert pending["directories_conflicted"] == 1
    assert actor.skips[-1][1] == "invalid_pending_group"


@pytest.mark.parametrize(
    "exclusive,create_lock",
    [(False, False), (True, False), (True, True), (False, True)],
)
def test_lock_probes_target_volume_only_for_mutating_operations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exclusive: bool, create_lock: bool
) -> None:
    _arm(monkeypatch)
    _install_fcntl(monkeypatch)
    calls = []

    def unsupported(root):
        calls.append(root)
        return False

    monkeypatch.setattr(cleanup_core, "_directory_xattr_supported", unsupported)
    if exclusive:
        with pytest.raises(NotImplementedError):
            with support.bronze_tree_lock(
                tmp_path, exclusive=True, create_lock=create_lock
            ):
                pytest.fail("Unsupported destructive operation acquired a lease")
        assert list(tmp_path.iterdir()) == []
    else:
        with support.bronze_tree_lock(
            tmp_path, exclusive=False, create_lock=create_lock
        ) as lease:
            assert lease.fd is not None
        names = sorted(path.name for path in tmp_path.iterdir())
        assert names == ([".bronze-cleanup.lock"] if create_lock else [])
    assert calls == ([tmp_path] if exclusive else [])


def test_shared_writer_refuses_unreadable_root_listing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unreadable root listing refuses the shared writer with no mutation."""
    monkeypatch.setattr(cleanup_core, "_platform_cleanup_supported", lambda: False)
    sentinel = tmp_path / "sentinel.bin"
    sentinel.write_bytes(b"keep")
    real_iterdir = Path.iterdir

    def denied(self: Path):
        same = os.path.normcase(str(self.resolve())) == os.path.normcase(
            str(tmp_path.resolve())
        )
        if same:
            raise PermissionError(13, "listing denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", denied)
    with pytest.raises(PermissionError, match="listing denied"):
        with support.bronze_tree_lock(tmp_path, exclusive=False):
            pytest.fail("unreadable root acquired a shared lease")
    assert sentinel.read_bytes() == b"keep"
    assert not (tmp_path / ".bronze-cleanup.lock").exists()


def test_flat_journal_directory_is_reserved_maintenance(tmp_path: Path) -> None:
    """An empty flat-layout journal directory is reserved maintenance."""
    root = _abs(tmp_path)
    journal = root / ".bronze-group-journals"
    journal.mkdir()
    (root / _DATE).mkdir()
    skips: list[tuple[str, str]] = []
    found = support.find_old_date_dirs(
        root,
        flat_structure=True,
        cutoff_str=_CUTOFF,
        on_skip=lambda path, reason: skips.append((path, reason)),
    )
    assert [path.name for path in found] == [_DATE]
    assert [reason for _path, reason in skips] == ["reserved_maintenance"]
    assert journal.is_dir() and not any(journal.iterdir())
    stats = planner.BronzeCleanupPlannerMixin._empty_cleanup_stats()
    mixin = type(
        "_SkipMixin",
        (),
        {
            "_log_cleanup_skip": staticmethod(lambda *_a, **_k: None),
            "_record_cleanup_discovery_skip": (
                read_cleanup.BronzeWriterReadCleanupMixin._record_cleanup_discovery_skip
            ),
        },
    )()
    for path, reason in skips:
        mixin._record_cleanup_discovery_skip(stats, path, reason)
    assert stats["directories_skipped"] == 0
