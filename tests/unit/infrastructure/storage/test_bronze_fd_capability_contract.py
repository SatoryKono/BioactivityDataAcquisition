"""Capability discovery cannot hide loss of the actual writer's pinned view."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.storage.bronze import cleanup_core

pytestmark = pytest.mark.unit


def test_lost_lease_view_cannot_reclassify_an_available_fd_capability(monkeypatch):
    inode = SimpleNamespace(st_dev=7, st_ino=11)
    closed = Mock()
    real_open = cleanup_core.os.open
    real_fstat = cleanup_core.os.fstat
    real_close = cleanup_core.os.close
    real_path_stat = Path.stat

    def open_root(path, *args, **kwargs):
        if path == "/":
            return 42
        return real_open(path, *args, **kwargs)

    def fstat_fd(fd):
        return inode if fd == 42 else real_fstat(fd)

    def close_fd(fd):
        if fd == 42:
            closed(fd)
            return
        real_close(fd)

    def stat_fd_view(path, *args, **kwargs):
        normalized_path = str(path).replace("\\", "/")
        if normalized_path in {"/proc/self/fd/42", "/dev/fd/42"}:
            return inode
        return real_path_stat(path, *args, **kwargs)

    monkeypatch.setattr(cleanup_core.os, "open", open_root)
    monkeypatch.setattr(cleanup_core.os, "fstat", fstat_fd)
    monkeypatch.setattr(cleanup_core.os, "close", close_fd)
    monkeypatch.setattr(Path, "stat", stat_fd_view)

    def lost_writer_view(lease):
        raise NotImplementedError("writer root view disappeared after probe")

    monkeypatch.setattr(
        cleanup_core.BronzeRootLease, "writer_path", property(lost_writer_view)
    )
    assert cleanup_core._fd_view_supported() is True
    closed.assert_called_once_with(42)
    with pytest.raises(NotImplementedError, match="disappeared after probe"):
        cleanup_core._shared_lease_after_pending_check(Path("unused"), 42)
