"""Failure-path ownership tests for evidence-location publication."""

from __future__ import annotations

import os
import errno
import tempfile
from pathlib import Path

import pytest

from bioetl.infrastructure.control_plane import evidence_location_publish as publish

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("error_type", [OSError, ValueError])
def test_fdopen_failure_closes_mkstemp_descriptor_and_removes_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    error_type: type[Exception],
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
        raise error_type("fdopen failed")

    monkeypatch.setattr(tempfile, "mkstemp", recording_mkstemp)
    monkeypatch.setattr(publish.os, "fdopen", failing_fdopen)

    with pytest.raises(error_type, match="fdopen failed"):
        publish.publish_bytes_if_absent(target, b"payload", trusted_base=base)

    fd = created["fd"]
    assert isinstance(fd, int)
    with pytest.raises(OSError):
        os.fstat(fd)
    path = created["path"]
    assert isinstance(path, str)
    assert not Path(path).exists()


def test_directory_read_is_an_explicit_invalid_location(monkeypatch, tmp_path):
    def directory_read(path):
        raise IsADirectoryError(str(path))

    monkeypatch.setattr(Path, "read_bytes", directory_read)
    with pytest.raises(ValueError, match="path is a directory") as caught:
        publish.read_existing_bytes(tmp_path / "directory", trusted_base=tmp_path)
    assert isinstance(caught.value.__cause__, IsADirectoryError)


def test_generic_eexist_keeps_the_existing_bytes_and_cleans_temp(monkeypatch, tmp_path):
    target = tmp_path / "catalog.json"
    target.write_bytes(b"previous")
    collision = OSError("generic provider collision")
    collision.errno = errno.EEXIST

    def occupied(*args):
        raise collision

    monkeypatch.setattr(publish.os, "link", occupied)
    assert (
        publish.publish_bytes_if_absent(target, b"new", trusted_base=tmp_path) is False
    )
    assert target.read_bytes() == b"previous"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["catalog.json"]
