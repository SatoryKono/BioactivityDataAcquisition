"""Deterministic test helpers for RAG catalog/chunk manifest pairs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from memory.rag.chunking import content_hash
from memory.rag.validation import normalize_rag_source_path


def write_test_rag_manifest(
    chunks_path: Path,
    rows: list[dict[str, Any]],
    *,
    build_scope: str = "workflow",
) -> tuple[Path, Path]:
    """Write a structurally valid manifest pair for retrieval-focused tests."""
    normalized_rows: list[dict[str, Any]] = []
    source_counts: dict[str, int] = {}
    source_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        normalized_row = dict(row)
        content = str(normalized_row.get("content") or "")
        normalized_row["content"] = content
        normalized_row["content_hash"] = content_hash(content)
        source_path = normalize_rag_source_path(
            str(normalized_row["source_path"]),
            allow_virtual_fragment=True,
        )
        source_counts[source_path] = source_counts.get(source_path, 0) + 1
        source_rows.setdefault(
            source_path,
            {
                "content_hash": "0" * 64,
                "domain": normalized_row.get("domain"),
                "owner": "BioETL Team",
                "repo_zone": normalized_row.get("repo_zone"),
                "source_path": source_path,
                "source_type": normalized_row.get("source_type"),
            },
        )
        normalized_rows.append(normalized_row)

    sources = []
    for source_path in sorted(source_rows):
        source = dict(source_rows[source_path])
        source["section_count"] = source_counts[source_path]
        sources.append(source)
    catalog = {
        "build_scope": build_scope,
        "chunk_count": len(normalized_rows),
        "focus_query": "test",
        "generator_version": 2,
        "git_head_sha": None,
        "source_count": len(sources),
        "source_surface_sha256": "0" * 64,
        "sources": sources,
        "working_tree_state": "unavailable",
    }

    chunks_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path = chunks_path.with_name("corpus_catalog.json")
    catalog_path.write_text(
        json.dumps(catalog, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    chunks_path.write_text(
        "".join(
            f"{json.dumps(row, sort_keys=True, ensure_ascii=True)}\n"
            for row in normalized_rows
        ),
        encoding="utf-8",
    )
    return catalog_path, chunks_path
