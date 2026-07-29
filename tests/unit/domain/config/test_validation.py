# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for validation configuration objects.

Tests for ValidationConfig, FieldValidation, CrossFieldValidation, ConditionalValidation.
"""

from __future__ import annotations

import math

import pytest

from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    DEFAULT_VALIDATION_CONFIG,
    FieldValidation,
    ValidationConfig,
)


@pytest.mark.unit
class TestValidationConfig:
    """Tests for ValidationConfig frozen dataclass."""

    def test_validation_config_default_values(self) -> None:
        config = ValidationConfig()
        assert config.min_publication_year == 1500
        assert config.max_publication_year == 2100
        assert math.isclose(config.min_molecular_weight, 10.0)
        assert math.isclose(config.max_molecular_weight, 10_000.0)
        assert config.max_pmid == 10_000_000_000
        assert config.max_taxonomy_id == 10_000_000
        assert math.isclose(config.min_pchembl_value, 0.0)
        assert math.isclose(config.max_pchembl_value, 15.0)
        assert config.molecular_weight_precision == 10

    def test_validation_config_custom_publication_year_values(self) -> None:
        config = ValidationConfig(
            min_publication_year=2000,
            max_publication_year=2025,
        )
        assert config.min_publication_year == 2000
        assert config.max_publication_year == 2025

    def test_invalid_publication_year_range_raises(self) -> None:
        with pytest.raises(ValueError, match="min_publication_year"):
            ValidationConfig(min_publication_year=2100, max_publication_year=1500)

    def test_invalid_molecular_weight_range_raises(self) -> None:
        with pytest.raises(ValueError, match="min_molecular_weight"):
            ValidationConfig(min_molecular_weight=10000.0, max_molecular_weight=10.0)

    def test_validation_config__pchembl_range_raises__bfb4466b(self) -> None:
        with pytest.raises(ValueError, match="min_pchembl_value"):
            ValidationConfig(min_pchembl_value=15.0, max_pchembl_value=0.0)

    def test_validation_config__precision_raises__a8db7fce(self) -> None:
        with pytest.raises(ValueError, match="molecular_weight_precision"):
            ValidationConfig(molecular_weight_precision=-1)

    def test_default_singleton(self) -> None:
        assert DEFAULT_VALIDATION_CONFIG is not None
        assert isinstance(DEFAULT_VALIDATION_CONFIG, ValidationConfig)

    def test_validation_config__frozen__06babd90(self) -> None:
        config = ValidationConfig()
        with pytest.raises(AttributeError):
            config.min_publication_year = 2000  # type: ignore[misc]


@pytest.mark.unit
class TestFieldValidation:
    """Tests for FieldValidation frozen dataclass."""

    def test_required_field(self) -> None:
        fv = FieldValidation(field="entity_id", validation_type="required")
        assert fv.field == "entity_id"
        assert fv.validation_type == "required"
        assert fv.nullable is True
        assert fv.severity == "error"

    def test_range_validation(self) -> None:
        fv = FieldValidation(
            field="year",
            validation_type="range",
            min_value=1500,
            max_value=2100,
        )
        assert fv.min_value == 1500
        assert fv.max_value == 2100

    def test_pattern_validation(self) -> None:
        fv = FieldValidation(
            field="doi",
            validation_type="pattern",
            pattern=r"^10\.\d{4,}/\S+$",
        )
        assert fv.pattern is not None

    def test_enum_validation(self) -> None:
        fv = FieldValidation(
            field="status",
            validation_type="enum",
            allowed=("active", "inactive"),
        )
        assert fv.allowed == ("active", "inactive")

    def test_field_validation__to_tuple_conversion__c80dac45(self) -> None:
        fv = FieldValidation(
            field="status",
            validation_type="enum",
            allowed=["active", "inactive"],  # type: ignore[arg-type]
        )
        assert isinstance(fv.allowed, tuple)

    def test_effective_severity_default(self) -> None:
        fv = FieldValidation(field="x", validation_type="required", severity="error")
        assert fv.effective_severity() == "error"
        assert fv.effective_severity(is_enricher=True) == "error"

    def test_effective_severity_enricher_override(self) -> None:
        fv = FieldValidation(
            field="x",
            validation_type="required",
            severity="error",
            severity_enricher="warn",
        )
        assert fv.effective_severity(is_enricher=False) == "error"
        assert fv.effective_severity(is_enricher=True) == "warn"


@pytest.mark.unit
class TestCrossFieldValidation:
    """Tests for CrossFieldValidation frozen dataclass."""

    def test_all_present_condition(self) -> None:
        cfv = CrossFieldValidation(
            name="both_required",
            fields=("field_a", "field_b"),
            condition="all_present",
        )
        assert cfv.condition == "all_present"
        assert cfv.fields == ("field_a", "field_b")

    def test_cross_field_validation__to_tuple_conversion__9f09a642(self) -> None:
        cfv = CrossFieldValidation(
            name="test",
            fields=["a", "b"],  # type: ignore[arg-type]
            condition="any_present",
        )
        assert isinstance(cfv.fields, tuple)

    def test_conditional_required(self) -> None:
        cfv = CrossFieldValidation(
            name="doi_needs_year",
            fields=("doi", "year"),
            condition="conditional_required",
            trigger_field="doi",
            required_field="year",
        )
        assert cfv.trigger_field == "doi"
        assert cfv.required_field == "year"


@pytest.mark.unit
class TestConditionalValidation:
    """Tests for ConditionalValidation frozen dataclass."""

    def test_conditional_validation__basic_creation__00a374cd(self) -> None:
        cv = ConditionalValidation(
            name="activity_type_check",
            condition_field="type",
            condition_value="IC50",
        )
        assert cv.name == "activity_type_check"
        assert cv.condition_operator == "eq"

    def test_in_operator(self) -> None:
        cv = ConditionalValidation(
            name="check",
            condition_field="status",
            condition_value=("active", "pending"),
            condition_operator="in",
        )
        assert cv.condition_operator == "in"
        assert cv.condition_value == ("active", "pending")

    def test_conditional_validation__to_tuple_conversion__e6bd2320(self) -> None:
        cv = ConditionalValidation(
            name="check",
            condition_field="status",
            condition_value=["active", "pending"],  # type: ignore[arg-type]
            condition_operator="in",
        )
        assert isinstance(cv.condition_value, tuple)
