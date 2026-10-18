# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Fail-closed Bronze cleanup when listing, xattr, flock, or link checks cannot pass."""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from uuid import UUID

import pytest
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.infrastructure.storage.bronze import cleanup_core
from bioetl.infrastructure.storage.bronze.cleanup_support import bronze_tree_lock

from tests.integration.infrastructure.storage.test_bronze_writer_cleanup_safety import (
    ARTIFACT,
    CUTOFF,
    SIDECAR,
    _APPLY_POSIX,
    _POSIX_HANDLES,
    _REAL_SYMLINK,
    _date_dir,
    _make_writer,
    _sidecar,
    _write_pair,
)

pytestmark = pytest.mark.integration


def _tree_bytes(root: Path) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        found[path.relative_to(root).as_posix()] = path.read_bytes()
    return found


def _xattr_names(path: Path) -> tuple[str, ...]:
    listed = os.listxattr(os.fspath(path), follow_symlinks=False)
    return tuple(sorted(os.fsdecode(name) for name in listed))


_LOCK_HOLDER_SCRIPT = """
import os
import sys
import time
import fcntl

root, ready, release = sys.argv[1:]
fd = os.open(
    os.path.join(root, ".bronze-cleanup.lock"),
    os.O_RDWR | os.O_CREAT,
    0o600,
)
fcntl.flock(fd, fcntl.LOCK_EX)
os.close(os.open(ready, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
while not os.path.exists(release):
    time.sleep(0.02)
fcntl.flock(fd, fcntl.LOCK_UN)
os.close(fd)
"""

_LISTING_DENIED_SCRIPT = """
import ctypes
import os
import sys
from pathlib import Path


def drop_read_override() -> None:
    libc = ctypes.CDLL(None, use_errno=True)

    class Header(ctypes.Structure):
        _fields_ = [("version", ctypes.c_uint32), ("pid", ctypes.c_int)]

    class Data(ctypes.Structure):
        _fields_ = [
            ("effective", ctypes.c_uint32),
            ("permitted", ctypes.c_uint32),
            ("inheritable", ctypes.c_uint32),
        ]

    header = Header(0x20080522, 0)
    data = (Data * 2)()
    capget = libc.capget
    capset = libc.capset
    pointer = ctypes.POINTER(Data)
    capget.argtypes = [ctypes.POINTER(Header), pointer]
    capset.argtypes = [ctypes.POINTER(Header), pointer]
    capget.restype = ctypes.c_int
    capset.restype = ctypes.c_int
    view = ctypes.cast(data, pointer)
    if capget(ctypes.byref(header), view) != 0:
        return
    mask = 0xFFFFFFFF ^ 0x6
    for word in data:
        word.effective &= mask
        word.permitted &= mask
        word.inheritable &= mask
    capset(ctypes.byref(header), view)


def main() -> int:
    root = Path(sys.argv[1])
    result = Path(sys.argv[2])
    try:
        drop_read_override()
        os.chmod(root, 0o300)
        from bioetl.infrastructure.storage.bronze import cleanup_core
        from bioetl.infrastructure.storage.bronze import cleanup_support

        cleanup_core._platform_cleanup_supported = lambda: False
        try:
            with cleanup_support.bronze_tree_lock(root, exclusive=False):
                result.write_text("acquired", encoding="utf-8")
        except PermissionError:
            result.write_text("permission", encoding="utf-8")
        except Exception as exc:
            result.write_text(
                f"error:{type(exc).__name__}:{exc}", encoding="utf-8"
            )
    finally:
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""


def _worktree_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(Path(cleanup_core.__file__).resolve().parents[4])
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src if not current else src + os.pathsep + current
    return env


@_POSIX_HANDLES
def test_shared_writer_waits_when_xattr_probe_is_false(tmp_path: Path, monkeypatch):
    """Unavailable directory xattr still shares the exclusive flock."""
    import fcntl

    monkeypatch.setattr(
        cleanup_core, "_directory_xattr_supported", lambda *_a, **_k: False
    )
    root = tmp_path / "bronze"
    root.mkdir()
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    script = tmp_path / "hold_lock.py"
    script.write_text(_LOCK_HOLDER_SCRIPT, encoding="utf-8")
    log = tmp_path / "holder.log"
    payload = root / "payload.bin"
    acquired: dict[str, int | None] = {}
    errors: list[BaseException] = []

    def writer() -> None:
        try:
            with bronze_tree_lock(root, exclusive=False) as lease:
                acquired["fd"] = lease.fd
                payload.write_bytes(b"wrote")
        except BaseException as exc:
            errors.append(exc)

    handle = log.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(script), str(root), str(ready), str(release)],
        cwd=tmp_path,
        env=_worktree_env(),
        stdout=handle,
        stderr=subprocess.STDOUT,
    )
    thread = threading.Thread(target=writer, daemon=True)
    try:
        deadline = time.monotonic() + 5
        while not ready.exists():
            if proc.poll() is not None or time.monotonic() > deadline:
                raise AssertionError(log.read_text(encoding="utf-8"))
            time.sleep(0.02)
        thread.start()
        blocked_until = time.monotonic() + 1
        while time.monotonic() < blocked_until:
            assert not payload.exists()
            assert "fd" not in acquired
            assert thread.is_alive()
            time.sleep(0.05)
        probe = os.open(root / ".bronze-cleanup.lock", os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(probe, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(probe)
        release.write_bytes(b"")
        thread.join(5)
    finally:
        release.write_bytes(b"")
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        handle.close()
    assert proc.returncode == 0, log.read_text(encoding="utf-8")
    assert errors == []
    assert not thread.is_alive()
    assert acquired["fd"] is not None
    assert payload.read_bytes() == b"wrote"


@_REAL_SYMLINK
def test_unreadable_root_listing_blocks_shared_writer(tmp_path: Path) -> None:
    """A writable root whose listing is denied does not accept a shared writer."""
    root = tmp_path / "bronze"
    root.mkdir()
    sentinel = root / "sentinel.bin"
    sentinel.write_bytes(b"keep")
    script = tmp_path / "listing_denied.py"
    script.write_text(_LISTING_DENIED_SCRIPT, encoding="utf-8")
    result = tmp_path / "result.txt"
    completed = subprocess.run(
        [sys.executable, str(script), str(root), str(result)],
        cwd=tmp_path,
        env=_worktree_env(),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    os.chmod(root, 0o700)
    assert completed.returncode == 0, completed.stderr
    assert result.read_text(encoding="utf-8") == "permission"
    assert sentinel.read_bytes() == b"keep"
    assert not (root / ".bronze-cleanup.lock").exists()


@_POSIX_HANDLES
async def test_dry_run_preview_without_directory_xattr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Preview plans owned files without directory xattr or filesystem mutation."""
    probed: list[object] = []

    def forbidden(*_args: object, **_kwargs: object) -> bool:
        probed.append(object())
        raise AssertionError("directory xattr probe")

    monkeypatch.setattr(
        cleanup_core, "_directory_xattr_supported", lambda *_a, **_k: False
    )
    monkeypatch.setattr(cleanup_core, "_run_directory_xattr_probe", forbidden)
    cache = cleanup_core._DIR_XATTR_BY_DEV
    saved = dict(cache)
    cache.clear()
    try:
        writer = _make_writer(tmp_path, flat=True)
        old_dir = _date_dir(tmp_path)
        _write_pair(old_dir, b"payload")
        payload = old_dir / ARTIFACT
        sidecar = old_dir / SIDECAR
        before = _tree_bytes(tmp_path)
        xattrs = {
            path: _xattr_names(path) for path in (tmp_path, old_dir, payload, sidecar)
        }
        result = await writer.cleanup_old_files(CUTOFF, dry_run=True)
        assert result["files_planned"] == 2
        assert result["files_removed"] == 0
        assert result["directories_removed"] == 0
        assert payload.read_bytes() == b"payload"
        assert sidecar.read_bytes() == _sidecar(b"payload")
        assert _tree_bytes(tmp_path) == before
        assert not (tmp_path / ".bronze-cleanup.lock").exists()
        assert not (tmp_path / ".bronze-group-journals").exists()
        assert not list(tmp_path.glob("bioetl-xattr-probe-*"))
        assert probed == []
        assert {
            path: _xattr_names(path) for path in (tmp_path, old_dir, payload, sidecar)
        } == xattrs
        with pytest.raises(NotImplementedError):
            await writer.cleanup_old_files(CUTOFF)
        assert payload.read_bytes() == b"payload"
        assert sidecar.read_bytes() == _sidecar(b"payload")
        assert not (tmp_path / ".bronze-cleanup.lock").exists()
    finally:
        cache.clear()
        cache.update(saved)


@_REAL_SYMLINK
@pytest.mark.parametrize("placement", ["root", "ancestor"])
async def test_symlink_root_is_rejected_before_xattr_probe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, placement: str
) -> None:
    """A linked root or ancestor is refused before probe or temp creation."""
    assert cleanup_core._xattr_apis() is not None
    external = tmp_path / "external"
    external.mkdir()
    (external / "payload.bin").write_bytes(b"external")
    before = _tree_bytes(external)
    xattrs = _xattr_names(external / "payload.bin")
    if placement == "root":
        link = tmp_path / "bronze"
        os.symlink(external, link, target_is_directory=True)
        target = link
    else:
        link = tmp_path / "linked-parent"
        os.symlink(external, link, target_is_directory=True)
        target = link / "new-bronze"
    probed: list[object] = []

    def forbidden(*_args: object, **_kwargs: object) -> bool:
        probed.append(object())
        raise AssertionError("directory xattr probe")

    monkeypatch.setattr(cleanup_core, "_run_directory_xattr_probe", forbidden)
    cache = cleanup_core._DIR_XATTR_BY_DEV
    saved = dict(cache)
    try:
        cache[external.stat().st_dev] = True
        assert cleanup_core._directory_xattr_supported(target) is False
        assert probed == []
        with pytest.raises(OSError, match="symlink or reparse"):
            with bronze_tree_lock(target, exclusive=True):
                pytest.fail("linked root acquired an exclusive lease")
        with pytest.raises(OSError, match="symlink or reparse"):
            cleanup_core._require_unlinked_bronze_root(target / "new-bronze")
        if placement == "ancestor":
            with pytest.raises(OSError, match="symlink or reparse"):
                with bronze_tree_lock(target, exclusive=False, create_lock=False):
                    pytest.fail("ancestor link acquired a shared lease")
            with pytest.raises(OSError, match="symlink or reparse"):
                await _make_writer(target).write_bronze(
                    records=iter([b"{}\n"]),
                    provider="chembl",
                    entity="activity",
                    date=CUTOFF,
                    batch_id=BatchID(UUID(int=1)),
                    run_id=RunID(UUID(int=2)),
                    run_type=RunType.INCREMENTAL,
                    ingestion_ts=CUTOFF,
                )
        else:
            # A leaf alias may take a non-creating shared lease. That lease
            # must not authorize probe, lock creation, or a new directory.
            with bronze_tree_lock(target, exclusive=False, create_lock=False) as lease:
                assert lease.fd is not None
        assert _tree_bytes(external) == before
        assert _xattr_names(external / "payload.bin") == xattrs
        assert not list(external.glob("bioetl-xattr-probe-*"))
        assert not (external / "new-bronze").exists()
        assert not (external / ".bronze-cleanup.lock").exists()
    finally:
        cache.clear()
        cache.update(saved)


@_APPLY_POSIX
async def test_flat_cleanup_keeps_empty_journal_directory(tmp_path: Path) -> None:
    """Successful flat cleanup retains an empty journal dir and no skip."""
    writer = _make_writer(tmp_path, flat=True)
    old_dir = _date_dir(tmp_path)
    _write_pair(old_dir)
    journal = tmp_path / ".bronze-group-journals"
    journal.mkdir(mode=0o700)
    result = await writer.cleanup_old_files(CUTOFF)
    assert result["files_removed"] == 2
    assert result["directories_removed"] == 1
    assert result["directories_skipped"] == 0
    assert not old_dir.exists()
    assert journal.is_dir()
    assert not any(journal.iterdir())
