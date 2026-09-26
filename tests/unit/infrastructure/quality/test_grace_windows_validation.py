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
"""Unit tests for _grace_windows_validation module."""

from __future__ import annotations

from datetime import date

import pytest

from bioetl.infrastructure.quality._grace_windows_validation import (
    _validate_allowances,
    _validate_grace_window_dates,
    _validate_grace_window_identity_fields,
    _validate_grace_window_metadata,
    _validate_grace_windows_section,
)

pytestmark = pytest.mark.unit


class TestValidateAllowances:
    """Tests for _validate_allowances."""

    def test_valid_allowances(self) -> None:
        """Valid allowances should produce no errors."""
        errors: list[str] = []
        _validate_allowances(
            allowances={
                "total_exemptions": 5,
                "registry_budgets": {"reg_a": 3},
                "group_budgets": {"grp1": 2},
            },
            prefix="gw[0]",
            baseline_registry_names={"reg_a"},
            group_names={"grp1"},
            errors=errors,
        )
        assert errors == []

    def test_validate_allowances__not_dict__8f8661e5(self) -> None:
        """Non-dict allowances should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances="invalid",
            prefix="gw[0]",
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("allowances" in e for e in errors)

    def test_registry_budgets_not_dict(self) -> None:
        """Non-dict registry_budgets should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances={"total_exemptions": 5, "registry_budgets": "invalid"},
            prefix="gw[0]",
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("registry_budgets" in e for e in errors)

    def test_unknown_registry_in_budgets(self) -> None:
        """Unknown registry in registry_budgets should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances={"registry_budgets": {"unknown_reg": 5}},
            prefix="gw[0]",
            baseline_registry_names={"reg_a"},
            group_names=set(),
            errors=errors,
        )
        assert any("unknown registry" in e for e in errors)

    def test_group_budgets_not_dict(self) -> None:
        """Non-dict group_budgets should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances={"group_budgets": "invalid"},
            prefix="gw[0]",
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("group_budgets" in e for e in errors)

    def test_unknown_group_in_budgets(self) -> None:
        """Unknown group in group_budgets should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances={"group_budgets": {"unknown_grp": 5}},
            prefix="gw[0]",
            baseline_registry_names=set(),
            group_names={"grp1"},
            errors=errors,
        )
        assert any("unknown group" in e for e in errors)

    def test_negative_total_exemptions(self) -> None:
        """Negative total_exemptions should add error."""
        errors: list[str] = []
        _validate_allowances(
            allowances={"total_exemptions": -1},
            prefix="gw[0]",
            baseline_registry_names=set(),
            group_names=set(),
            errors=errors,
        )
        assert any("non-negative" in e for e in errors)


class TestValidateGraceWindowIdentityFields:
    """Tests for _validate_grace_window_identity_fields."""

    def test_valid_approved_with_rf_ref(self) -> None:
        """Approved window with RF-* ref should produce no errors."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="RF-001",
            approved=True,
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert errors == []

    def test_missing_rf_id(self) -> None:
        """Missing rf_id should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id=None,
            approved=True,
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("rf_id" in e for e in errors)

    def test_empty_rf_id(self) -> None:
        """Empty rf_id should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="   ",
            approved=True,
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("rf_id" in e for e in errors)

    def test_approved_not_bool(self) -> None:
        """Non-bool approved should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="RF-001",
            approved="yes",
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("approved" in e for e in errors)

    def test_allow_rf_only_false_approved(self) -> None:
        """approved=False when allow_rf_only=True should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="RF-001",
            approved=False,
            allow_rf_only_for_rf=True,
            errors=errors,
        )
        assert any("approved" in e for e in errors)

    def test_approved_without_rf_ref(self) -> None:
        """Approved window with non-RF rf_id should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="TASK-001",  # not RF-*
            approved=True,
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("RF-*" in e for e in errors)

    def test_allow_rf_only_non_rf_ref(self) -> None:
        """allow_rf_only=True with non-RF rf_id should add error."""
        errors: list[str] = []
        _validate_grace_window_identity_fields(
            prefix="gw[0]",
            rf_id="TASK-001",
            approved=True,
            allow_rf_only_for_rf=True,
            errors=errors,
        )
        # Both "RF-*" errors may appear
        assert any("RF-*" in e for e in errors)


class TestValidateGraceWindowDates:
    """Tests for _validate_grace_window_dates."""

    def test_valid_dates(self) -> None:
        """Valid non-overlapping dates should produce no errors."""
        errors: list[str] = []
        _validate_grace_window_dates(
            prefix="gw[0]",
            starts_on=date(2025, 1, 1),
            ends_on=date(2025, 12, 31),
            errors=errors,
        )
        assert errors == []

    def test_missing_starts_on(self) -> None:
        """Missing starts_on should add error."""
        errors: list[str] = []
        _validate_grace_window_dates(
            prefix="gw[0]",
            starts_on=None,
            ends_on=date(2025, 12, 31),
            errors=errors,
        )
        assert any("starts_on" in e for e in errors)

    def test_missing_ends_on(self) -> None:
        """Missing ends_on should add error."""
        errors: list[str] = []
        _validate_grace_window_dates(
            prefix="gw[0]",
            starts_on=date(2025, 1, 1),
            ends_on=None,
            errors=errors,
        )
        assert any("ends_on" in e for e in errors)

    def test_ends_before_starts(self) -> None:
        """ends_on before starts_on should add error."""
        errors: list[str] = []
        _validate_grace_window_dates(
            prefix="gw[0]",
            starts_on=date(2025, 6, 1),
            ends_on=date(2025, 1, 1),
            errors=errors,
        )
        assert any("ends_on must be >=" in e for e in errors)

    def test_same_day_is_valid(self) -> None:
        """Same start and end date should be valid."""
        errors: list[str] = []
        _validate_grace_window_dates(
            prefix="gw[0]",
            starts_on=date(2025, 6, 1),
            ends_on=date(2025, 6, 1),
            errors=errors,
        )
        assert errors == []


class TestValidateGraceWindowMetadata:
    """Tests for _validate_grace_window_metadata."""

    def test_valid_metadata(self) -> None:
        """Valid metadata should produce no errors."""
        errors: list[str] = []
        _validate_grace_window_metadata(
            prefix="gw[0]",
            window={
                "rf_id": "RF-001",
                "approved": True,
                "starts_on": "2025-01-01",
                "ends_on": "2025-12-31",
            },
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert errors == []

    def test_invalid_dates(self) -> None:
        """Invalid date strings should add errors."""
        errors: list[str] = []
        _validate_grace_window_metadata(
            prefix="gw[0]",
            window={
                "rf_id": "RF-001",
                "approved": True,
                "starts_on": "not-a-date",
                "ends_on": "also-bad",
            },
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("starts_on" in e for e in errors)
        assert any("ends_on" in e for e in errors)


class TestValidateGraceWindowsSection:
    """Tests for _validate_grace_windows_section."""

    def test_empty_list_no_errors(self) -> None:
        """Empty grace_windows list should produce no errors."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {},
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert errors == []

    def test_none_treated_as_empty(self) -> None:
        """grace_windows=None should be treated as empty list."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {"grace_windows": None},
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert errors == []

    def test_not_list(self) -> None:
        """Non-list grace_windows should add error."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {"grace_windows": "invalid"},
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("expected list" in e for e in errors)

    def test_non_dict_item_skipped(self) -> None:
        """Non-dict window item should add error and be skipped."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {"grace_windows": ["not_a_dict"]},
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("expected mapping" in e for e in errors)

    def test_valid_window(self) -> None:
        """Valid window should produce no errors."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {
                "grace_windows": [
                    {
                        "rf_id": "RF-001",
                        "approved": True,
                        "starts_on": "2025-01-01",
                        "ends_on": "2025-12-31",
                        "allowances": {"total_exemptions": 5},
                    }
                ]
            },
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert errors == []

    def test_multiple_windows_validated(self) -> None:
        """Multiple windows should each be validated."""
        errors: list[str] = []
        _validate_grace_windows_section(
            {
                "grace_windows": [
                    {
                        "rf_id": "RF-001",
                        "approved": True,
                        "starts_on": "2025-01-01",
                        "ends_on": "2025-12-31",
                    },
                    {
                        "rf_id": None,  # invalid
                        "approved": True,
                        "starts_on": "2025-01-01",
                        "ends_on": "2025-12-31",
                    },
                ]
            },
            baseline_registry_names=set(),
            group_names=set(),
            allow_rf_only_for_rf=False,
            errors=errors,
        )
        assert any("rf_id" in e for e in errors)
