"""Unit tests for DQ config Pydantic schemas.

Tests validation logic for standalone DQ configuration files.
Covers ThresholdsConfig and DQConfigFile schema validation.

Requirements:
- REQ-CONF-001: DQ thresholds validation
- REQ-CONF-002: Field validation configuration
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from bioetl.infrastructure.schemas.dq_config import (
    DQConfigFile,
    ThresholdsConfig,
)
from bioetl.infrastructure.schemas.pipeline_config import (
    ConditionalValidationConfig,
    CrossFieldValidationConfig,
    DQReportYamlConfig,
    FieldValidationConfig,
)

pytestmark = pytest.mark.unit


class TestThresholdsConfig:
    """Tests for ThresholdsConfig validation."""

    def test_thresholds_config__default_values__d770af11(self) -> None:
        """Default thresholds should be 0.05/0.20."""
        config = ThresholdsConfig()
        assert config.soft_fail == pytest.approx(0.05)
        assert config.hard_fail == pytest.approx(0.20)

    def test_valid_thresholds(self) -> None:
        """Valid thresholds should pass validation."""
        config = ThresholdsConfig(soft_fail=0.03, hard_fail=0.10)
        assert config.soft_fail == pytest.approx(0.03)
        assert config.hard_fail == pytest.approx(0.10)

    def test_thresholds_config__be_less_than_hard__d2c5b480(self) -> None:
        """soft_fail >= hard_fail should raise ValidationError."""
        with pytest.raises(ValidationError, match=r"soft_fail.*must be < hard_fail"):
            ThresholdsConfig(soft_fail=0.20, hard_fail=0.10)

    def test_equal_thresholds_invalid(self) -> None:
        """Equal thresholds should raise ValidationError."""
        with pytest.raises(ValidationError, match=r"soft_fail.*must be < hard_fail"):
            ThresholdsConfig(soft_fail=0.10, hard_fail=0.10)

    def test_threshold_bounds_soft_negative(self) -> None:
        """Negative soft_fail should raise ValidationError."""
        with pytest.raises(ValidationError, match="greater than or equal to 0"):
            ThresholdsConfig(soft_fail=-0.1, hard_fail=0.20)

    def test_threshold_bounds_hard_over_one(self) -> None:
        """hard_fail > 1.0 should raise ValidationError."""
        with pytest.raises(ValidationError, match="less than or equal to 1"):
            ThresholdsConfig(soft_fail=0.05, hard_fail=1.5)

    def test_boundary_values_valid(self) -> None:
        """Boundary values 0.0 and 1.0 should be valid when ordered correctly."""
        config = ThresholdsConfig(soft_fail=0.0, hard_fail=1.0)
        assert config.soft_fail == pytest.approx(0.0)
        assert config.hard_fail == pytest.approx(1.0)

    def test_very_small_difference_valid(self) -> None:
        """Very small difference between thresholds should be valid."""
        config = ThresholdsConfig(soft_fail=0.05, hard_fail=0.06)
        assert config.soft_fail == pytest.approx(0.05)
        assert config.hard_fail == pytest.approx(0.06)


class TestDQConfigFile:
    """Tests for DQConfigFile schema."""

    def test_minimal_config(self) -> None:
        """Minimal config with only defaults should be valid."""
        config = DQConfigFile()
        assert config.version == "1.0.0"
        assert config.thresholds.soft_fail == pytest.approx(0.05)
        assert config.thresholds.hard_fail == pytest.approx(0.20)
        assert config.strict_validation is False
        assert config.invalid_record_policy == "quarantine"

    def test_full_config_with_metadata(self) -> None:
        """Full config with provider and entity metadata."""
        config = DQConfigFile(
            version="1.1.0",
            provider="chembl",
            entity="activity",
        )
        assert config.provider == "chembl"
        assert config.entity == "activity"
        assert config.version == "1.1.0"

    def test_config_with_thresholds(self) -> None:
        """Config with custom thresholds."""
        config = DQConfigFile(
            thresholds=ThresholdsConfig(soft_fail=0.03, hard_fail=0.15),
        )
        assert config.thresholds.soft_fail == pytest.approx(0.03)
        assert config.thresholds.hard_fail == pytest.approx(0.15)

    def test_config_with_field_validations(self) -> None:
        """Config with field validations at different levels."""
        config = DQConfigFile(
            common_field_validations=[
                FieldValidationConfig(
                    field="common_field", type="required", nullable=False
                )
            ],
            provider_field_validations=[
                FieldValidationConfig(
                    field="provider_field", type="pattern", pattern="^TEST"
                )
            ],
            entity_field_validations=[
                FieldValidationConfig(
                    field="entity_field", type="range", min=0, max=100
                )
            ],
        )
        assert len(config.common_field_validations) == 1
        assert len(config.provider_field_validations) == 1
        assert len(config.entity_field_validations) == 1

    def test_config_with_cross_field_validations(self) -> None:
        """Config with cross-field validations."""
        config = DQConfigFile(
            common_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="common_rule",
                    fields=["field_a", "field_b"],
                    condition="all_present",
                )
            ],
            entity_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="entity_rule",
                    fields=["field_x", "field_y"],
                    condition="conditional_required",
                    trigger_field="field_x",
                    required_field="field_y",
                )
            ],
        )
        assert len(config.common_cross_field_validations) == 1
        assert len(config.entity_cross_field_validations) == 1
        assert (
            config.entity_cross_field_validations[0].condition == "conditional_required"
        )

    def test_config_accepts_cross_field_equality_condition(self) -> None:
        """Equality is a supported cross-field condition for alias parity rules."""
        config = DQConfigFile(
            entity_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="doi_alias_equality",
                    fields=["doi", "publication_doi"],
                    condition="equality",
                )
            ]
        )

        assert config.entity_cross_field_validations[0].condition == "equality"

    def test_config_with_conditional_validations(self) -> None:
        """Config with conditional validations."""
        config = DQConfigFile(
            entity_conditional_validations=[
                ConditionalValidationConfig(
                    name="type_a_rule",
                    condition_field="type",
                    condition_value="A",
                    condition_operator="eq",
                    then_validations=[
                        FieldValidationConfig(
                            field="code", type="required", nullable=False
                        )
                    ],
                )
            ],
        )
        assert len(config.entity_conditional_validations) == 1
        assert config.entity_conditional_validations[0].condition_value == "A"
        assert len(config.entity_conditional_validations[0].then_validations) == 1

    def test_config_with_report_settings(self) -> None:
        """Config with custom report settings."""
        config = DQConfigFile(
            report=DQReportYamlConfig(
                enabled=True,
                format="yaml",
                include_sample_failures=False,
                sample_size=20,
                output_path="/custom/path",
            )
        )
        assert config.report.format == "yaml"
        assert config.report.sample_size == 20
        assert config.report.output_path == "/custom/path"

    def test_invalid_policy_rejected(self) -> None:
        """Invalid record policy should raise ValidationError."""
        with pytest.raises(ValidationError, match="Input should be"):
            DQConfigFile(invalid_record_policy="invalid")  # type: ignore[arg-type]

    def test_valid_policies(self) -> None:
        """All valid policies should be accepted."""
        valid_policies = ["quarantine", "skip", "fail"]
        for policy in valid_policies:
            config = DQConfigFile(invalid_record_policy=policy)  # type: ignore[arg-type]
            assert config.invalid_record_policy == policy

    def test_field_validation_types(self) -> None:
        """All validation types should be accepted."""
        valid_types = ["required", "range", "pattern", "enum", "custom"]
        for vtype in valid_types:
            config = DQConfigFile(
                entity_field_validations=[
                    FieldValidationConfig(field="test", type=vtype)  # type: ignore[arg-type]
                ]
            )
            assert config.entity_field_validations[0].type == vtype


class TestDQConfigFileToDomain:
    """Tests for DQConfigFile.to_domain() conversion."""

    def test_to_domain_minimal(self) -> None:
        """Minimal config converts to domain correctly."""
        config = DQConfigFile()
        domain = config.to_domain()

        assert domain.soft_fail_threshold == pytest.approx(0.05)
        assert domain.hard_fail_threshold == pytest.approx(0.20)
        assert domain.strict_validation is False
        assert domain.invalid_record_policy == "quarantine"
        assert len(domain.field_validations) == 0

    def test_to_domain_thresholds(self) -> None:
        """Thresholds are correctly converted."""
        config = DQConfigFile(
            thresholds=ThresholdsConfig(soft_fail=0.03, hard_fail=0.15),
        )
        domain = config.to_domain()

        assert domain.soft_fail_threshold == pytest.approx(0.03)
        assert domain.hard_fail_threshold == pytest.approx(0.15)

    def test_to_domain_merges_field_validations(self) -> None:
        """Field validations from all levels are merged."""
        config = DQConfigFile(
            common_field_validations=[
                FieldValidationConfig(field="common", type="required", nullable=False)
            ],
            provider_field_validations=[
                FieldValidationConfig(field="provider", type="pattern", pattern="^P")
            ],
            entity_field_validations=[
                FieldValidationConfig(field="entity", type="range", min=0, max=100)
            ],
        )
        domain = config.to_domain()

        assert len(domain.field_validations) == 3
        field_names = [fv.field for fv in domain.field_validations]
        assert "common" in field_names
        assert "provider" in field_names
        assert "entity" in field_names

    def test_to_domain_merges_cross_field_validations(self) -> None:
        """Cross-field validations are merged (common + entity)."""
        config = DQConfigFile(
            common_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="common_rule",
                    fields=["a", "b"],
                    condition="all_present",
                )
            ],
            entity_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="entity_rule",
                    fields=["x", "y"],
                    condition="any_present",
                )
            ],
        )
        domain = config.to_domain()

        assert len(domain.cross_field_validations) == 2
        names = [cfv.name for cfv in domain.cross_field_validations]
        assert "common_rule" in names
        assert "entity_rule" in names

    def test_to_domain_cross_field_severity_preserved(self) -> None:
        """Cross-field validation severity is preserved through to_domain()."""
        config = DQConfigFile(
            entity_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="publication_identifiable",
                    fields=["publication_id", "title"],
                    condition="all_present",
                    severity="error",
                ),
                CrossFieldValidationConfig(
                    name="has_cross_reference",
                    fields=["publication_pmid", "publication_doi"],
                    condition="any_present",
                    severity="warn",
                ),
            ],
        )
        domain = config.to_domain()

        assert len(domain.cross_field_validations) == 2

        identifiable = next(
            cfv
            for cfv in domain.cross_field_validations
            if cfv.name == "publication_identifiable"
        )
        assert identifiable.severity == "error"
        assert identifiable.condition == "all_present"
        assert identifiable.fields == ("publication_id", "title")

        cross_ref = next(
            cfv
            for cfv in domain.cross_field_validations
            if cfv.name == "has_cross_reference"
        )
        assert cross_ref.severity == "warn"
        assert cross_ref.condition == "any_present"
        assert cross_ref.fields == ("publication_pmid", "publication_doi")

    def test_to_domain_cross_field_severity_defaults_error(self) -> None:
        """Cross-field validation severity defaults to 'error' in domain."""
        config = DQConfigFile(
            entity_cross_field_validations=[
                CrossFieldValidationConfig(
                    name="rule_no_severity",
                    fields=["a", "b"],
                    condition="all_present",
                ),
            ],
        )
        domain = config.to_domain()

        assert domain.cross_field_validations[0].severity == "error"

    def test_to_domain_conditional_validations(self) -> None:
        """Conditional validations are converted with nested validations."""
        config = DQConfigFile(
            entity_conditional_validations=[
                ConditionalValidationConfig(
                    name="cond_rule",
                    condition_field="type",
                    condition_value=["A", "B"],
                    condition_operator="in",
                    then_validations=[
                        FieldValidationConfig(
                            field="code", type="required", nullable=False
                        )
                    ],
                )
            ],
        )
        domain = config.to_domain()

        assert len(domain.conditional_validations) == 1
        cv = domain.conditional_validations[0]
        assert cv.name == "cond_rule"
        assert cv.condition_operator == "in"
        assert cv.condition_value == ("A", "B")
        assert len(cv.then_validations) == 1

    def test_to_domain_report_config(self) -> None:
        """Report config is converted correctly."""
        config = DQConfigFile(
            report=DQReportYamlConfig(
                enabled=False,
                format="csv",
                sample_size=25,
            )
        )
        domain = config.to_domain()

        assert domain.report.enabled is False
        assert domain.report.format == "csv"
        assert domain.report.sample_size == 25

    def test_to_domain_field_validation_details(self) -> None:
        """Field validation details are preserved in conversion."""
        config = DQConfigFile(
            entity_field_validations=[
                FieldValidationConfig(
                    field="test_field",
                    type="enum",
                    nullable=False,
                    allowed=["A", "B", "C"],
                    error_message="Invalid value",
                )
            ],
        )
        domain = config.to_domain()

        fv = domain.field_validations[0]
        assert fv.field == "test_field"
        assert fv.validation_type == "enum"
        assert fv.nullable is False
        assert fv.allowed == ("A", "B", "C")
        assert fv.error_message == "Invalid value"

    def test_to_domain_range_validation(self) -> None:
        """Range validation with min/max is preserved."""
        config = DQConfigFile(
            entity_field_validations=[
                FieldValidationConfig(
                    field="value",
                    type="range",
                    min=0.0,
                    max=100.0,
                )
            ],
        )
        domain = config.to_domain()

        fv = domain.field_validations[0]
        assert fv.min_value == pytest.approx(0.0)
        assert fv.max_value == pytest.approx(100.0)

    def test_to_domain_immutable(self) -> None:
        """Domain config should be immutable (frozen dataclass)."""
        config = DQConfigFile()
        domain = config.to_domain()

        with pytest.raises(AttributeError):
            domain.soft_fail_threshold = 0.99  # type: ignore[misc]


class TestFieldValidationConfig:
    """Tests for FieldValidationConfig schema."""

    def test_minimal_field_validation(self) -> None:
        """Minimal field validation with required fields only."""
        fv = FieldValidationConfig(field="test", type="required")
        assert fv.field == "test"
        assert fv.type == "required"
        assert fv.nullable is True  # Default

    def test_range_validation_params(self) -> None:
        """Range validation with min/max parameters."""
        fv = FieldValidationConfig(
            field="value",
            type="range",
            min=0,
            max=100,
        )
        assert fv.min == 0
        assert fv.max == 100

    def test_validation_config__pattern_validation__66b796f8(self) -> None:
        """Pattern validation with regex."""
        fv = FieldValidationConfig(
            field="id",
            type="pattern",
            pattern=r"^[A-Z]\d+$",
        )
        assert fv.pattern == r"^[A-Z]\d+$"

    def test_validation_config__enum_validation__e8edaea3(self) -> None:
        """Enum validation with allowed values."""
        fv = FieldValidationConfig(
            field="status",
            type="enum",
            allowed=["active", "inactive", "pending"],
        )
        assert fv.allowed == ["active", "inactive", "pending"]

    def test_custom_validation(self) -> None:
        """Custom validation with validator reference."""
        fv = FieldValidationConfig(
            field="complex_field",
            type="custom",
            validator="validate_complex_field",
        )
        assert fv.validator == "validate_complex_field"


class TestCrossFieldValidationConfig:
    """Tests for CrossFieldValidationConfig schema."""

    def test_all_present_condition__test_cross_field_validation_config_infrastructure_schemas_test_dq_config_483(
        self,
    ) -> None:
        """All present condition validation."""
        cfv = CrossFieldValidationConfig(
            name="all_fields",
            fields=["a", "b", "c"],
            condition="all_present",
        )
        assert cfv.condition == "all_present"
        assert len(cfv.fields) == 3

    def test_conditional_required__test_cross_field_validation_config_infrastructure_schemas_test_dq_config_493(
        self,
    ) -> None:
        """Conditional required with trigger/required fields."""
        cfv = CrossFieldValidationConfig(
            name="cond_req",
            fields=["trigger", "required"],
            condition="conditional_required",
            trigger_field="trigger",
            required_field="required",
        )
        assert cfv.trigger_field == "trigger"
        assert cfv.required_field == "required"

    def test_mutually_exclusive(self) -> None:
        """Mutually exclusive condition."""
        cfv = CrossFieldValidationConfig(
            name="mutex",
            fields=["option_a", "option_b"],
            condition="mutually_exclusive",
        )
        assert cfv.condition == "mutually_exclusive"

    def test_severity_defaults_to_error(self) -> None:
        """Severity should default to 'error' when not specified."""
        cfv = CrossFieldValidationConfig(
            name="strict_rule",
            fields=["pk", "title"],
            condition="all_present",
        )
        assert cfv.severity == "error"

    def test_severity_warn(self) -> None:
        """Severity 'warn' should be accepted."""
        cfv = CrossFieldValidationConfig(
            name="soft_rule",
            fields=["pmid", "doi"],
            condition="any_present",
            severity="warn",
        )
        assert cfv.severity == "warn"

    def test_severity_invalid_rejected(self) -> None:
        """Invalid severity value should raise ValidationError."""
        with pytest.raises(ValidationError, match="Input should be"):
            CrossFieldValidationConfig(
                name="bad_rule",
                fields=["a", "b"],
                condition="all_present",
                severity="critical",  # type: ignore[arg-type]
            )
