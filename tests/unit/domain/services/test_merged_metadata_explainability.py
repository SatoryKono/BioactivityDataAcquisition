"""Unit tests for MergedMetadataExplainer."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedFieldExplanation,
    MergedRecordExplanation,
    MergedMetadataExplainer,
)
from bioetl.domain.models.metadata import CompositeOutputExt
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


class TestMergedMetadataExplainer:
    """Tests for MergedMetadataExplainer."""

    @pytest.fixture
    def service(self) -> MergedMetadataExplainer:
        """Create a MergedMetadataExplainer instance."""
        return MergedMetadataExplainer()

    @pytest.fixture
    def composite_metadata(self) -> CompositeOutputExt:
        """Create sample composite metadata."""
        return CompositeOutputExt(
            composite_run_id="test_run_123",
            source_providers=["chembl", "pubchem"],
            enrichment_status={"uniprot": "applied", "go": "not_applied"},
            lineage_created_at=FIXED_TEST_TIME,
        )

    @pytest.fixture
    def field_priorities(self) -> dict[str, dict]:
        """Create sample field priorities configuration."""
        return {
            "activity_value": {
                "priority": ["chembl", "pubchem"],
                "source": "chembl",
                "fallback": "keep_first",
                "conflict_resolution": "priority_based",
            },
            "assay_type": {
                "priority": ["pubchem", "chembl"],
                "source": "pubchem",
                "fallback": "keep_first",
            },
        }

    @pytest.fixture
    def sample_record(self) -> dict:
        """Create a sample record for testing."""
        return {
            "_record_id": "mol123",
            "molecule_id": "CHEMBL123",
            "activity_value": 10.5,
            "assay_type": "IC50",
            "source": "chembl",
        }

    # ==========================================================================
    # generate_field_explanation() tests
    # ==========================================================================

    def test_generate_field_explanation_basic(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
    ) -> None:
        """Test generation of basic field explanation."""
        result = service.generate_field_explanation(
            "activity_value",
            sample_record,
            composite_metadata,
        )

        assert isinstance(result, MergedFieldExplanation)
        assert result.field_name == "activity_value"
        assert result.source_providers == ["chembl", "pubchem"]
        assert result.merge_strategy == "prioritize"
        assert result.final_value_source == "chembl"
        assert result.enrichment_applied == ["uniprot"]

    def test_generate_field_explanation_with_priorities(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
        field_priorities: dict[str, dict],
    ) -> None:
        """Test field explanation with priority configuration."""
        result = service.generate_field_explanation(
            "activity_value",
            sample_record,
            composite_metadata,
            field_priorities,
        )

        assert result.priority_order == ["chembl", "pubchem"]
        assert result.conflict_resolution == "priority_based"

    def test_generate_field_explanation_no_enrichments(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
    ) -> None:
        """Test field explanation when no enrichments applied."""
        # Create metadata without enrichments
        metadata = CompositeOutputExt(
            composite_run_id="test_run_123",
            source_providers=["chembl", "pubchem"],
            enrichment_status={},
        )

        result = service.generate_field_explanation(
            "activity_value",
            sample_record,
            metadata,
        )

        assert result.enrichment_applied is None

    # ==========================================================================
    # generate_record_explanation() tests
    # ==========================================================================

    def test_generate_record_explanation_basic(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
    ) -> None:
        """Test generation of complete record explanation."""
        result = service.generate_record_explanation(
            "mol123",
            sample_record,
            composite_metadata,
        )

        assert isinstance(result, MergedRecordExplanation)
        assert result.record_id == "mol123"
        assert result.composite_run_id == "test_run_123"
        assert result.source_providers == ["chembl", "pubchem"]
        assert (
            len(result.field_explanations) == 4
        )  # activity_value, assay_type, source, molecule_id
        assert result.merge_strategy == "prioritize"
        assert result.conflict_count >= 0
        assert result.enrichment_count >= 0

    def test_generate_record_explanation_with_priorities(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
        field_priorities: dict[str, dict],
    ) -> None:
        """Test record explanation with field priorities."""
        result = service.generate_record_explanation(
            "mol123",
            sample_record,
            composite_metadata,
            field_priorities,
        )

        # Find activity_value explanation
        activity_explanation = next(
            (
                exp
                for exp in result.field_explanations
                if exp.field_name == "activity_value"
            ),
            None,
        )

        assert activity_explanation is not None
        assert activity_explanation.priority_order == ["chembl", "pubchem"]

    def test_generate_record_explanation_empty_record(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
    ) -> None:
        """Test record explanation with empty record."""
        result = service.generate_record_explanation(
            "empty_record",
            {},
            composite_metadata,
        )

        assert result.record_id == "empty_record"
        assert len(result.field_explanations) == 0
        assert result.conflict_count == 0
        assert result.enrichment_count == 0

    # ==========================================================================
    # generate_explainability_metadata() tests
    # ==========================================================================

    def test_generate_explainability_metadata_multiple_records(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
    ) -> None:
        """Test generation of explainability for multiple records."""
        records = [
            sample_record,
            {
                "_record_id": "mol456",
                "molecule_id": "CHEMBL456",
                "activity_value": 20.3,
                "assay_type": "EC50",
            },
        ]

        results = service.generate_explainability_metadata(
            records,
            composite_metadata,
        )

        assert len(results) == 2
        assert results[0].record_id == "mol123"
        assert results[1].record_id == "mol456"

    # ==========================================================================
    # generate_explainability_summary() tests
    # ==========================================================================

    def test_generate_explainability_summary_empty(
        self, service: MergedMetadataExplainer
    ) -> None:
        """Test summary generation with empty explanations."""
        summary = service.generate_explainability_summary([])

        assert summary["record_count"] == 0
        assert summary["source_provider_distribution"] == {}
        assert summary["merge_strategy_distribution"] == {}
        assert summary["conflict_summary"]["total_conflicts"] == 0
        assert summary["conflict_summary"]["conflict_rate"] == pytest.approx(0.0)
        assert summary["enrichment_summary"]["total_enrichments"] == 0
        assert summary["enrichment_summary"]["enrichment_rate"] == pytest.approx(0.0)

    def test_generate_explainability_summary_with_data(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
        sample_record: dict,
        field_priorities: dict[str, dict],
    ) -> None:
        """Test summary generation with actual data."""
        # Generate explanations for multiple records
        explanations = []
        for i in range(3):
            record_id = f"record_{i}"
            record = {
                "_record_id": record_id,
                "molecule_id": f"CHEMBL{i}",
                "activity_value": 10.0 + i,
                "assay_type": "IC50",
            }

            explanation = service.generate_record_explanation(
                record_id,
                record,
                composite_metadata,
                field_priorities,
            )
            explanations.append(explanation)

        summary = service.generate_explainability_summary(explanations)

        assert summary["record_count"] == 3
        assert summary["field_count"] > 0
        assert summary["avg_fields_per_record"] > 0
        assert "chembl" in summary["source_provider_distribution"]
        assert "pubchem" in summary["source_provider_distribution"]
        assert summary["conflict_summary"]["total_conflicts"] >= 0
        assert summary["enrichment_summary"]["total_enrichments"] >= 0

    # ==========================================================================
    # generate_field_priority_explanation() tests
    # ==========================================================================

    def test_generate_field_priority_explanation(
        self,
        service: MergedMetadataExplainer,
        field_priorities: dict[str, dict],
    ) -> None:
        """Test generation of field priority explanations."""
        results = service.generate_field_priority_explanation(field_priorities)

        assert len(results) == 2

        # Check activity_value explanation
        activity_explanation = next(
            (exp for exp in results if exp["field_name"] == "activity_value"), None
        )
        assert activity_explanation is not None
        assert activity_explanation["priority_order"] == ["chembl", "pubchem"]
        assert activity_explanation["source"] == "chembl"
        assert activity_explanation["conflict_resolution"] == "priority_based"

    def test_generate_field_priority_explanation_empty(
        self, service: MergedMetadataExplainer
    ) -> None:
        """Test field priority explanation with empty input."""
        results = service.generate_field_priority_explanation({})
        assert results == []

    # ==========================================================================
    # Edge cases and error handling
    # ==========================================================================

    def test_record_without_standard_id_fields(
        self,
        service: MergedMetadataExplainer,
        composite_metadata: CompositeOutputExt,
    ) -> None:
        """Test record explanation when standard ID fields are missing."""
        record = {"custom_id": "custom123", "data": "value"}

        result = service.generate_record_explanation(
            "test",
            record,
            composite_metadata,
        )

        assert result.record_id == "test"  # Should use provided ID
        assert len(result.field_explanations) == 2  # custom_id and data

    def test_factory_function(self) -> None:
        """Test the factory function."""
        service = create_merged_metadata_explainability_service()
        assert isinstance(service, MergedMetadataExplainer)


# Helper function for easier testing


def create_merged_metadata_explainability_service() -> MergedMetadataExplainer:
    """Factory function for MergedMetadataExplainer."""
    return MergedMetadataExplainer()
