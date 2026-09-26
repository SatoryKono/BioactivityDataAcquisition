"""Freshness, integrity, memory bounds and sharing for catalog projections."""

from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from bioetl.infrastructure.storage import file_metadata_index as module
from bioetl.infrastructure.storage.file_metadata_index import FileMetadataIndex
from bioetl.infrastructure.storage.run_report_store_adapter import (
    FileRunReportStoreAdapter,
)

pytestmark = pytest.mark.unit


def test_concurrent_readers_share_one_projection(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("one", encoding="utf-8")
    project = Mock(side_effect=str)
    index = FileMetadataIndex(project)
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert list(pool.map(index.read, [path] * 16)) == ["one"] * 16
    project.assert_called_once_with("one")


def test_same_size_atomic_replacement_with_preserved_mtime_is_detected(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("old", encoding="utf-8")
    index = FileMetadataIndex()
    assert index.read(path) == "old"
    before = path.stat()
    replacement = tmp_path / "replacement"
    replacement.write_text("new", encoding="utf-8")
    os.utime(replacement, ns=(before.st_atime_ns, before.st_mtime_ns))
    replacement.replace(path)
    assert index.read(path) == "new"


def test_removed_or_corrupt_file_never_returns_previous_projection(tmp_path):
    path = tmp_path / "record.json"
    path.write_text('{"ok":true}', encoding="utf-8")
    index = FileMetadataIndex(lambda text: json.dumps(json.loads(text)))
    assert index.read(path) == '{"ok": true}'
    path.write_text("broken", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        index.read(path)
    path.unlink()
    with pytest.raises(FileNotFoundError):
        index.read(path)
    path.write_text("{}", encoding="utf-8")
    assert index.read(path) == "{}"


def test_failed_stat_does_not_serve_cached_data(tmp_path, monkeypatch):
    path = tmp_path / "record.json"
    path.write_text("ok", encoding="utf-8")
    index = FileMetadataIndex()
    assert index.read(path) == "ok"
    with monkeypatch.context() as patch:
        patch.setattr(Path, "stat", Mock(side_effect=PermissionError("denied")))
        with pytest.raises(PermissionError):
            index.read(path)
    assert not index._entries


def test_file_changing_during_every_read_fails_closed(tmp_path):
    path = tmp_path / "record.json"
    path.write_text("old", encoding="utf-8")

    def changing(text):
        path.write_text(text + "x", encoding="utf-8")
        return text

    index = FileMetadataIndex(changing)
    with pytest.raises(OSError, match="changed during"):
        index.read(path)
    assert not index._entries


def test_projection_memory_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "_MAX_BYTES", 4)
    index = FileMetadataIndex()
    for name in ("a", "b", "c"):
        path = tmp_path / name
        path.write_text(name * 3, encoding="utf-8")
        assert index.read(path) == name * 3
    assert index._bytes == 3
    assert len(index._entries) == 1


def test_report_projection_is_shared_but_full_artifact_is_preserved(
    tmp_path, monkeypatch
):
    path = tmp_path / "report.json"
    body = {"identity": {"run_id": "a"}, "schema_version": "v1", "large": "x" * 10000}
    path.write_text(json.dumps(body), encoding="utf-8")
    first = FileRunReportStoreAdapter()
    second = FileRunReportStoreAdapter()
    real_read = Path.read_text
    calls = []

    def counted(target, *args, **kwargs):
        calls.append(target)
        return real_read(target, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", counted)
    assert json.loads(first.read_identity_text(str(path))) == {
        "identity": body["identity"],
        "schema_version": "v1",
    }
    assert second.read_identity_text(str(path)) == first.read_identity_text(str(path))
    assert calls == [path]
    assert json.loads(first.read_text(str(path))) == body
