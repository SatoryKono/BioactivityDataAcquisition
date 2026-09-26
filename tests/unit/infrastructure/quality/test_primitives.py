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
"""Unit tests for debt scorecard primitives."""

from __future__ import annotations

from datetime import date

import pytest

from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _parse_quarter_label,
    _quarter_label,
    _validate_budget_mapping,
    _validate_gate_mode,
    _validate_non_negative_int,
)

pytestmark = pytest.mark.unit


class TestParseIsoDate:
    """Tests for _parse_iso_date."""

    def test_parse_iso_date__valid_date__f1e5c1bf(self) -> None:
        """Should parse valid ISO date."""
        result = _parse_iso_date("2025-06-15")
        assert result == date(2025, 6, 15)

    def test_invalid_string(self) -> None:
        """Should return None for invalid date string."""
        assert _parse_iso_date("not-a-date") is None

    def test_parse_iso_date__non_string_input__f2ac9d9f(self) -> None:
        """Should return None for non-string input."""
        assert _parse_iso_date(12345) is None
        assert _parse_iso_date(None) is None

    def test_parse_iso_date__empty_string__b14cf534(self) -> None:
        """Should return None for empty string."""
        assert _parse_iso_date("") is None


class TestParseQuarterLabel:
    """Tests for _parse_quarter_label."""

    def test_parse_quarter_label__valid_quarter__bf31fe6c(self) -> None:
        """Should parse valid quarter labels."""
        assert _parse_quarter_label("2025-Q1") == (2025, 1)
        assert _parse_quarter_label("2025-Q4") == (2025, 4)
        assert _parse_quarter_label("2030-Q2") == (2030, 2)

    def test_with_whitespace(self) -> None:
        """Should strip whitespace."""
        assert _parse_quarter_label("  2025-Q1  ") == (2025, 1)

    def test_parse_quarter_label__invalid_format__98a525e5(self) -> None:
        """Should return None for invalid format."""
        assert _parse_quarter_label("Q1-2025") is None
        assert _parse_quarter_label("2025-Q5") is None
        assert _parse_quarter_label("2025-Q0") is None
        assert _parse_quarter_label("invalid") is None
        assert _parse_quarter_label("") is None

    def test_non_2000s_year(self) -> None:
        """Should only accept years starting with 20."""
        assert _parse_quarter_label("1999-Q1") is None
        assert _parse_quarter_label("3000-Q1") is None


class TestQuarterLabel:
    """Tests for _quarter_label."""

    def test_q1(self) -> None:
        """Jan-Mar should be Q1."""
        assert _quarter_label(date(2025, 1, 15)) == "2025-Q1"
        assert _quarter_label(date(2025, 3, 31)) == "2025-Q1"

    def test_q2(self) -> None:
        """Apr-Jun should be Q2."""
        assert _quarter_label(date(2025, 4, 1)) == "2025-Q2"
        assert _quarter_label(date(2025, 6, 30)) == "2025-Q2"

    def test_q3(self) -> None:
        """Jul-Sep should be Q3."""
        assert _quarter_label(date(2025, 7, 1)) == "2025-Q3"

    def test_q4(self) -> None:
        """Oct-Dec should be Q4."""
        assert _quarter_label(date(2025, 12, 31)) == "2025-Q4"


class TestValidateNonNegativeInt:
    """Tests for _validate_non_negative_int."""

    def test_non_negative_int__valid_int__b462d8d0(self) -> None:
        """Should return value for valid non-negative int."""
        errors: list[str] = []
        result = _validate_non_negative_int(5, field_name="count", errors=errors)
        assert result == 5
        assert errors == []

    def test_non_negative_int__zero_is_valid__9276072a(self) -> None:
        """Zero should be valid."""
        errors: list[str] = []
        result = _validate_non_negative_int(0, field_name="count", errors=errors)
        assert result == 0
        assert errors == []

    def test_negative_int(self) -> None:
        """Negative int should add error and return None."""
        errors: list[str] = []
        result = _validate_non_negative_int(-1, field_name="count", errors=errors)
        assert result is None
        assert len(errors) == 1
        assert "non-negative" in errors[0]

    def test_non_int_type(self) -> None:
        """Non-int type should add error and return None."""
        errors: list[str] = []
        result = _validate_non_negative_int("5", field_name="count", errors=errors)
        assert result is None
        assert len(errors) == 1
        assert "expected int" in errors[0]

    def test_non_negative_int__none_value__684b1c82(self) -> None:
        """None should add error and return None."""
        errors: list[str] = []
        result = _validate_non_negative_int(None, field_name="count", errors=errors)
        assert result is None
        assert len(errors) == 1


class TestValidateGateMode:
    """Tests for _validate_gate_mode."""

    def test_valid_warn(self) -> None:
        """Should accept 'warn' mode."""
        errors: list[str] = []
        result = _validate_gate_mode(value="warn", field_name="gate", errors=errors)
        assert result == "warn"
        assert errors == []

    def test_valid_block(self) -> None:
        """Should accept 'block' mode."""
        errors: list[str] = []
        result = _validate_gate_mode(value="block", field_name="gate", errors=errors)
        assert result == "block"
        assert errors == []

    def test_validate_gate_mode__case_insensitive__2dbc995d(self) -> None:
        """Should be case insensitive."""
        errors: list[str] = []
        result = _validate_gate_mode(value="WARN", field_name="gate", errors=errors)
        assert result == "warn"

    def test_validate_gate_mode__with_whitespace__9984d633(self) -> None:
        """Should strip whitespace."""
        errors: list[str] = []
        result = _validate_gate_mode(
            value="  block  ", field_name="gate", errors=errors
        )
        assert result == "block"

    def test_invalid_mode(self) -> None:
        """Should add error for invalid mode."""
        errors: list[str] = []
        result = _validate_gate_mode(value="invalid", field_name="gate", errors=errors)
        assert result is None
        assert len(errors) == 1

    def test_validate_gate_mode__non_string__b693d7a2(self) -> None:
        """Should add error for non-string value."""
        errors: list[str] = []
        result = _validate_gate_mode(value=123, field_name="gate", errors=errors)
        assert result is None
        assert len(errors) == 1


class TestValidateBudgetMapping:
    """Tests for _validate_budget_mapping."""

    def test_valid_mapping(self) -> None:
        """Should pass for valid mapping with expected keys."""
        errors: list[str] = []
        _validate_budget_mapping(
            {"a": 5, "b": 10},
            expected_keys={"a", "b"},
            field_name="budgets",
            errors=errors,
        )
        assert errors == []

    def test_budget_mapping__not_dict__59637188(self) -> None:
        """Should add error for non-dict input."""
        errors: list[str] = []
        _validate_budget_mapping(
            "invalid",
            expected_keys={"a"},
            field_name="budgets",
            errors=errors,
        )
        assert len(errors) == 1
        assert "expected mapping" in errors[0]

    def test_missing_keys(self) -> None:
        """Should add error for missing keys."""
        errors: list[str] = []
        _validate_budget_mapping(
            {"a": 5},
            expected_keys={"a", "b"},
            field_name="budgets",
            errors=errors,
        )
        assert any("missing" in e for e in errors)

    def test_extra_keys(self) -> None:
        """Should add error for extra keys."""
        errors: list[str] = []
        _validate_budget_mapping(
            {"a": 5, "b": 10, "c": 3},
            expected_keys={"a", "b"},
            field_name="budgets",
            errors=errors,
        )
        assert any("unknown" in e for e in errors)

    def test_invalid_values(self) -> None:
        """Should validate values as non-negative ints."""
        errors: list[str] = []
        _validate_budget_mapping(
            {"a": -1, "b": "invalid"},
            expected_keys={"a", "b"},
            field_name="budgets",
            errors=errors,
        )
        assert len(errors) >= 2
