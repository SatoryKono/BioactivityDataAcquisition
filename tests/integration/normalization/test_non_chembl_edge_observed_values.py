"""Offline edge-case checks for non-ChEMBL observed-value fixtures."""

from __future__ import annotations

import json
from pathlib import Path


def _load_jsonl(path: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_uniprot_idmapping_edge_fixture_covers_all_status_variants() -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/uniprot/idmapping/sample_edge_statuses_2026-05-05.jsonl"
    )
    assert {row["mapping_status"] for row in rows} == {
        "found",
        "multiple",
        "not_found",
        "error",
    }


def test_pubmed_edge_fixture_covers_publication_type_mesh_and_affiliation_shapes() -> (
    None
):
    rows = _load_jsonl(
        "tests/fixtures/bronze/pubmed/publication/sample_edge_publication_types_mesh_2026-05-05.jsonl"
    )
    publication_types = {
        value for row in rows for value in row.get("PublicationTypeList", [])
    }
    assert {
        "Journal Article",
        "Review",
        "Clinical Trial",
        "Meta-Analysis",
    } <= publication_types
    assert all("MeshHeadingList" in row for row in rows)
    assert all("AuthorList" in row for row in rows)


def test_semanticscholar_edge_fixture_covers_nested_author_and_citation_variants() -> (
    None
):
    rows = _load_jsonl(
        "tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl"
    )
    publication_types = {
        value for row in rows for value in row.get("publicationTypes", [])
    }
    assert {"JournalArticle", "Review", "ClinicalTrial"} <= publication_types
    assert any(
        "section" in citation for row in rows for citation in row.get("citations", [])
    )
    assert any(
        "DBLP" in (author.get("externalIds") or {})
        for row in rows
        for author in row.get("authors", [])
    )
