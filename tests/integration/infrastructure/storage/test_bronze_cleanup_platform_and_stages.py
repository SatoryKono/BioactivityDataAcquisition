"""Private-stage retirement regression for Bronze cleanup."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest
from bioetl.infrastructure.storage.bronze import cleanup_posix

pytestmark = pytest.mark.integration


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
