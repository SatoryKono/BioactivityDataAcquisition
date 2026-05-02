"""Unit tests for OrganismClassifier.

Tests cover:
- Single-record classification (classify, get_cellularity, normalize_name)
- Batch classification and enrichment (classify_records, enrich_records)
- Filtering by cellularity (filter_by_cellularity)
- Classification statistics (compute_stats)
- Custom field names
- Edge cases (empty records, missing fields, None values)
"""

from __future__ import annotations

import pytest

from bioetl.domain.mapping.organism_classification import OrganismClassificationResult
from bioetl.domain.behavior.organism_classification_service import (
    ClassificationStats,
    OrganismClassifier,
)
from bioetl.domain.types import CellularityType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def service() -> OrganismClassifier:
    """Default service with standard ChEMBL field names."""
    return OrganismClassifier()


@pytest.fixture()
def custom_service() -> OrganismClassifier:
    """Service with custom field names."""
    return OrganismClassifier(
        organism_field="organism_name",
        taxonomy_id_field="tax_id",
    )


@pytest.fixture()
def sample_records() -> list[dict[str, object]]:
    """Mixed-cellularity sample records."""
    return [
        {"assay_organism": "Homo sapiens", "assay_tax_id": 9606},
        {"assay_organism": "Escherichia coli", "assay_tax_id": 562},
        {"assay_organism": "Human immunodeficiency virus 1", "assay_tax_id": 11676},
        {"assay_organism": "Unknown organism", "assay_tax_id": None},
    ]


# ---------------------------------------------------------------------------
# Single-record classification
# ---------------------------------------------------------------------------


class TestClassify:
    """Tests for classify() method."""

    def test_classify_human_by_taxonomy(self, service: OrganismClassifier) -> None:
        result = service.classify("Homo sapiens", 9606)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source == "taxonomy_id"
        assert result.source_conflict is False

    def test_classify_ecoli_by_taxonomy(self, service: OrganismClassifier) -> None:
        result = service.classify("Escherichia coli", 562)
        assert result.organism_class == CellularityType.UNICELLULAR

    def test_classify_hiv_by_taxonomy(self, service: OrganismClassifier) -> None:
        result = service.classify("HIV-1", 11676)
        assert result.organism_class == CellularityType.ACELLULAR

    def test_classify_by_name_only(self, service: OrganismClassifier) -> None:
        result = service.classify("Homo sapiens", None)
        assert result.organism_class == CellularityType.MULTICELLULAR
        assert result.source == "organism_name"

    def test_classify_unresolved(self, service: OrganismClassifier) -> None:
        result = service.classify("Unknown organism", None)
        assert result.organism_class is None
        assert result.source == "unresolved"

    def test_classify_none_inputs(self, service: OrganismClassifier) -> None:
        result = service.classify(None, None)
        assert result.organism_class is None
        assert result.source == "unresolved"

    def test_classify_with_string_taxonomy_id(
        self, service: OrganismClassifier
    ) -> None:
        result = service.classify("Homo sapiens", "9606")
        assert result.organism_class == CellularityType.MULTICELLULAR


class TestGetCellularity:
    """Tests for get_cellularity() convenience method."""

    def test_returns_cellularity_type(self, service: OrganismClassifier) -> None:
        assert (
            service.get_cellularity("Homo sapiens", 9606)
            == CellularityType.MULTICELLULAR
        )

    def test_returns_none_for_unresolved(self, service: OrganismClassifier) -> None:
        assert service.get_cellularity("Unknown", None) is None


class TestNormalizeName:
    """Tests for normalize_name() method."""

    def test_lowercases(self, service: OrganismClassifier) -> None:
        assert service.normalize_name("Homo Sapiens") == "homo sapiens"

    def test_strips_parenthetical(self, service: OrganismClassifier) -> None:
        assert service.normalize_name("E. coli (strain K12)") == "e. coli"

    def test_resolves_alias(self, service: OrganismClassifier) -> None:
        assert service.normalize_name("HIV") == "human immunodeficiency virus 1"

    def test_none_input(self, service: OrganismClassifier) -> None:
        assert service.normalize_name(None) is None

    def test_empty_input(self, service: OrganismClassifier) -> None:
        assert service.normalize_name("") is None


# ---------------------------------------------------------------------------
# Batch operations
# ---------------------------------------------------------------------------


class TestClassifyRecords:
    """Tests for classify_records() method."""

    def test_returns_paired_tuples(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        results = service.classify_records(sample_records)
        assert len(results) == 4
        for record, result in results:
            assert isinstance(record, dict)
            assert isinstance(result, OrganismClassificationResult)

    def test_preserves_record_order(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        results = service.classify_records(sample_records)
        assert results[0][1].organism_class == CellularityType.MULTICELLULAR
        assert results[1][1].organism_class == CellularityType.UNICELLULAR
        assert results[2][1].organism_class == CellularityType.ACELLULAR
        assert results[3][1].organism_class is None

    def test_empty_input(self, service: OrganismClassifier) -> None:
        assert service.classify_records([]) == []


class TestEnrichRecords:
    """Tests for enrich_records() method."""

    def test_adds_classification_fields(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        enriched = service.enrich_records(sample_records)
        assert len(enriched) == 4

        human = enriched[0]
        assert human["organism_class"] == "multicellular"
        assert human["normalized_organism"] == "homo sapiens"
        assert human["classification_source"] == "taxonomy_id"

    def test_does_not_mutate_originals(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        service.enrich_records(sample_records)
        assert "organism_class" not in sample_records[0]

    def test_unresolved_gets_none_class(self, service: OrganismClassifier) -> None:
        records = [{"assay_organism": "Unknown", "assay_tax_id": None}]
        enriched = service.enrich_records(records)
        assert enriched[0]["organism_class"] is None
        assert enriched[0]["classification_source"] == "unresolved"

    def test_preserves_existing_fields(self, service: OrganismClassifier) -> None:
        records = [
            {"assay_organism": "Homo sapiens", "assay_tax_id": 9606, "extra": 42}
        ]
        enriched = service.enrich_records(records)
        assert enriched[0]["extra"] == 42

    def test_empty_input(self, service: OrganismClassifier) -> None:
        assert service.enrich_records([]) == []


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------


class TestFilterByCellularity:
    """Tests for filter_by_cellularity() method."""

    def test_include_multicellular(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(
            sample_records,
            include={CellularityType.MULTICELLULAR},
            keep_unresolved=False,
        )
        assert len(filtered) == 1
        assert filtered[0]["assay_organism"] == "Homo sapiens"

    def test_exclude_acellular(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(
            sample_records,
            exclude={CellularityType.ACELLULAR},
            keep_unresolved=False,
        )
        organisms = [r["assay_organism"] for r in filtered]
        assert "Human immunodeficiency virus 1" not in organisms
        assert "Homo sapiens" in organisms
        assert "Escherichia coli" in organisms

    def test_keep_unresolved_true(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(
            sample_records,
            include={CellularityType.MULTICELLULAR},
            keep_unresolved=True,
        )
        assert len(filtered) == 2  # human + unknown
        organisms = [r["assay_organism"] for r in filtered]
        assert "Homo sapiens" in organisms
        assert "Unknown organism" in organisms

    def test_keep_unresolved_false(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(
            sample_records,
            include={CellularityType.MULTICELLULAR},
            keep_unresolved=False,
        )
        assert len(filtered) == 1

    def test_no_filter_passes_all(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(sample_records)
        assert len(filtered) == len(sample_records)

    def test_include_multiple_types(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        filtered = service.filter_by_cellularity(
            sample_records,
            include={CellularityType.MULTICELLULAR, CellularityType.UNICELLULAR},
            keep_unresolved=False,
        )
        assert len(filtered) == 2

    def test_empty_input(self, service: OrganismClassifier) -> None:
        assert service.filter_by_cellularity([]) == []


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


class TestComputeStats:
    """Tests for compute_stats() method."""

    def test_stats_from_mixed_results(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        paired = service.classify_records(sample_records)
        results = [r for _, r in paired]
        stats = service.compute_stats(results)

        assert isinstance(stats, ClassificationStats)
        assert stats.total == 4
        assert stats.multicellular == 1
        assert stats.unicellular == 1
        assert stats.acellular == 1
        assert stats.unresolved == 1
        assert stats.conflict_count == 0

    def test_resolution_rate(
        self,
        service: OrganismClassifier,
        sample_records: list[dict[str, object]],
    ) -> None:
        paired = service.classify_records(sample_records)
        results = [r for _, r in paired]
        stats = service.compute_stats(results)
        assert stats.resolved_count == 3
        assert stats.resolution_rate == pytest.approx(0.75)

    def test_empty_stats(self, service: OrganismClassifier) -> None:
        stats = service.compute_stats([])
        assert stats.total == 0
        assert stats.resolution_rate == pytest.approx(0.0)

    def test_all_resolved(self, service: OrganismClassifier) -> None:
        records = [
            {"assay_organism": "Homo sapiens", "assay_tax_id": 9606},
            {"assay_organism": "Escherichia coli", "assay_tax_id": 562},
        ]
        paired = service.classify_records(records)
        results = [r for _, r in paired]
        stats = service.compute_stats(results)
        assert stats.resolution_rate == pytest.approx(1.0)
        assert stats.unresolved == 0


# ---------------------------------------------------------------------------
# Custom field names
# ---------------------------------------------------------------------------


class TestCustomFieldNames:
    """Tests for service with non-default field names."""

    def test_custom_fields(self, custom_service: OrganismClassifier) -> None:
        records = [{"organism_name": "Homo sapiens", "tax_id": 9606}]
        enriched = custom_service.enrich_records(records)
        assert enriched[0]["organism_class"] == "multicellular"

    def test_filter_with_custom_fields(
        self, custom_service: OrganismClassifier
    ) -> None:
        records = [
            {"organism_name": "Homo sapiens", "tax_id": 9606},
            {"organism_name": "Escherichia coli", "tax_id": 562},
        ]
        filtered = custom_service.filter_by_cellularity(
            records,
            include={CellularityType.UNICELLULAR},
            keep_unresolved=False,
        )
        assert len(filtered) == 1
        assert filtered[0]["organism_name"] == "Escherichia coli"

    def test_missing_fields_treated_as_none(
        self, custom_service: OrganismClassifier
    ) -> None:
        records = [{"some_other_field": "value"}]
        enriched = custom_service.enrich_records(records)
        assert enriched[0]["organism_class"] is None
        assert enriched[0]["classification_source"] == "unresolved"
