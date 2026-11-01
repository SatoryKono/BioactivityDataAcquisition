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
    monkeypatch.setattr(cleanup_core.os, "open", lambda *args, **kwargs: 42)
    monkeypatch.setattr(cleanup_core.os, "fstat", lambda fd: inode)
    monkeypatch.setattr(cleanup_core.os, "close", closed)
    monkeypatch.setattr(Path, "stat", lambda *args, **kwargs: inode)

    def lost_writer_view(lease):
        raise NotImplementedError("writer root view disappeared after probe")

    monkeypatch.setattr(
        cleanup_core.BronzeRootLease, "writer_path", property(lost_writer_view)
    )
    assert cleanup_core._fd_view_supported() is True
    closed.assert_called_once_with(42)
    with pytest.raises(NotImplementedError, match="disappeared after probe"):
        cleanup_core._shared_lease_after_pending_check(Path("unused"), 42)
