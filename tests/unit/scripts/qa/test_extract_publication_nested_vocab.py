"""Tests for nested publication-sidecar vocabulary extraction."""

from __future__ import annotations

import pytest

from pathlib import Path

from scripts.engineering.qa.extract_publication_nested_vocab import (
    extract_publication_nested_vocab,
)


pytestmark = pytest.mark.unit


def test_extract_publication_nested_vocab_collects_expected_edge_values() -> None:
    payload = extract_publication_nested_vocab(
        openalex_paths=[
            Path(
                "tests/fixtures/bronze/openalex/publication/sample_ci_2026-04-29.jsonl"
            ),
            Path(
                "tests/fixtures/bronze/openalex/publication/sample_edge_nested_vocab_2026-05-05.jsonl"
            ),
        ],
        semanticscholar_paths=[
            Path(
                "tests/fixtures/bronze/semanticscholar/publication/sample_ci_2026-04-30.jsonl"
            ),
            Path(
                "tests/fixtures/bronze/semanticscholar/publication/sample_edge_publication_types_citations_2026-05-05.jsonl"
            ),
        ],
        pubmed_paths=[
            Path(
                "tests/fixtures/bronze/pubmed/publication/sample_edge_publication_types_mesh_2026-05-05.jsonl"
            )
        ],
    )

    assert "journal" in payload["openalex"]["source_type"]
    assert "posted-content" in payload["openalex"]["raw_type"]
    assert "JournalArticle" in payload["semanticscholar"]["publication_types"]
    assert "section" in payload["semanticscholar"]["citation_context_keys"]
    assert "DBLP" in payload["semanticscholar"]["author_id_families"]
    assert "Clinical Trial" in payload["pubmed"]["publication_types"]
    assert "descriptor_ui" in payload["pubmed"]["mesh_keys"]
    assert "collective_name" in payload["pubmed"]["affiliation_keys"]
