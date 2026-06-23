"""Tests for domain.mapping.publication_fields — cross-provider field unification."""

from __future__ import annotations

import pytest

from bioetl.domain.mapping import (
    PUBLICATION_FIELD_MAPPING,
    UNIFIED_TO_PROVIDER,
    apply_field_mapping,
    get_provider_name,
    get_unified_name,
)
from bioetl.domain.mapping.publication_fields import ProviderName


@pytest.mark.unit
class TestPublicationFieldMapping:
    """Tests for PUBLICATION_FIELD_MAPPING constant."""

    def test_all_providers_present(self) -> None:
        expected: set[ProviderName] = {
            "chembl",
            "crossref",
            "openalex",
            "pubmed",
            "semanticscholar",
        }
        assert set(PUBLICATION_FIELD_MAPPING.keys()) == expected

    def test_chembl_mapping_entries(self) -> None:
        m = PUBLICATION_FIELD_MAPPING["chembl"]
        assert m["doc_type"] == "publication_type"
        assert m["year"] == "publication_year"

    def test_crossref_mapping_entries(self) -> None:
        m = PUBLICATION_FIELD_MAPPING["crossref"]
        assert m["source_type"] == "publication_type"
        assert m["citation_count"] == "citations_received"
        assert m["reference_count"] == "citations_made"

    def test_pubmed_mapping_entries(self) -> None:
        m = PUBLICATION_FIELD_MAPPING["pubmed"]
        assert m["journal_title"] == "journal"
        assert m["journal_abbrev"] == "journal_name_short"
        assert m["mesh_terms"] == "subject_mesh"

    def test_openalex_mapping_entries(self) -> None:
        m = PUBLICATION_FIELD_MAPPING["openalex"]
        assert m["topics"] == "subject_topics"
        assert m["affiliations"] == "affiliation_list"

    def test_semanticscholar_mapping_entries(self) -> None:
        m = PUBLICATION_FIELD_MAPPING["semanticscholar"]
        assert m["fields_of_study"] == "subject_fields"
        assert m["pages"] == "page_range"


@pytest.mark.unit
class TestUnifiedToProvider:
    """Tests for reverse mapping UNIFIED_TO_PROVIDER."""

    def test_reverse_mapping_all_providers(self) -> None:
        assert set(UNIFIED_TO_PROVIDER.keys()) == set(PUBLICATION_FIELD_MAPPING.keys())

    def test_reverse_mapping_roundtrip(self) -> None:
        """Forward then reverse mapping recovers original field name."""
        for provider, mapping in PUBLICATION_FIELD_MAPPING.items():
            reverse = UNIFIED_TO_PROVIDER[provider]
            for original, unified in mapping.items():
                assert reverse[unified] == original, (
                    f"Roundtrip failed for {provider}: {original} -> {unified} -> {reverse.get(unified)}"
                )


@pytest.mark.unit
class TestGetUnifiedName:
    """Tests for get_unified_name helper."""

    def test_mapped_field(self) -> None:
        assert get_unified_name("chembl", "doc_type") == "publication_type"

    def test_unmapped_field_returns_original(self) -> None:
        assert get_unified_name("chembl", "title") == "title"

    def test_unknown_provider_returns_original(self) -> None:
        # type: ignore because we're testing invalid input
        assert get_unified_name("unknown", "doc_type") == "doc_type"  # type: ignore[arg-type]


@pytest.mark.unit
class TestGetProviderName:
    """Tests for get_provider_name helper."""

    def test_mapped_unified_field(self) -> None:
        assert get_provider_name("chembl", "publication_type") == "doc_type"

    def test_unmapped_unified_field_returns_original(self) -> None:
        assert get_provider_name("chembl", "title") == "title"

    def test_get_provider_name__returns_original__0733e419(self) -> None:
        assert get_provider_name("unknown", "publication_type") == "publication_type"  # type: ignore[arg-type]


@pytest.mark.unit
class TestApplyFieldMapping:
    """Tests for apply_field_mapping function."""

    def test_chembl_record_mapping(self) -> None:
        record = {"doc_type": "article", "year": 2020, "title": "Test"}
        result = apply_field_mapping(record, "chembl")
        assert result == {
            "publication_type": "article",
            "publication_year": 2020,
            "title": "Test",
        }

    def test_preserves_unmapped_fields(self) -> None:
        record = {"title": "Test", "abstract": "Abs"}
        result = apply_field_mapping(record, "chembl")
        assert result == {"title": "Test", "abstract": "Abs"}

    def test_apply_field_mapping__empty_record__7ab29770(self) -> None:
        assert apply_field_mapping({}, "chembl") == {}

    def test_unknown_provider_returns_same_keys(self) -> None:
        record = {"doc_type": "article"}
        result = apply_field_mapping(record, "unknown")  # type: ignore[arg-type]
        assert result == record

    def test_crossref_full_mapping(self) -> None:
        record = {
            "source_type": "journal-article",
            "year": 2023,
            "citation_count": 42,
            "reference_count": 15,
            "first_page": "100",
            "last_page": "110",
            "doi": "10.1234/test",
        }
        result = apply_field_mapping(record, "crossref")
        assert result["publication_type"] == "journal-article"
        assert result["citations_received"] == 42
        assert result["citations_made"] == 15
        assert result["page_first"] == "100"
        assert result["doi"] == "10.1234/test"
