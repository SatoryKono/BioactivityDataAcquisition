"""Unit tests for pure composite metadata parsing helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.services.composite_metadata_helpers import (
    extract_composite_lineage_metadata,
    parse_composite_field_sources,
)


def test_parse_composite_field_sources_from_dict_and_stringified_dict() -> None:
    """Field-source metadata should parse from dict and string payloads."""
    assert parse_composite_field_sources({"title": "openalex", "doi": "seed"}) == {
        "title": "openalex",
        "doi": "seed",
    }
    assert parse_composite_field_sources("{'abstract': 'pubmed'}") == {
        "abstract": "pubmed"
    }
    assert parse_composite_field_sources("[1, 2, 3]") == {}


def test_extract_composite_lineage_metadata_parses_graph_relevant_fields() -> None:
    """Composite lineage extraction should normalize canonical graph fields."""
    metadata = extract_composite_lineage_metadata(
        [
            {
                "_composite_run_id": "comp-run-123",
                "_source_providers": "['seed', 'openalex']",
                "_enrichment_status": "{'openalex': 'success'}",
                "_field_sources": "{'title': 'openalex', 'doi': 'seed'}",
                "_seed_record_id": "seed-001",
                "_lineage_created_at": "2026-03-24T10:00:00+00:00",
            }
        ],
        composite_name="composite.publication",
    )

    assert metadata is not None
    assert metadata.composite_run_id == "comp-run-123"
    assert metadata.composite_name == "composite.publication"
    assert metadata.source_providers == ("seed", "openalex")
    assert metadata.enrichment_status["openalex"].status == "success"
    assert metadata.field_sources == {"title": "openalex", "doi": "seed"}
    assert metadata.seed_record_id == "seed-001"
    assert metadata.created_at == datetime(2026, 3, 24, 10, 0, tzinfo=UTC)


def test_extract_composite_lineage_metadata_returns_none_for_plain_records() -> None:
    """Plain records should not produce composite lineage metadata."""
    assert extract_composite_lineage_metadata([{"id": 1}], composite_name="plain") is None
