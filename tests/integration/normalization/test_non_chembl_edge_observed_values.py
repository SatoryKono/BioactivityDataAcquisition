"""Offline edge-case checks for non-ChEMBL observed-value fixtures."""

from __future__ import annotations

import pytest

import json
from pathlib import Path


pytestmark = pytest.mark.integration


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


def test_crossref_edge_fixture_covers_structured_author_and_reference_payloads() -> (
    None
):
    rows = _load_jsonl(
        "tests/fixtures/bronze/crossref/publication/sample_edge_structured_payloads_2026-05-12.jsonl"
    )
    assert {"posted-content", "journal-article"} == {row["type"] for row in rows}
    assert all(isinstance(row.get("author"), list) and row["author"] for row in rows)
    assert all(
        isinstance(row.get("reference"), list) and row["reference"] for row in rows
    )
    assert any(
        isinstance(author, dict) and author.get("ORCID")
        for row in rows
        for author in row.get("author", [])
    )


def test_publication_edge_fixtures_cover_identifier_and_taxonomy_inventory_hooks() -> (
    None
):
    crossref_rows = _load_jsonl(
        "tests/fixtures/bronze/crossref/publication/sample_edge_structured_payloads_2026-05-12.jsonl"
    )
    semanticscholar_rows = _load_jsonl(
        "tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl"
    )

    assert {"journal-article", "posted-content"} <= {
        row["type"] for row in crossref_rows
    }
    assert any(
        (author.get("externalIds") or {}).get("ORCID")
        for row in semanticscholar_rows
        for author in row.get("authors", [])
        if isinstance(author, dict)
    )


def test_uniprot_protein_edge_fixture_covers_nested_comment_feature_and_keyword_vocab() -> (
    None
):
    rows = _load_jsonl(
        "tests/fixtures/bronze/uniprot/protein/sample_edge_semantic_payloads_2026-05-12.jsonl"
    )
    comment_types = {
        comment["commentType"]
        for row in rows
        for comment in row.get("comments", [])
        if isinstance(comment, dict) and comment.get("commentType") is not None
    }
    feature_types = {
        feature["type"]
        for row in rows
        for feature in row.get("features", [])
        if isinstance(feature, dict) and feature.get("type") is not None
    }
    keyword_categories = {
        keyword["category"]
        for row in rows
        for keyword in row.get("keywords", [])
        if isinstance(keyword, dict) and keyword.get("category") is not None
    }

    assert {"COFACTOR", "PATHWAY", "CATALYTIC ACTIVITY"} <= comment_types
    assert {"Active site", "Binding site", "Domain", "Modified residue"} <= (
        feature_types
    )
    assert {"Ligand", "Technical term", "Biological process", "PTM"} <= (
        keyword_categories
    )
