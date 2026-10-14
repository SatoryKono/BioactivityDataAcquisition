"""POSIX capability and private-stage retirement regressions for Bronze cleanup."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.storage.bronze import cleanup_core, cleanup_posix
from bioetl.infrastructure.storage.bronze.cleanup_support import (
    bronze_tree_lock,
    destructive_cleanup_supported,
)

pytestmark = pytest.mark.integration
_APPLY_POSIX = pytest.mark.skipif(
    not destructive_cleanup_supported(),
    reason="POSIX anchored destructive capability required (Windows NOT_VERIFIED)",
)
ARTIFACT = "batch_2024-01-01_12345678-1234-5678-1234-567812345678.jsonl.zst"


@_APPLY_POSIX
def test_uninitialized_stage_is_removed_after_journal_sync_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / ARTIFACT
    target.write_bytes(b"retained")
    root_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    original_fsync = cleanup_posix.os.fsync
    failed = False

    def fail_first_sync(fd: int) -> None:
        nonlocal failed
        if not failed:
            failed = True
            raise OSError("injected journal sync failure")
        original_fsync(fd)

    monkeypatch.setattr(cleanup_posix.os, "fsync", fail_first_sync)
    try:
        with pytest.raises(OSError, match="injected journal sync failure"):
            with cleanup_posix._private_stage(root_fd, Path(ARTIFACT), target.lstat()):
                pytest.fail("uninitialized stage must not be yielded")
    finally:
        os.close(root_fd)
    assert target.read_bytes() == b"retained"
    assert not list(tmp_path.glob(".bronze-cleanup-stage-*"))
    with bronze_tree_lock(tmp_path, exclusive=True):
        assert target.read_bytes() == b"retained"


@_APPLY_POSIX
def test_fd_view_probe_refuses_missing_pseudo_fd_mount(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_stat = Path.stat

    def missing_fd_view(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if str(path).startswith(("/proc/self/fd/", "/dev/fd/")):
            raise FileNotFoundError("injected missing pseudo-fd mount")
        return original_stat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", missing_fd_view)
    assert not cleanup_core._fd_view_supported()
    assert not destructive_cleanup_supported()


@_APPLY_POSIX
def test_missing_fd_view_keeps_writes_available_but_refuses_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cleanup_core, "_fd_view_supported", lambda: False)
    assert not destructive_cleanup_supported()
    with bronze_tree_lock(tmp_path, exclusive=False) as lease:
        assert lease.fd is None
        assert lease.writer_path == tmp_path
    with pytest.raises(NotImplementedError, match="dir_fd/no-follow"):
        with bronze_tree_lock(tmp_path, exclusive=True):
            pytest.fail("destructive apply must refuse missing fd-view capability")


@_APPLY_POSIX
def test_fd_view_lost_after_probe_refuses_both_locks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_fd_view(_lease: cleanup_core.BronzeRootLease) -> Path:
        raise NotImplementedError("injected missing procfs fd view")

    monkeypatch.setattr(
        cleanup_core.BronzeRootLease, "writer_path", property(no_fd_view)
    )
    for exclusive in (False, True):
        with pytest.raises(NotImplementedError, match="injected missing procfs"):
            with bronze_tree_lock(tmp_path, exclusive=exclusive):
                pytest.fail("root fd without a view must never yield a path")


def test_stage_retirement_preserves_substituted_directory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Identity mismatch must prevent rmdir while retaining the completed marker."""
    stage_fd, root_fd = 101, 102
    owned = Mock(st_dev=1, st_ino=2)
    replacement = Mock(st_dev=1, st_ino=3)
    closed, removed, unlinked = Mock(), Mock(), Mock()
    monkeypatch.setattr(cleanup_posix.os, "listdir", lambda _fd: [])
    monkeypatch.setattr(cleanup_posix.os, "rename", Mock())
    monkeypatch.setattr(cleanup_posix.os, "fsync", Mock())
    monkeypatch.setattr(cleanup_posix.os, "fstat", lambda _fd: owned)
    monkeypatch.setattr(cleanup_posix.os, "stat", lambda *_args, **_kwargs: replacement)
    monkeypatch.setattr(cleanup_posix.os, "rmdir", removed)
    monkeypatch.setattr(cleanup_posix.os, "unlink", unlinked)
    monkeypatch.setattr(cleanup_posix.os, "close", closed)
    errors = Mock()
    cleanup_posix._finish_private_stage(
        root_fd, stage_fd, ".bronze-cleanup-stage-test", Path("date/member"), errors
    )
    removed.assert_not_called()
    unlinked.assert_not_called()
    closed.assert_called_once_with(stage_fd)
    errors.assert_called_once()
    assert "replaced before retirement" in str(errors.call_args.args[1])
