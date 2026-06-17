"""Focused unit tests for filesystem checkpoint writer branches."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bioetl.infrastructure.storage.support.checkpoint_writer import (
    FileCompositeCheckpointWriter,
)


pytestmark = pytest.mark.unit


def test_checkpoint_writer_read_delete_exists_and_missing_paths(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    assert writer.read("missing.json") is None
    assert not writer.exists("missing.json")
    assert writer.delete("missing.json") is False

    writer.write_atomic("state.json", '{"status": "ok"}')

    assert writer.read("state.json") == '{"status": "ok"}'
    assert writer.exists("state.json")
    assert writer.delete("state.json") is True
    assert writer.read("state.json") is None


def test_checkpoint_writer_list_glob_returns_newest_first(tmp_path: Path) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)

    assert writer.list_glob("*.json") == []

    older = tmp_path / "older.json"
    newer = tmp_path / "newer.json"
    older.write_text("older", encoding="utf-8")
    newer.write_text("newer", encoding="utf-8")
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))

    assert writer.list_glob("*.json") == ["newer.json", "older.json"]


def test_checkpoint_writer_write_atomic_removes_temp_on_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    writer = FileCompositeCheckpointWriter(tmp_path)
    path_cls = type(tmp_path)

    def _raise_replace(self: Path, target: Path) -> Path:
        del self, target
        raise OSError("replace failed")

    monkeypatch.setattr(path_cls, "replace", _raise_replace)

    with pytest.raises(OSError, match="replace failed"):
        writer.write_atomic("state.json", "{}")

    assert not (tmp_path / "state.tmp").exists()
    assert not (tmp_path / "state.json").exists()
