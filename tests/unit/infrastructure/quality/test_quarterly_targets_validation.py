# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for _quarterly_targets_validation module."""

from __future__ import annotations

import pytest

from bioetl.infrastructure.quality._quarterly_targets_validation import (
    _validate_quarter_target,
    _validate_quarterly_targets_section,
)


pytestmark = pytest.mark.unit


class TestValidateQuarterTarget:
    """Tests for _validate_quarter_target."""

    def test_valid_target(self) -> None:
        """Valid target should return parsed tuple."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target={
                "quarter": "2025-Q1",
                "max_total_exemptions": 20,
                "min_integral_score": 50.0,
                "group_budgets": {"grp1": 10},
                "registry_budgets": {"reg_a": 20},
            },
            group_names={"grp1"},
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert result is not None
        assert result[0] == (2025, 1)
        assert errors == []

    def test_quarter_target__not_dict__63dae542(self) -> None:
        """Non-dict target should add error and return None."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target="invalid",
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert result is None
        assert any("expected mapping" in e for e in errors)

    def test_invalid_quarter_format(self) -> None:
        """Invalid quarter format should add error and return None."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target={
                "quarter": "bad-format",
                "max_total_exemptions": 10,
                "min_integral_score": 50.0,
                "group_budgets": {},
                "registry_budgets": {},
            },
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert result is None
        assert any("YYYY-QN" in e for e in errors)

    def test_negative_max_total_exemptions(self) -> None:
        """Negative max_total_exemptions should add error."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target={
                "quarter": "2025-Q1",
                "max_total_exemptions": -5,
                "min_integral_score": 50.0,
                "group_budgets": {},
                "registry_budgets": {},
            },
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert result is None
        assert any("non-negative" in e for e in errors)

    def test_quarter_target__min_score_not_number__542fd816(self) -> None:
        """Non-number min_integral_score should add error and return None."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target={
                "quarter": "2025-Q1",
                "max_total_exemptions": 10,
                "min_integral_score": "high",
                "group_budgets": {},
                "registry_budgets": {},
            },
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert result is None
        assert any("min_integral_score" in e for e in errors)

    def test_min_score_out_of_range(self) -> None:
        """min_integral_score outside [0, 100] should add error (result is still returned)."""
        errors: list[str] = []
        # When score is a valid float but out of range, an error is added.
        # The function only returns None when score is not (int, float), so result is not None here.
        _validate_quarter_target(
            index=0,
            target={
                "quarter": "2025-Q1",
                "max_total_exemptions": 10,
                "min_integral_score": 150.0,
                "group_budgets": {},
                "registry_budgets": {},
            },
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any("between 0 and 100" in e for e in errors)

    def test_group_budgets_validated(self) -> None:
        """group_budgets missing keys should add error."""
        errors: list[str] = []
        _validate_quarter_target(
            index=0,
            target={
                "quarter": "2025-Q1",
                "max_total_exemptions": 10,
                "min_integral_score": 50.0,
                "group_budgets": {},  # missing expected keys
                "registry_budgets": {},
            },
            group_names={"grp1"},  # expects grp1 key
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any("missing" in e for e in errors)

    def test_missing_quarter_key(self) -> None:
        """Missing quarter key should add error and return None."""
        errors: list[str] = []
        result = _validate_quarter_target(
            index=0,
            target={
                "max_total_exemptions": 10,
                "min_integral_score": 50.0,
            },
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert result is None


class TestValidateQuarterlyTargetsSection:
    """Tests for _validate_quarterly_targets_section."""

    def test_valid_strictly_decreasing(self) -> None:
        """Strictly decreasing max_total and increasing min_score should pass."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "max_total_exemptions": 20,
                    "min_integral_score": 50.0,
                    "group_budgets": {"grp1": 20},
                    "registry_budgets": {"reg_a": 20},
                },
                {
                    "quarter": "2025-Q2",
                    "max_total_exemptions": 15,
                    "min_integral_score": 60.0,
                    "group_budgets": {"grp1": 15},
                    "registry_budgets": {"reg_a": 15},
                },
            ]
        }
        errors: list[str] = []
        _validate_quarterly_targets_section(
            raw,
            group_names={"grp1"},
            baseline_registry_names={"reg_a"},
            errors=errors,
        )
        assert errors == []

    def test_targets_section__quarterly_targets__f7acef7b(self) -> None:
        """Missing quarterly_targets should add error."""
        errors: list[str] = []
        _validate_quarterly_targets_section(
            {},
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any("quarterly_targets" in e for e in errors)

    def test_targets_section__not_a_list__c40ae2c5(self) -> None:
        """Non-list quarterly_targets should add error."""
        errors: list[str] = []
        _validate_quarterly_targets_section(
            {"quarterly_targets": "invalid"},
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any("quarterly_targets" in e for e in errors)

    def test_non_decreasing_max_total_violation(self) -> None:
        """Non-decreasing max_total_exemptions should add error."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "max_total_exemptions": 10,
                    "min_integral_score": 50.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                },
                {
                    "quarter": "2025-Q2",
                    "max_total_exemptions": 15,  # increases (violation)
                    "min_integral_score": 60.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                },
            ]
        }
        errors: list[str] = []
        _validate_quarterly_targets_section(
            raw,
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any(
            "max_total_exemptions" in e and "strictly decrease" in e for e in errors
        )

    def test_non_increasing_min_score_violation(self) -> None:
        """Non-increasing min_integral_score should add error."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "max_total_exemptions": 20,
                    "min_integral_score": 60.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                },
                {
                    "quarter": "2025-Q2",
                    "max_total_exemptions": 15,
                    "min_integral_score": 50.0,  # decreases (violation)
                    "group_budgets": {},
                    "registry_budgets": {},
                },
            ]
        }
        errors: list[str] = []
        _validate_quarterly_targets_section(
            raw,
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any(
            "min_integral_score" in e and "strictly increase" in e for e in errors
        )

    def test_duplicate_quarters(self) -> None:
        """Duplicate quarter entries should add error."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "max_total_exemptions": 20,
                    "min_integral_score": 50.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                },
                {
                    "quarter": "2025-Q1",  # duplicate
                    "max_total_exemptions": 15,
                    "min_integral_score": 60.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                },
            ]
        }
        errors: list[str] = []
        _validate_quarterly_targets_section(
            raw,
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert any("duplicate" in e for e in errors)

    def test_single_target_no_comparison(self) -> None:
        """Single target has nothing to compare against, should pass."""
        raw = {
            "quarterly_targets": [
                {
                    "quarter": "2025-Q1",
                    "max_total_exemptions": 10,
                    "min_integral_score": 50.0,
                    "group_budgets": {},
                    "registry_budgets": {},
                }
            ]
        }
        errors: list[str] = []
        _validate_quarterly_targets_section(
            raw,
            group_names=set(),
            baseline_registry_names=set(),
            errors=errors,
        )
        assert errors == []
