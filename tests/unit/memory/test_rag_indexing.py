"""Tests for deterministic RAG manifest generation."""

from __future__ import annotations

import json
from pathlib import Path

from memory.rag.chunking import infer_domain, infer_source_type, split_markdown_sections
from memory.rag.indexing import build_rag_manifests, write_rag_manifests
from memory.rag.retrieval import filter_chunks, load_chunk_manifest


def test_split_markdown_sections_respects_headings() -> None:
    text = """---
title: Demo
---

# Title
Intro paragraph.

## Details
Detail line.
"""
    sections = split_markdown_sections(text)
    assert [section.title for section in sections] == ["Title", "Details"]
    assert sections[0].level == 1
    assert "Intro paragraph." in sections[0].content


def test_infer_source_metadata_from_repo_paths() -> None:
    assert infer_source_type(Path("docs/02-architecture/decisions/ADR-043-example.md")) == "adr"
    assert infer_source_type(Path("docs/05-operations/runbooks/example.md")) == "runbook"
    assert infer_source_type(Path("docs/00-project/overview.md")) == "doc"
    assert infer_domain(Path("docs/02-architecture/decisions/ADR-043-example.md")) == "architecture"
    assert infer_domain(Path("docs/05-operations/runbooks/example.md")) == "operations"
    assert infer_domain(Path("docs/00-project/overview.md")) == "project"


def test_build_rag_manifests_indexes_selected_markdown_sources(tmp_path: Path) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/02-architecture/decisions").mkdir(parents=True)
    (tmp_path / "docs/05-operations/runbooks").mkdir(parents=True)
    (tmp_path / "docs/99-archive").mkdir(parents=True)

    (tmp_path / "docs/00-project/overview.md").write_text("# Overview\nAlpha\n", encoding="utf-8")
    (tmp_path / "docs/02-architecture/decisions/ADR-999-test.md").write_text(
        "# ADR Test\nDecision body.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/05-operations/runbooks/sample.md").write_text(
        "# Runbook\nRecovery steps.\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/99-archive/ignored.md").write_text("# Ignore\n", encoding="utf-8")

    catalog, chunks = build_rag_manifests(tmp_path)

    assert catalog["source_count"] == 3
    assert {item["source_type"] for item in catalog["sources"]} == {"doc", "adr", "runbook"}
    assert all("99-archive" not in chunk["source_path"] for chunk in chunks)


def test_write_and_reload_rag_manifests(tmp_path: Path) -> None:
    (tmp_path / "docs/00-project").mkdir(parents=True)
    (tmp_path / "docs/00-project/overview.md").write_text(
        "# Overview\nAlpha\n\n## Scope\nBeta\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "out"
    catalog_path, chunks_path = write_rag_manifests(tmp_path, output_dir)

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    chunks = load_chunk_manifest(chunks_path)

    assert catalog["source_count"] == 1
    assert catalog["chunk_count"] == 2
    assert len(chunks) == 2
    assert len(filter_chunks(chunks, source_type="doc", query="scope")) == 1
