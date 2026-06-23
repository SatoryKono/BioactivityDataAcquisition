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
    assert rows[0]["MeshHeadingList"][0] == {
        "descriptor_name": "Neoplasms",
        "descriptor_ui": "D009369",
        "is_major_topic": True,
        "qualifier_name": "drug therapy",
        "qualifier_ui": "Q000188",
    }
    assert rows[1]["AuthorList"][0]["collective_name"] == "Example Consortium"
    assert rows[1]["PublicationTypeList"] == ["Clinical Trial", "Meta-Analysis"]


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
    assert rows[0]["citations"][0] == {
        "contexts": ["Sentence A"],
        "intent": "Background",
        "isInfluential": True,
    }
    assert rows[0]["authors"][0]["externalIds"]["ORCID"] == "0000-0001-0000-0001"
    assert rows[1]["citations"][0]["section"] == "Methods"
    assert rows[1]["authors"][0]["externalIds"]["OpenAlex"] == "A123"


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
    assert rows[0]["author"][0]["ORCID"] == "https://orcid.org/0000-0002-1825-0097"
    assert rows[0]["author"][1]["name"] == "Edge Consortium"
    assert rows[0]["reference"][0]["unstructured"] == "Prior Work A (2024)"
    assert rows[1]["reference"][0]["article-title"] == "Canonical Reference"


def test_openalex_edge_fixture_covers_nested_location_license_and_index_semantics() -> (
    None
):
    rows = _load_jsonl(
        "tests/fixtures/bronze/openalex/publication/sample_edge_nested_vocab_2026-05-05.jsonl"
    )

    assert rows[0]["indexed_in"] == ["crossref", "pubmed"]
    assert rows[0]["open_access"]["oa_status"] == "gold"
    assert rows[0]["primary_location"]["raw_type"] == "journal-article"
    assert rows[0]["primary_location"]["source"]["type"] == "journal"
    assert rows[0]["locations"][1]["version"] == "submittedVersion"
    assert rows[1]["type"] == "preprint"
    assert rows[1]["primary_location"]["source"]["type"] == "ebook platform"
    assert rows[1]["locations"][0]["license"] == "cc-by-nc-nd"


def test_pubchem_edge_fixture_covers_property_urn_semantics() -> None:
    rows = _load_jsonl(
        "tests/fixtures/bronze/pubchem/compound/sample_edge_property_vocab_2026-05-05.jsonl"
    )

    assert rows[0]["id"]["id"]["cid"] == 999001
    assert rows[0]["props"][0]["urn"] == {
        "datatype": 1,
        "label": "SMILES",
        "name": "Connectivity",
        "release": "2025.06.30",
        "software": "OEChem",
        "source": "OpenEye Scientific Software",
    }
    assert rows[0]["props"][0]["value"]["sval"] == "CCO"
    assert rows[0]["props"][1]["urn"]["label"] == "Mass"
    assert rows[0]["props"][1]["value"]["sval"] == "46.04"
    assert rows[1]["props"][0]["urn"]["label"] == "IUPAC Name"
    assert rows[1]["props"][1]["urn"]["name"] == "XLogP3-AA"
    assert rows[1]["props"][1]["value"]["fval"] == pytest.approx(1.2)


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
    assert rows[0]["comments"][0]["cofactors"][0]["name"] == "ATP"
    assert rows[0]["comments"][1]["texts"][0]["value"].startswith(
        "Participates in a curated pathway"
    )
    assert rows[1]["comments"][0]["reaction"]["name"] == "Hydrolysis"
    assert rows[1]["comments"][1]["subcellularLocations"][0]["location"]["value"] == (
        "Membrane"
    )
    assert rows[1]["features"][1]["location"] == {
        "start": {"value": 20},
        "end": {"value": 80},
    }
