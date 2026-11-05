"""Failure-path ownership tests for evidence-location publication."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane import _evidence_location_publish as publish

pytestmark = pytest.mark.unit


def test_fdopen_failure_closes_mkstemp_descriptor_and_removes_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A failed ownership transfer must close the raw descriptor and unlink path."""
    base = tmp_path.resolve()
    target = base / "catalog.json"
    original_mkstemp = tempfile.mkstemp
    created: dict[str, int | str] = {}

    def recording_mkstemp(**kwargs: object) -> tuple[int, str]:
        fd, path = original_mkstemp(**kwargs)
        created["fd"] = fd
        created["path"] = path
        return fd, path

    def failing_fdopen(*args: object, **kwargs: object) -> object:
        raise OSError("fdopen failed")

    monkeypatch.setattr(tempfile, "mkstemp", recording_mkstemp)
    monkeypatch.setattr(publish.os, "fdopen", failing_fdopen)

    with pytest.raises(OSError, match="fdopen failed"):
        publish.publish_bytes_if_absent(target, b"payload", trusted_base=base)

    fd = created["fd"]
    assert isinstance(fd, int)
    with pytest.raises(OSError):
        os.fstat(fd)
    path = created["path"]
    assert isinstance(path, str)
    assert not Path(path).exists()
