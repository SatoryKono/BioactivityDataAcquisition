"""Unit tests for debt scorecard primitives."""

from __future__ import annotations

from datetime import date


from bioetl.infrastructure.quality._primitives import (
    _parse_iso_date,
    _parse_quarter_label,
    _quarter_label,
    _validate_budget_mapping,
    _validate_gate_mode,
    _validate_non_negative_int,
)


class TestParseIsoDate:
    """Tests for _parse_iso_date."""

    def test_valid_date(self) -> None:
        """Should parse valid ISO date."""
        result = _parse_iso_date("2025-06-15")
        assert result == date(2025, 6, 15)

    def test_invalid_string(self) -> None:
        """Should return None for invalid date string."""
        assert _parse_iso_date("not-a-date") is None

    def test_non_string_input(self) -> None:
        """Should return None for non-string input."""
        assert _parse_iso_date(12345) is None
        assert _parse_iso_date(None) is None

    def test_empty_string(self) -> None:
        """Should return None for empty string."""
        assert _parse_iso_date("") is None


class TestParseQuarterLabel:
    """Tests for _parse_quarter_label."""

    def test_valid_quarter(self) -> None:
        """Should parse valid quarter labels."""
        assert _parse_quarter_label("2025-Q1") == (2025, 1)
        assert _parse_quarter_label("2025-Q4") == (2025, 4)
        assert _parse_quarter_label("2030-Q2") == (2030, 2)

    def test_with_whitespace(self) -> None:
        """Should strip whitespace."""
        assert _parse_quarter_label("  2025-Q1  ") == (2025, 1)

    def test_invalid_format(self) -> None:
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

    def test_valid_int(self) -> None:
        """Should return value for valid non-negative int."""
        errors: list[str] = []
        result = _validate_non_negative_int(5, field_name="count", errors=errors)
        assert result == 5
        assert errors == []

    def test_zero_is_valid(self) -> None:
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

    def test_none_value(self) -> None:
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

    def test_case_insensitive(self) -> None:
        """Should be case insensitive."""
        errors: list[str] = []
        result = _validate_gate_mode(value="WARN", field_name="gate", errors=errors)
        assert result == "warn"

    def test_with_whitespace(self) -> None:
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

    def test_non_string(self) -> None:
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

    def test_not_dict(self) -> None:
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
