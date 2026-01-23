"""Unit tests for SinkMetadataConfig schema.

Tests governance metadata parsing from pipeline YAML configurations.
"""

from __future__ import annotations

import pytest

from bioetl.infrastructure.schemas.pipeline_config import (
    SinkLayerConfig,
    SinkLineageConfig,
    SinkMetadataConfig,
    SinkQualityExpectationsConfig,
)


class TestSinkLineageConfig:
    """Tests for SinkLineageConfig schema."""

    def test_lineage_config_defaults(self) -> None:
        """Test SinkLineageConfig has correct defaults."""
        config = SinkLineageConfig()

        assert config.source_system is None
        assert config.source_version is None
        assert config.extraction_method is None
        assert config.source_layer is None
        assert config.transformations == []
        assert config.filters_applied is None
        assert config.business_domain is None
        assert config.use_cases == []

    def test_lineage_config_with_values(self) -> None:
        """Test SinkLineageConfig with all values."""
        config = SinkLineageConfig(
            source_system="chembl",
            source_version="v33",
            extraction_method="api",
            source_layer="bronze",
            transformations=["dedup", "normalize"],
            filters_applied=True,
            business_domain="drug-discovery",
            use_cases=["ml-training", "analytics"],
        )

        assert config.source_system == "chembl"
        assert config.source_version == "v33"
        assert config.extraction_method == "api"
        assert config.source_layer == "bronze"
        assert config.transformations == ["dedup", "normalize"]
        assert config.filters_applied is True
        assert config.business_domain == "drug-discovery"
        assert config.use_cases == ["ml-training", "analytics"]


class TestSinkQualityExpectationsConfig:
    """Tests for SinkQualityExpectationsConfig schema."""

    def test_quality_expectations_defaults(self) -> None:
        """Test SinkQualityExpectationsConfig has correct defaults."""
        config = SinkQualityExpectationsConfig()

        assert config.completeness is None
        assert config.accuracy is None

    def test_quality_expectations_with_values(self) -> None:
        """Test SinkQualityExpectationsConfig with values."""
        config = SinkQualityExpectationsConfig(
            completeness=0.95,
            accuracy=0.99,
        )

        assert config.completeness == 0.95
        assert config.accuracy == 0.99

    def test_quality_expectations_validates_range(self) -> None:
        """Test quality expectations validates 0-1 range."""
        with pytest.raises(ValueError):
            SinkQualityExpectationsConfig(completeness=1.5)

        with pytest.raises(ValueError):
            SinkQualityExpectationsConfig(accuracy=-0.1)


class TestSinkMetadataConfig:
    """Tests for SinkMetadataConfig schema."""

    def test_metadata_config_defaults(self) -> None:
        """Test SinkMetadataConfig has correct defaults."""
        config = SinkMetadataConfig()

        assert config.owner is None
        assert config.steward is None
        assert config.description is None
        assert config.tags == []
        assert config.retention_days is None
        assert config.sla_freshness_hours is None
        assert config.classification is None
        assert config.lineage is not None
        assert config.quality_expectations is not None

    def test_metadata_config_with_all_fields(self) -> None:
        """Test SinkMetadataConfig with all fields."""
        config = SinkMetadataConfig(
            owner="data-team",
            steward="chembl-owner",
            description="Raw ChEMBL activity data",
            tags=["chembl", "activity", "raw"],
            retention_days=90,
            sla_freshness_hours=24,
            classification="public",
            lineage=SinkLineageConfig(
                source_system="chembl",
                extraction_method="api",
            ),
            quality_expectations=SinkQualityExpectationsConfig(
                completeness=0.95,
            ),
        )

        assert config.owner == "data-team"
        assert config.steward == "chembl-owner"
        assert config.description == "Raw ChEMBL activity data"
        assert config.tags == ["chembl", "activity", "raw"]
        assert config.retention_days == 90
        assert config.sla_freshness_hours == 24
        assert config.classification == "public"
        assert config.lineage.source_system == "chembl"
        assert config.quality_expectations.completeness == 0.95

    def test_metadata_config_to_domain(self) -> None:
        """Test SinkMetadataConfig.to_domain() conversion."""
        config = SinkMetadataConfig(
            owner="data-team",
            steward="chembl-owner",
            description="Raw ChEMBL activity data",
            tags=["chembl", "activity", "raw"],
            retention_days=90,
            sla_freshness_hours=24,
            lineage=SinkLineageConfig(
                source_system="chembl",
                source_version="v33",
                extraction_method="api",
            ),
            quality_expectations=SinkQualityExpectationsConfig(
                completeness=0.95,
                accuracy=0.99,
            ),
        )

        domain = config.to_domain()

        assert domain.owner == "data-team"
        assert domain.steward == "chembl-owner"
        assert domain.description == "Raw ChEMBL activity data"
        assert domain.tags == ["chembl", "activity", "raw"]
        assert domain.retention_days == 90
        assert domain.sla_freshness_hours == 24
        assert domain.lineage.source_system == "chembl"
        assert domain.lineage.source_version == "v33"
        assert domain.lineage.extraction_method == "api"
        assert domain.quality_expectations.completeness == 0.95
        assert domain.quality_expectations.accuracy == 0.99

    def test_metadata_config_to_domain_with_defaults(self) -> None:
        """Test SinkMetadataConfig.to_domain() with default values."""
        config = SinkMetadataConfig()

        domain = config.to_domain()

        assert domain.owner is None
        assert domain.tags == []
        assert domain.lineage.source_system is None
        assert domain.lineage.transformations == []
        assert domain.quality_expectations.completeness is None

    def test_retention_days_validates_min(self) -> None:
        """Test retention_days validates minimum value."""
        with pytest.raises(ValueError):
            SinkMetadataConfig(retention_days=0)

    def test_sla_freshness_hours_validates_min(self) -> None:
        """Test sla_freshness_hours validates minimum value."""
        with pytest.raises(ValueError):
            SinkMetadataConfig(sla_freshness_hours=0)


class TestSinkLayerConfigWithMetadata:
    """Tests for SinkLayerConfig with metadata field."""

    def test_sink_layer_config_has_metadata_field(self) -> None:
        """Test SinkLayerConfig has optional metadata field."""
        config = SinkLayerConfig()

        assert config.metadata is None

    def test_sink_layer_config_with_metadata(self) -> None:
        """Test SinkLayerConfig with metadata configuration."""
        config = SinkLayerConfig(
            enabled=True,
            format="delta",
            save_metadata=True,
            metadata=SinkMetadataConfig(
                owner="data-team",
                description="Test data",
                tags=["test"],
            ),
        )

        assert config.save_metadata is True
        assert config.metadata is not None
        assert config.metadata.owner == "data-team"
        assert config.metadata.description == "Test data"
        assert config.metadata.tags == ["test"]

    def test_sink_layer_config_metadata_from_dict(self) -> None:
        """Test SinkLayerConfig can parse metadata from dict (YAML-like)."""
        config = SinkLayerConfig.model_validate(
            {
                "enabled": True,
                "format": "delta",
                "save_metadata": True,
                "metadata": {
                    "owner": "data-team",
                    "steward": "chembl-owner",
                    "description": "Raw ChEMBL data",
                    "tags": ["chembl", "raw"],
                    "retention_days": 90,
                    "lineage": {
                        "source_system": "chembl",
                        "extraction_method": "api",
                    },
                },
            }
        )

        assert config.metadata is not None
        assert config.metadata.owner == "data-team"
        assert config.metadata.steward == "chembl-owner"
        assert config.metadata.retention_days == 90
        assert config.metadata.lineage.source_system == "chembl"


class TestGovernanceMetadataFullPipeline:
    """Integration tests for full governance metadata flow."""

    def test_bronze_governance_from_yaml_to_domain(self) -> None:
        """Test Bronze governance metadata flow from YAML config to domain."""
        # Simulate YAML config parsing
        sink_config = SinkLayerConfig.model_validate(
            {
                "enabled": True,
                "format": "jsonl",
                "save_metadata": True,
                "metadata": {
                    "owner": "data-team",
                    "steward": "chembl-owner",
                    "description": "Raw ChEMBL activity data",
                    "tags": ["chembl", "activity", "raw"],
                    "retention_days": 90,
                    "sla_freshness_hours": 24,
                    "lineage": {
                        "source_system": "chembl",
                        "source_version": "v33",
                        "extraction_method": "api",
                    },
                },
            }
        )

        # Convert to domain model
        assert sink_config.metadata is not None
        governance = sink_config.metadata.to_domain()

        # Verify all fields
        assert governance.owner == "data-team"
        assert governance.steward == "chembl-owner"
        assert governance.description == "Raw ChEMBL activity data"
        assert governance.tags == ["chembl", "activity", "raw"]
        assert governance.retention_days == 90
        assert governance.sla_freshness_hours == 24
        assert governance.lineage.source_system == "chembl"
        assert governance.lineage.source_version == "v33"
        assert governance.lineage.extraction_method == "api"

    def test_silver_governance_from_yaml_to_domain(self) -> None:
        """Test Silver governance metadata flow from YAML config to domain."""
        sink_config = SinkLayerConfig.model_validate(
            {
                "enabled": True,
                "format": "delta",
                "save_metadata": True,
                "metadata": {
                    "description": "Cleansed ChEMBL activity data",
                    "tags": ["chembl", "activity", "silver", "validated"],
                    "lineage": {
                        "source_layer": "bronze",
                        "transformations": ["deduplication", "normalization"],
                    },
                    "quality_expectations": {
                        "completeness": 0.95,
                        "accuracy": 0.99,
                    },
                },
            }
        )

        assert sink_config.metadata is not None
        governance = sink_config.metadata.to_domain()

        assert governance.lineage.source_layer == "bronze"
        assert "deduplication" in governance.lineage.transformations
        assert governance.quality_expectations.completeness == 0.95
        assert governance.quality_expectations.accuracy == 0.99

    def test_gold_governance_from_yaml_to_domain(self) -> None:
        """Test Gold governance metadata flow from YAML config to domain."""
        sink_config = SinkLayerConfig.model_validate(
            {
                "enabled": True,
                "format": "delta",
                "save_metadata": True,
                "metadata": {
                    "description": "Business-ready ChEMBL activity data",
                    "tags": ["chembl", "activity", "gold", "ml-ready"],
                    "lineage": {
                        "source_layer": "silver",
                        "filters_applied": True,
                        "business_domain": "drug-discovery",
                        "use_cases": ["ml-training", "reporting", "analytics"],
                    },
                },
            }
        )

        assert sink_config.metadata is not None
        governance = sink_config.metadata.to_domain()

        assert governance.lineage.source_layer == "silver"
        assert governance.lineage.filters_applied is True
        assert governance.lineage.business_domain == "drug-discovery"
        assert "ml-training" in governance.lineage.use_cases
