"""Tests for semantic readiness of rebuild-only memory artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

from memory.artifact_readiness import rag_chunks_ready
from memory.rag.indexing import write_rag_manifests

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
