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
"""Tests for Data Quality configuration objects.

Tests for DQConfig, DQReportConfig, KeyNullabilityRule.
"""

from __future__ import annotations

import pytest

from bioetl.domain.config.dq import DQConfig, DQReportConfig, KeyNullabilityRule
from bioetl.domain.config.validation import FieldValidation


@pytest.mark.unit
class TestDQReportConfig:
    """Tests for DQReportConfig frozen dataclass."""

    def test_dq_report_config_default_values(self) -> None:
        config = DQReportConfig()
        assert config.enabled is True
        assert config.format == "json"
        assert config.include_sample_failures is True
        assert config.sample_size == 10
        assert config.output_path is None

    def test_dq_report_config_custom_values(self) -> None:
        config = DQReportConfig(
            enabled=False,
            format="csv",
            sample_size=50,
            output_path="reports",
        )
        assert config.enabled is False
        assert config.format == "csv"
        assert config.sample_size == 50


@pytest.mark.unit
class TestKeyNullabilityRule:
    """Tests for KeyNullabilityRule frozen dataclass."""

    def test_merge_key(self) -> None:
        rule = KeyNullabilityRule(field="entity_id", key_type="merge")
        assert rule.field == "entity_id"
        assert rule.key_type == "merge"
        assert rule.nullable is False

    def test_partition_key_nullable(self) -> None:
        rule = KeyNullabilityRule(
            field="partition_col", key_type="partition", nullable=True
        )
        assert rule.nullable is True


@pytest.mark.unit
class TestDQConfig:
    """Tests for DQConfig frozen dataclass."""

    def test_dq_config_default_values(self) -> None:
        config = DQConfig()
        assert config.soft_fail_threshold == pytest.approx(0.05)
        assert config.hard_fail_threshold == pytest.approx(0.50)
        assert config.strict_validation is False
        assert config.field_validations == ()
        assert config.cross_field_validations == ()
        assert config.conditional_validations == ()
        assert config.invalid_record_policy == "quarantine"
        assert isinstance(config.report, DQReportConfig)

    def test_custom_thresholds(self) -> None:
        config = DQConfig(soft_fail_threshold=0.01, hard_fail_threshold=0.10)
        assert config.soft_fail_threshold == pytest.approx(0.01)
        assert config.hard_fail_threshold == pytest.approx(0.10)

    def test_soft_exceeds_hard_raises(self) -> None:
        with pytest.raises(
            ValueError, match="soft_fail_threshold must be strictly less"
        ):
            DQConfig(soft_fail_threshold=0.30, hard_fail_threshold=0.20)

    def test_equal_thresholds_raises(self) -> None:
        with pytest.raises(
            ValueError, match="soft_fail_threshold must be strictly less"
        ):
            DQConfig(soft_fail_threshold=0.20, hard_fail_threshold=0.20)

    def test_soft_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="soft_fail_threshold must be between"):
            DQConfig(soft_fail_threshold=-0.1, hard_fail_threshold=0.20)

    def test_hard_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="hard_fail_threshold must be between"):
            DQConfig(soft_fail_threshold=0.05, hard_fail_threshold=1.5)

    def test_with_field_validations(self) -> None:
        fv = FieldValidation(field="entity_id", validation_type="required")
        config = DQConfig(field_validations=(fv,))
        assert len(config.field_validations) == 1

    def test_config_dq_d_q_config__to_tuple_conversion__397cadb5(self) -> None:
        fv = FieldValidation(field="entity_id", validation_type="required")
        config = DQConfig(field_validations=[fv])  # type: ignore[arg-type]
        assert isinstance(config.field_validations, tuple)

    def test_validate_thresholds_static(self) -> None:
        # Should not raise
        DQConfig.validate_thresholds(soft_fail_threshold=0.01, hard_fail_threshold=0.10)

    def test_validate_thresholds_static_raises(self) -> None:
        with pytest.raises(ValueError):
            DQConfig.validate_thresholds(
                soft_fail_threshold=0.50, hard_fail_threshold=0.10
            )
