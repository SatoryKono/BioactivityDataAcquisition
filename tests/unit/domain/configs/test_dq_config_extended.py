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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Extended tests for DQ config classes — DQReportConfig, KeyNullabilityRule, DQConfig with nested objects."""

from __future__ import annotations

import pytest

from bioetl.domain.config.dq import DQConfig, DQReportConfig, KeyNullabilityRule
from bioetl.domain.config.validation import (
    ConditionalValidation,
    CrossFieldValidation,
    FieldValidation,
)


@pytest.mark.unit
class TestDQReportConfig:
    """Tests for DQReportConfig dataclass."""

    def test_d_q_report_config__default_values__dd3ea153(self) -> None:
        rc = DQReportConfig()
        assert rc.enabled is True
        assert rc.format == "json"
        assert rc.include_sample_failures is True
        assert rc.sample_size == 10
        assert rc.output_path is None

    def test_d_q_report_config__custom_values__7563d6e8(self) -> None:
        rc = DQReportConfig(
            enabled=False,
            format="yaml",
            include_sample_failures=False,
            sample_size=50,
            output_path="reports",
        )
        assert rc.format == "yaml"
        assert rc.sample_size == 50

    @pytest.mark.parametrize("fmt", ["json", "yaml", "csv"])
    def test_valid_formats(self, fmt: str) -> None:
        rc = DQReportConfig(format=fmt)  # type: ignore[arg-type]
        assert rc.format == fmt

    def test_d_q_report_config__immutable__d9c2b855(self) -> None:
        rc = DQReportConfig()
        with pytest.raises((AttributeError, TypeError)):
            rc.enabled = False  # type: ignore[misc]


@pytest.mark.unit
class TestKeyNullabilityRule:
    """Tests for KeyNullabilityRule dataclass."""

    def test_creation_merge(self) -> None:
        rule = KeyNullabilityRule(field="entity_id", key_type="merge")
        assert rule.field == "entity_id"
        assert rule.key_type == "merge"
        assert rule.nullable is False

    def test_creation_partition_nullable(self) -> None:
        rule = KeyNullabilityRule(field="provider", key_type="partition", nullable=True)
        assert rule.key_type == "partition"
        assert rule.nullable is True

    def test_key_nullability_rule__immutable__57eba322(self) -> None:
        rule = KeyNullabilityRule(field="x", key_type="merge")
        with pytest.raises((AttributeError, TypeError)):
            rule.nullable = True  # type: ignore[misc]


@pytest.mark.unit
class TestDQConfigExtended:
    """Extended tests for DQConfig with nested validation objects."""

    def test_d_q_config_extended__default_values__b30b68aa(self) -> None:
        dq = DQConfig()
        assert dq.soft_fail_threshold == pytest.approx(0.05)
        assert dq.hard_fail_threshold == pytest.approx(0.50)
        assert dq.strict_validation is False
        assert dq.invalid_record_policy == "quarantine"
        assert dq.field_validations == ()
        assert dq.cross_field_validations == ()
        assert dq.conditional_validations == ()
        assert dq.key_nullability_rules == ()
        assert isinstance(dq.report, DQReportConfig)

    def test_d_q_config_extended__field_validations__6563f525(self) -> None:
        fv = FieldValidation(field="name", validation_type="required")
        dq = DQConfig(field_validations=(fv,))
        assert len(dq.field_validations) == 1
        assert dq.field_validations[0].field == "name"

    def test_field_validations_list_frozen(self) -> None:
        fv = FieldValidation(field="x", validation_type="required")
        dq = DQConfig(field_validations=[fv])  # type: ignore[arg-type]
        assert isinstance(dq.field_validations, tuple)

    def test_with_cross_field_validations(self) -> None:
        cfv = CrossFieldValidation(
            name="test",
            fields=("a", "b"),
            condition="all_present",
        )
        dq = DQConfig(cross_field_validations=(cfv,))
        assert len(dq.cross_field_validations) == 1

    def test_with_conditional_validations(self) -> None:
        cv = ConditionalValidation(
            name="type_b",
            condition_field="assay_type",
            condition_value="B",
        )
        dq = DQConfig(conditional_validations=(cv,))
        assert len(dq.conditional_validations) == 1

    def test_with_key_nullability_rules(self) -> None:
        rule = KeyNullabilityRule(field="entity_id", key_type="merge")
        dq = DQConfig(key_nullability_rules=(rule,))
        assert len(dq.key_nullability_rules) == 1

    def test_threshold_boundary_values(self) -> None:
        dq = DQConfig(soft_fail_threshold=0.0, hard_fail_threshold=1.0)
        assert dq.soft_fail_threshold == pytest.approx(0.0)
        assert dq.hard_fail_threshold == pytest.approx(1.0)

    def test_threshold_ordering_violation_raises(self) -> None:
        with pytest.raises(
            ValueError, match="soft_fail_threshold must be strictly less"
        ):
            DQConfig(soft_fail_threshold=0.5, hard_fail_threshold=0.5)

    def test_soft_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="soft_fail_threshold must be between"):
            DQConfig(soft_fail_threshold=-0.1, hard_fail_threshold=0.5)

    def test_hard_threshold_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="hard_fail_threshold must be between"):
            DQConfig(soft_fail_threshold=0.1, hard_fail_threshold=1.5)

    @pytest.mark.parametrize("policy", ["quarantine", "skip", "fail"])
    def test_valid_invalid_record_policies(self, policy: str) -> None:
        dq = DQConfig(invalid_record_policy=policy)  # type: ignore[arg-type]
        assert dq.invalid_record_policy == policy

    def test_with_custom_report(self) -> None:
        report = DQReportConfig(format="yaml", sample_size=20)
        dq = DQConfig(report=report)
        assert dq.report.format == "yaml"
        assert dq.report.sample_size == 20

    def test_d_q_config_extended__immutable__9213e566(self) -> None:
        dq = DQConfig()
        with pytest.raises((AttributeError, TypeError)):
            dq.strict_validation = True  # type: ignore[misc]
