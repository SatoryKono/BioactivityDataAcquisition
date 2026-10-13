"""Tests for semantic readiness of rebuild-only memory artifacts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from memory.artifact_readiness import rag_chunks_ready, timeline_events_ready
from memory.rag.indexing import write_rag_manifests
from memory.rag.validation import capture_rag_git_identity
from memory.timeline._common import write_timeline_manifest

pytestmark = pytest.mark.unit


def _write_doc(root: Path, text: str = "# Overview\nAlpha\n") -> Path:
    source = root / "docs/00-project/overview.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    return source


def test_rag_readiness_requires_catalog_chunk_pair(tmp_path: Path) -> None:
    chunks_path = tmp_path / "chunks.jsonl"
    chunks_path.write_text('{"id":"chunk-1"}\n', encoding="utf-8")

    assert rag_chunks_ready(chunks_path) is False


def test_rag_readiness_accepts_current_valid_pair(tmp_path: Path) -> None:
    _write_doc(tmp_path)
    _, chunks_path = write_rag_manifests(tmp_path, tmp_path / "out")

    assert rag_chunks_ready(chunks_path, repo_root=tmp_path) is True


def test_rag_readiness_rejects_source_content_drift(tmp_path: Path) -> None:
    source = _write_doc(tmp_path)
    _, chunks_path = write_rag_manifests(tmp_path, tmp_path / "out")
    source.write_text("# Overview\nChanged\n", encoding="utf-8")

    assert rag_chunks_ready(chunks_path, repo_root=tmp_path) is False


def test_untracked_source_invalidates_clean_rag_cache_identity(tmp_path: Path) -> None:
    _write_doc(tmp_path)
    for args in (
        ("init", "-q"),
        ("add", "docs/00-project/overview.md"),
        (
            "-c",
            "user.name=RAG test",
            "-c",
            "user.email=rag@example.invalid",
            "commit",
            "-qm",
            "initial source",
        ),
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / ".git/info/exclude").write_text("out/\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    _, chunks_path = write_rag_manifests(tmp_path, output_dir)
    assert capture_rag_git_identity(tmp_path)["working_tree_state"] == "clean"
    assert rag_chunks_ready(chunks_path, repo_root=tmp_path)

    untracked = tmp_path / "docs/00-project/new.md"
    untracked.write_text("# New source\n", encoding="utf-8")
    assert capture_rag_git_identity(tmp_path)["working_tree_state"] == "dirty"
    assert not rag_chunks_ready(chunks_path, repo_root=tmp_path)
    untracked.write_text("# Changed new source\n", encoding="utf-8")
    assert not rag_chunks_ready(chunks_path, repo_root=tmp_path)
    untracked.unlink()
    assert rag_chunks_ready(chunks_path, repo_root=tmp_path)


def test_rag_readiness_rejects_workflow_pair_when_full_is_required(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src/memory/tooling/demo.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    _, chunks_path = write_rag_manifests(
        tmp_path,
        tmp_path / "outside",
        build_scope="workflow",
        focus_query="demo",
        max_sources=1,
    )

    assert (
        rag_chunks_ready(
            chunks_path,
            repo_root=tmp_path,
            require_build_scope="full",
        )
        is False
    )


def test_timeline_readiness_rejects_tampered_projection(tmp_path: Path) -> None:
    events_dir = tmp_path / "events"
    events_dir.mkdir()
    events = events_dir / "ci.jsonl"
    events.write_text('{"id":"ci::one"}\n', encoding="utf-8")
    write_timeline_manifest(tmp_path, events_dir)

    assert timeline_events_ready(events_dir) is True

    events.write_text('{"id":"ci::changed"}\n', encoding="utf-8")

    assert timeline_events_ready(events_dir) is False


def test_timeline_readiness_ignores_untracked_files(tmp_path: Path) -> None:
    source = _write_doc(tmp_path)
    for args in (
        ("init", "-q"),
        ("add", source.relative_to(tmp_path).as_posix()),
        (
            "-c",
            "user.name=Timeline test",
            "-c",
            "user.email=timeline@example.invalid",
            "commit",
            "-qm",
            "initial source",
        ),
    ):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    events_dir = tmp_path / "out/events"
    events_dir.mkdir(parents=True)
    (tmp_path / ".git/info/exclude").write_text("out/\n", encoding="utf-8")
    (events_dir / "ci.jsonl").write_text('{"id":"ci::one"}\n', encoding="utf-8")
    (tmp_path / "scratch.txt").write_text("temporary\n", encoding="utf-8")
    write_timeline_manifest(tmp_path, events_dir)

    assert capture_rag_git_identity(tmp_path)["working_tree_state"] == "dirty"
    assert timeline_events_ready(events_dir, repo_root=tmp_path)


def test_timeline_readiness_requires_manifest_inside_repository(
    tmp_path: Path,
) -> None:
    (tmp_path / ".git").mkdir()
    events_dir = tmp_path / "src/memory/derived/timeline/events"
    events_dir.mkdir(parents=True)
    (events_dir / "ci.jsonl").write_text('{"id":"ci::one"}\n', encoding="utf-8")

    assert timeline_events_ready(events_dir, repo_root=tmp_path) is False
