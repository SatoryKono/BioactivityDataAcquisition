"""Tests for fail-closed checkpoint artifact candidate resolution."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.domain.control_plane import (
    ControlPlaneArtifactResolutionIssueCode,
    ControlPlaneArtifactSurface,
)
from bioetl.infrastructure.control_plane._file_artifact_lifecycle_checkpoint_refs import (
    _append_checkpoint_history_dir,
    _append_checkpoint_manifest_index,
)

pytestmark = pytest.mark.unit


def _manifest() -> SimpleNamespace:
    return SimpleNamespace(
        pipeline_name="chembl_activity", run_id="run-1", manifest_id="manifest-1"
    )


def test_append_checkpoint_history_dir_collects_files_only(tmp_path: Path) -> None:
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]] = []
    run_dir = tmp_path / "history"

    _append_checkpoint_history_dir(
        candidates, tmp_path, _manifest(), lambda *_: run_dir
    )
    assert candidates == []

    run_dir.mkdir()
    checkpoint = run_dir / "checkpoint.json"
    checkpoint.write_text("{}", encoding="utf-8")
    (run_dir / "nested").mkdir()
    _append_checkpoint_history_dir(
        candidates, tmp_path, _manifest(), lambda *_: run_dir
    )
    assert candidates == [(ControlPlaneArtifactSurface.CHECKPOINT, checkpoint)]


def _append_index(
    *,
    tmp_path: Path,
    index_path: Path,
    read_json_file: object,
    history_path: Path | None = None,
) -> tuple[
    list[tuple[ControlPlaneArtifactSurface, Path]],
    list[object],
]:
    candidates: list[tuple[ControlPlaneArtifactSurface, Path]] = []
    issues: list[object] = []
    resolved_history = history_path or tmp_path / "history.json"
    _append_checkpoint_manifest_index(
        candidates,
        issues,
        tmp_path,
        _manifest(),
        history_path_from_manifest_index=lambda *_: resolved_history,
        manifest_index_path=lambda *_: index_path,
        read_json_file=read_json_file,
    )
    return candidates, issues


def test_append_checkpoint_manifest_index_reports_missing_index(tmp_path: Path) -> None:
    candidates, issues = _append_index(
        tmp_path=tmp_path,
        index_path=tmp_path / "missing.json",
        read_json_file=lambda _: {},
    )
    assert candidates == []
    assert issues[0].code is ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_MISSING


@pytest.mark.parametrize(
    "reader",
    [
        lambda _: (_ for _ in ()).throw(ValueError("invalid")),
        lambda _: [],
        lambda _: {},
        lambda _: {"history_path": " "},
    ],
)
def test_append_checkpoint_manifest_index_reports_corrupt_index(
    tmp_path: Path, reader: object
) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text("{}", encoding="utf-8")
    candidates, issues = _append_index(
        tmp_path=tmp_path, index_path=index_path, read_json_file=reader
    )
    assert candidates == [(ControlPlaneArtifactSurface.CHECKPOINT, index_path)]
    assert issues[0].code is ControlPlaneArtifactResolutionIssueCode.CHECKPOINT_INDEX_CORRUPT


def test_append_checkpoint_manifest_index_adds_existing_history(tmp_path: Path) -> None:
    index_path = tmp_path / "index.json"
    index_path.write_text("{}", encoding="utf-8")
    history_path = tmp_path / "history.json"
    history_path.write_text("{}", encoding="utf-8")
    candidates, issues = _append_index(
        tmp_path=tmp_path,
        index_path=index_path,
        read_json_file=lambda _: {"history_path": " history.json "},
        history_path=history_path,
    )
    assert candidates == [
        (ControlPlaneArtifactSurface.CHECKPOINT, index_path),
        (ControlPlaneArtifactSurface.CHECKPOINT, history_path),
    ]
    assert issues == []
