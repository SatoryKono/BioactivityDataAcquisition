"""Unit tests for AggregationValidator service."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.aggregation_validator import (
    AggregationConfig,
    AggregationProvenance,
    AggregationValidator,
)
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


pytestmark = pytest.mark.unit


class TestAggregationValidator:
    """Tests for AggregationValidator."""

    @pytest.fixture
    def validator(self) -> AggregationValidator:
        """Create an AggregationValidator instance."""
        return AggregationValidator()

    @pytest.fixture
    def valid_config(self) -> AggregationConfig:
        """Create a valid aggregation configuration."""
        return AggregationConfig(
            group_by=["molecule_id", "assay_type"],
            aggregations={
                "activity_count": "count",
                "avg_activity": "avg",
                "max_activity": "max",
            },
            source_field="activity_value",
            provenance_tracking=True,
        )

    @pytest.fixture
    def source_schema(self) -> dict:
        """Create a sample source schema."""
        return {
            "properties": {
                "molecule_id": {"type": "string"},
                "assay_type": {"type": "string"},
                "activity_value": {"type": "number"},
                "unit": {"type": "string"},
                "source": {"type": "string"},
            },
        }

    # ==========================================================================
    # validate_aggregation_config() tests
    # ==========================================================================

    def test_validate_valid_config(
        self,
        validator: AggregationValidator,
        valid_config: AggregationConfig,
        source_schema: dict,
    ) -> None:
        """Test validation of a completely valid configuration."""
        result = validator.validate_aggregation_config(valid_config, source_schema)

        assert result.issues == []
        assert result.validation_layer == ValidationLayer.DEEP_PREFLIGHT
        assert result.is_valid()

    def test_validate_missing_group_by(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when group_by fields are missing."""
        config = AggregationConfig(
            group_by=[],  # Empty group_by
            aggregations={"activity_count": "count"},
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_001
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "missing group_by fields" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_group_by_field_not_in_schema(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when group_by field is not in source schema."""
        config = AggregationConfig(
            group_by=["molecule_id", "nonexistent_field"],
            aggregations={"activity_count": "count"},
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_002
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "not found in source schema" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_missing_aggregations(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when aggregations are missing."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={},  # Empty aggregations
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_003
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "missing aggregations" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_unsupported_aggregation_function(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when using unsupported aggregation function."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={"activity_count": "invalid_function"},
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_004
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "Unsupported aggregation function" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_source_field_not_in_schema(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when source field is not in source schema."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={"activity_count": "count"},
            source_field="nonexistent_source",
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_005
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "not found in source schema" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_field_shadowing(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation when aggregation field shadows group_by field."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={"molecule_id": "count"},  # Shadows group_by field
        )

        result = validator.validate_aggregation_config(config, source_schema)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_AGG_006
        assert result.issues[0].severity == ValidationSeverity.WARNING
        assert "shadows group_by field" in result.issues[0].message
        # Should still be valid since it's just a warning
        assert result.is_valid()

    def test_validate_multiple_issues(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test validation with multiple issues."""
        config = AggregationConfig(
            group_by=["nonexistent_group"],
            aggregations={"invalid_agg": "bad_function"},
            source_field="nonexistent_source",
        )

        result = validator.validate_aggregation_config(config, source_schema)

        # Should have 3 issues: missing group_by field, unsupported function, missing source field
        assert len(result.issues) == 3
        assert not result.is_valid()

        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_AGG_002 in issue_codes  # Missing group_by field
        assert IssueCode.CMP_PF_AGG_004 in issue_codes  # Unsupported function
        assert IssueCode.CMP_PF_AGG_005 in issue_codes  # Missing source field

    # ==========================================================================
    # validate_post_aggregation_uniqueness() tests
    # ==========================================================================

    def test_validate_post_aggregation_uniqueness_valid(
        self, validator: AggregationValidator
    ) -> None:
        """Test post-aggregation uniqueness validation with unique groups."""
        aggregation_results = [
            {"molecule_id": "mol1", "assay_type": "IC50", "activity_count": 5},
            {"molecule_id": "mol2", "assay_type": "EC50", "activity_count": 3},
            {"molecule_id": "mol3", "assay_type": "IC50", "activity_count": 7},
        ]

        result = validator.validate_post_aggregation_uniqueness(
            aggregation_results, ["molecule_id", "assay_type"]
        )

        assert result.issues == []
        assert result.validation_layer == ValidationLayer.RUNTIME_GUARD
        assert result.is_valid()

    def test_validate_post_aggregation_uniqueness_duplicates(
        self, validator: AggregationValidator
    ) -> None:
        """Test post-aggregation uniqueness validation with duplicate groups."""
        aggregation_results = [
            {"molecule_id": "mol1", "assay_type": "IC50", "activity_count": 5},
            {
                "molecule_id": "mol1",
                "assay_type": "IC50",
                "activity_count": 8,
            },  # Duplicate
            {"molecule_id": "mol2", "assay_type": "EC50", "activity_count": 3},
        ]

        result = validator.validate_post_aggregation_uniqueness(
            aggregation_results, ["molecule_id", "assay_type"]
        )

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_RT_GRAIN_001
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "uniqueness violation" in result.issues[0].message
        assert not result.is_valid()

        # Check details contain duplicate information
        details = result.issues[0].details
        assert details["duplicate_count"] == 1
        assert details["group_by_fields"] == ["molecule_id", "assay_type"]
        assert len(details["sample_duplicates"]) == 1

    def test_validate_post_aggregation_uniqueness_missing_fields(
        self, validator: AggregationValidator
    ) -> None:
        """Test post-aggregation uniqueness validation with missing group_by fields."""
        aggregation_results = [
            {"molecule_id": "mol1", "activity_count": 5},  # Missing assay_type
            {"molecule_id": "mol1", "assay_type": "IC50", "activity_count": 8},
            {"molecule_id": "mol2", "assay_type": "EC50", "activity_count": 3},
        ]

        result = validator.validate_post_aggregation_uniqueness(
            aggregation_results, ["molecule_id", "assay_type"]
        )

        # Should still work, treating missing fields as "MISSING"
        assert result.issues == []
        assert result.is_valid()

    # ==========================================================================
    # generate_aggregation_provenance() tests
    # ==========================================================================

    def test_generate_aggregation_provenance(
        self, validator: AggregationValidator, valid_config: AggregationConfig
    ) -> None:
        """Test generation of aggregation provenance."""
        source_records = [
            {"activity_value": 10.5, "molecule_id": "mol1", "assay_type": "IC50"},
            {"activity_value": 20.3, "molecule_id": "mol1", "assay_type": "IC50"},
            {"activity_value": 15.2, "molecule_id": "mol2", "assay_type": "EC50"},
            {"activity_value": 5.8, "molecule_id": "mol2", "assay_type": "EC50"},
        ]

        provenance = validator.generate_aggregation_provenance(
            valid_config, source_records
        )

        # Should have 3 provenance records (one for each aggregation field)
        assert len(provenance) == 3

        # Check each provenance record
        for prov in provenance:
            assert isinstance(prov, AggregationProvenance)
            assert prov.source_field == "activity_value"  # From config
            assert prov.source_count == 4  # All records have activity_value

        # Check specific fields
        field_names = {prov.field_name for prov in provenance}
        assert field_names == {"activity_count", "avg_activity", "max_activity"}

        functions = {prov.aggregation_function for prov in provenance}
        assert functions == {"count", "avg", "max"}

    def test_generate_aggregation_provenance_missing_fields(
        self, validator: AggregationValidator
    ) -> None:
        """Test provenance generation when some source records are missing fields."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={
                "activity_count": "count",
                "avg_activity": "avg",
            },
            source_field="activity_value",
        )

        source_records = [
            {"activity_value": 10.5, "molecule_id": "mol1"},
            {"molecule_id": "mol2"},  # Missing activity_value
            {"activity_value": 15.2, "molecule_id": "mol3"},
        ]

        provenance = validator.generate_aggregation_provenance(config, source_records)

        assert len(provenance) == 2

        for prov in provenance:
            assert prov.source_count == 2  # Only 2 records have activity_value

    def test_generate_aggregation_provenance_no_source_field(
        self, validator: AggregationValidator
    ) -> None:
        """Test provenance generation when no source field is specified."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={
                "activity_count": "count",
                "avg_activity": "avg",
            },
            # No source_field specified
        )

        source_records = [
            {"activity_value": 10.5, "molecule_id": "mol1"},
            {"activity_value": 20.3, "molecule_id": "mol1"},
        ]

        provenance = validator.generate_aggregation_provenance(config, source_records)

        assert len(provenance) == 2

        # Source field should default to the aggregation field name
        for prov in provenance:
            assert prov.source_field == prov.field_name

    # ==========================================================================
    # Edge cases and schema variations
    # ==========================================================================

    def test_validate_with_alternative_schema_format(
        self, validator: AggregationValidator
    ) -> None:
        """Test validation with alternative schema format (fields instead of properties)."""
        config = AggregationConfig(
            group_by=["molecule_id"],
            aggregations={"activity_count": "count"},
        )

        # Schema with "fields" instead of "properties"
        schema = {"fields": ["molecule_id", "activity_value", "unit"]}

        result = validator.validate_aggregation_config(config, schema)
        assert result.is_valid()

    def test_validate_with_nested_schema(self, validator: AggregationValidator) -> None:
        """Test validation with nested schema structure."""
        config = AggregationConfig(
            group_by=["data"],  # The top-level field is "data"
            aggregations={"activity_count": "count"},
        )

        # Nested schema structure
        schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "object",
                    "properties": {
                        "molecule_id": {"type": "string"},
                        "activity_value": {"type": "number"},
                    },
                }
            },
        }

        result = validator.validate_aggregation_config(config, schema)
        # Should find "data" field at top level
        assert result.is_valid()

    def test_supported_aggregation_functions(
        self, validator: AggregationValidator, source_schema: dict
    ) -> None:
        """Test all supported aggregation functions."""
        supported_functions = [
            "sum",
            "avg",
            "min",
            "max",
            "count",
            "first",
            "last",
            "concat",
            "list",
        ]

        for function in supported_functions:
            config = AggregationConfig(
                group_by=["molecule_id"],
                aggregations={f"test_{function}": function},
            )
            result = validator.validate_aggregation_config(config, source_schema)
            assert result.is_valid(), f"Function {function} should be supported"
