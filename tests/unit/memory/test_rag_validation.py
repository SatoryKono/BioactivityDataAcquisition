"""Regression tests for semantic RAG manifest validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from memory.rag.indexing import build_rag_manifests, write_rag_manifests
from memory.rag.validation import (
    normalize_rag_source_path,
    validate_rag_manifest_files,
    validate_rag_manifest_payload,
)

pytestmark = pytest.mark.unit


def _write_source(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _issue_codes(report: object) -> set[str]:
    return {issue.code for issue in report.issues}  # type: ignore[attr-defined]


def test_valid_full_manifest_covers_current_source_surface(tmp_path: Path) -> None:
    _write_source(tmp_path, "docs/00-project/overview.md", "# Overview\nAlpha\n")

    catalog, chunks = build_rag_manifests(tmp_path)
    report = validate_rag_manifest_payload(
        tmp_path,
        catalog,
        chunks,
        require_build_scope="full",
    )

    assert report.ok is True
    assert report.missing_path_count == 0
    assert report.stale_chunk_count == 0
    assert report.indexed_source_count == report.eligible_source_count == 1
    assert catalog["source_surface_sha256"]
    assert catalog["working_tree_state"] == "unavailable"
    assert catalog["git_head_sha"] is None


def test_validator_detects_source_content_drift(tmp_path: Path) -> None:
    source = _write_source(
        tmp_path,
        "docs/00-project/overview.md",
        "# Overview\nOriginal\n",
    )
    catalog, chunks = build_rag_manifests(tmp_path)
    source.write_text("# Overview\nChanged\n", encoding="utf-8")

    report = validate_rag_manifest_payload(tmp_path, catalog, chunks)

    assert report.ok is False
    assert "source_content_mismatch" in _issue_codes(report)
    assert "source_identity_mismatch" in _issue_codes(report)
    assert report.stale_chunk_count == len(chunks)


def test_validator_detects_full_source_set_drift(tmp_path: Path) -> None:
    _write_source(tmp_path, "docs/00-project/overview.md", "# Overview\nAlpha\n")
    catalog, chunks = build_rag_manifests(tmp_path)
    _write_source(tmp_path, "docs/00-project/new.md", "# New\nBeta\n")

    report = validate_rag_manifest_payload(
        tmp_path,
        catalog,
        chunks,
        require_build_scope="full",
    )

    assert report.ok is False
    assert "source_set_mismatch" in _issue_codes(report)
    assert report.indexed_source_count == 1
    assert report.eligible_source_count == 2


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("duplicate_id", "duplicate_chunk_id"),
        ("wrong_chunk_count", "chunk_count_mismatch"),
        ("unknown_source", "chunk_source_not_cataloged"),
        ("bad_chunk_hash", "chunk_content_hash_mismatch"),
        ("path_escape", "invalid_source_path"),
    ],
)
def test_validator_rejects_manifest_contract_drift(
    tmp_path: Path,
    mutation: str,
    expected_code: str,
) -> None:
    _write_source(tmp_path, "docs/00-project/overview.md", "# Overview\nAlpha\n")
    catalog, chunks = build_rag_manifests(tmp_path)
    mutated_chunks = [dict(chunk) for chunk in chunks]
    mutated_catalog = dict(catalog)

    if mutation == "duplicate_id":
        mutated_chunks.append(dict(mutated_chunks[0]))
        mutated_catalog["chunk_count"] = len(mutated_chunks)
    elif mutation == "wrong_chunk_count":
        mutated_catalog["chunk_count"] = len(mutated_chunks) + 1
    elif mutation == "unknown_source":
        mutated_chunks[0]["source_path"] = "docs/00-project/unknown.md"
    elif mutation == "bad_chunk_hash":
        mutated_chunks[0]["content_hash"] = "0" * 64
    elif mutation == "path_escape":
        mutated_chunks[0]["source_path"] = "../outside.md"

    report = validate_rag_manifest_payload(
        tmp_path,
        mutated_catalog,
        mutated_chunks,
    )

    assert report.ok is False
    assert expected_code in _issue_codes(report)


def test_devin_wiki_virtual_fragments_are_normalized_to_base_source(
    tmp_path: Path,
) -> None:
    _write_source(
        tmp_path,
        ".devin/wiki.json",
        json.dumps(
            {
                "repo_notes": [{"content": "Navigation seed."}],
                "pages": [{"title": "Architecture", "purpose": "Map."}],
            }
        )
        + "\n",
    )

    catalog, chunks = build_rag_manifests(tmp_path)
    report = validate_rag_manifest_payload(tmp_path, catalog, chunks)

    assert report.ok is True
    assert normalize_rag_source_path(
        ".devin/wiki.json#architecture", allow_virtual_fragment=True
    ) == ".devin/wiki.json"


def test_manifest_file_validator_requires_requested_scope(tmp_path: Path) -> None:
    _write_source(tmp_path, "src/memory/tooling/demo.py", "VALUE = 1\n")
    output_dir = tmp_path / "out"
    catalog_path, chunks_path = write_rag_manifests(
        tmp_path,
        output_dir,
        build_scope="workflow",
        focus_query="demo",
        max_sources=1,
    )

    report = validate_rag_manifest_files(
        tmp_path,
        catalog_path,
        chunks_path,
        require_build_scope="full",
    )

    assert report.ok is False
    assert "build_scope_mismatch" in _issue_codes(report)
