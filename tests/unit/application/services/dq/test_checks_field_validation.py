"""Unit tests for field validation checks.

Tests for all validation types defined in FieldValidation:
- non_empty, json_array, json_object, url, boolean_strict, date_iso
- Also tests existing types: required, range, pattern, enum
"""

from __future__ import annotations

import math

import pytest

from bioetl.application.services.dq._checks_field_validation import validate_field_value


# =============================================================================
# non_empty validation
# =============================================================================


class TestNonEmpty:
    """Tests for non_empty validation type."""

    @pytest.mark.parametrize("value", ["x", "hello world", "  x  ", "0"])
    def test_non_empty_valid(self, value: str) -> None:
        assert validate_field_value(value, "non_empty") is True

    @pytest.mark.parametrize("value", ["", "   ", "  \t  ", "\n"])
    def test_non_empty_invalid(self, value: str) -> None:
        assert validate_field_value(value, "non_empty") is False

    def test_non_empty_null_nullable(self) -> None:
        assert validate_field_value(None, "non_empty", nullable=True) is True

    def test_non_empty_null_not_nullable(self) -> None:
        assert validate_field_value(None, "non_empty", nullable=False) is False

    def test_non_empty_nan_nullable(self) -> None:
        assert validate_field_value(float("nan"), "non_empty", nullable=True) is True


# =============================================================================
# json_array validation
# =============================================================================


class TestJsonArray:
    """Tests for json_array validation type."""

    @pytest.mark.parametrize(
        "value",
        ['["a","b"]', "[1,2,3]", "[]", '[{"key": "val"}]'],
    )
    def test_json_array_valid(self, value: str) -> None:
        assert validate_field_value(value, "json_array") is True

    @pytest.mark.parametrize(
        "value",
        ['{"key": "val"}', '"string"', "not json", "123", "null"],
    )
    def test_json_array_invalid(self, value: str) -> None:
        assert validate_field_value(value, "json_array") is False

    def test_json_array_null_nullable(self) -> None:
        assert validate_field_value(None, "json_array", nullable=True) is True

    def test_json_array_null_not_nullable(self) -> None:
        assert validate_field_value(None, "json_array", nullable=False) is False

    def test_json_array_element_type_string_pass(self) -> None:
        assert (
            validate_field_value(
                '["a","b"]', "json_array", element_type="string"
            )
            is True
        )

    def test_json_array_element_type_string_fail(self) -> None:
        assert (
            validate_field_value(
                "[1,2]", "json_array", element_type="string"
            )
            is False
        )

    def test_json_array_element_type_integer_pass(self) -> None:
        assert (
            validate_field_value(
                "[1,2,3]", "json_array", element_type="integer"
            )
            is True
        )

    def test_json_array_element_type_integer_fail(self) -> None:
        assert (
            validate_field_value(
                '["a"]', "json_array", element_type="integer"
            )
            is False
        )

    def test_json_array_element_type_object_pass(self) -> None:
        assert (
            validate_field_value(
                '[{"k":"v"}]', "json_array", element_type="object"
            )
            is True
        )

    def test_json_array_element_pattern_pass(self) -> None:
        assert (
            validate_field_value(
                '["123","456"]', "json_array", element_pattern=r"^\d+$"
            )
            is True
        )

    def test_json_array_element_pattern_fail(self) -> None:
        assert (
            validate_field_value(
                '["abc","456"]', "json_array", element_pattern=r"^\d+$"
            )
            is False
        )

    def test_json_array_min_items_pass(self) -> None:
        assert (
            validate_field_value('["x"]', "json_array", min_items=1) is True
        )

    def test_json_array_min_items_fail(self) -> None:
        assert (
            validate_field_value("[]", "json_array", min_items=1) is False
        )


# =============================================================================
# json_object validation
# =============================================================================


class TestJsonObject:
    """Tests for json_object validation type."""

    @pytest.mark.parametrize(
        "value",
        ['{}', '{"key": "value"}', '{"nested": {"a": 1}}'],
    )
    def test_json_object_valid(self, value: str) -> None:
        assert validate_field_value(value, "json_object") is True

    @pytest.mark.parametrize(
        "value",
        ["[]", '"string"', "not json", "123", "null"],
    )
    def test_json_object_invalid(self, value: str) -> None:
        assert validate_field_value(value, "json_object") is False

    def test_json_object_null_nullable(self) -> None:
        assert validate_field_value(None, "json_object", nullable=True) is True

    def test_json_object_null_not_nullable(self) -> None:
        assert validate_field_value(None, "json_object", nullable=False) is False


# =============================================================================
# url validation
# =============================================================================


class TestUrl:
    """Tests for url validation type."""

    @pytest.mark.parametrize(
        "value",
        [
            "https://example.com",
            "http://example.com",
            "https://example.com/path?q=1",
            "http://localhost:8080",
        ],
    )
    def test_url_valid(self, value: str) -> None:
        assert validate_field_value(value, "url") is True

    @pytest.mark.parametrize(
        "value",
        ["ftp://example.com", "", "example.com", "not a url", "mailto:a@b.com"],
    )
    def test_url_invalid(self, value: str) -> None:
        assert validate_field_value(value, "url") is False

    def test_url_null_nullable(self) -> None:
        assert validate_field_value(None, "url", nullable=True) is True

    def test_url_null_not_nullable(self) -> None:
        assert validate_field_value(None, "url", nullable=False) is False


# =============================================================================
# boolean_strict validation
# =============================================================================


class TestBooleanStrict:
    """Tests for boolean_strict validation type."""

    @pytest.mark.parametrize("value", [True, False])
    def test_boolean_strict_valid(self, value: bool) -> None:
        assert validate_field_value(value, "boolean_strict") is True

    @pytest.mark.parametrize("value", [0, 1, "true", "false", "True", "False", "yes"])
    def test_boolean_strict_invalid(self, value: object) -> None:
        assert validate_field_value(value, "boolean_strict") is False

    def test_boolean_strict_null_nullable(self) -> None:
        assert validate_field_value(None, "boolean_strict", nullable=True) is True

    def test_boolean_strict_null_not_nullable(self) -> None:
        assert validate_field_value(None, "boolean_strict", nullable=False) is False


# =============================================================================
# date_iso validation
# =============================================================================


class TestDateIso:
    """Tests for date_iso validation type."""

    @pytest.mark.parametrize(
        "value",
        ["2024-01-01", "2024-02-29", "1999-12-31", "2000-06-15"],
    )
    def test_date_iso_valid(self, value: str) -> None:
        assert validate_field_value(value, "date_iso") is True

    @pytest.mark.parametrize(
        "value",
        [
            "2024-13-01",  # invalid month
            "2024-1-1",  # not zero-padded
            "2023-02-29",  # not a leap year
            "01-01-2024",  # wrong order
            "2024/01/01",  # wrong separator
            "not a date",
            "",
        ],
    )
    def test_date_iso_invalid(self, value: str) -> None:
        assert validate_field_value(value, "date_iso") is False

    def test_date_iso_null_nullable(self) -> None:
        assert validate_field_value(None, "date_iso", nullable=True) is True

    def test_date_iso_null_not_nullable(self) -> None:
        assert validate_field_value(None, "date_iso", nullable=False) is False


# =============================================================================
# Existing types (regression tests)
# =============================================================================


class TestRequired:
    """Tests for required validation type."""

    def test_required_with_value(self) -> None:
        assert validate_field_value("abc", "required") is True

    def test_required_null_not_nullable(self) -> None:
        assert validate_field_value(None, "required", nullable=False) is False

    def test_required_null_nullable(self) -> None:
        assert validate_field_value(None, "required", nullable=True) is True


class TestRange:
    """Tests for range validation type."""

    def test_range_in_bounds(self) -> None:
        assert (
            validate_field_value(50, "range", min_value=0.0, max_value=100.0)
            is True
        )

    def test_range_out_of_bounds(self) -> None:
        assert (
            validate_field_value(150, "range", min_value=0.0, max_value=100.0)
            is False
        )

    def test_range_non_numeric(self) -> None:
        assert (
            validate_field_value("abc", "range", min_value=0.0, max_value=100.0)
            is False
        )


class TestPattern:
    """Tests for pattern validation type."""

    def test_pattern_match(self) -> None:
        assert (
            validate_field_value("CHEMBL123", "pattern", pattern=r"^CHEMBL\d+$")
            is True
        )

    def test_pattern_no_match(self) -> None:
        assert (
            validate_field_value("invalid", "pattern", pattern=r"^CHEMBL\d+$")
            is False
        )


class TestEnum:
    """Tests for enum validation type."""

    def test_enum_in_allowed(self) -> None:
        assert (
            validate_field_value("A", "enum", allowed=("A", "B", "C")) is True
        )

    def test_enum_not_in_allowed(self) -> None:
        assert (
            validate_field_value("D", "enum", allowed=("A", "B", "C")) is False
        )


# =============================================================================
# Edge cases
# =============================================================================


class TestEdgeCases:
    """Edge case tests for field validation."""

    def test_nan_nullable(self) -> None:
        assert validate_field_value(float("nan"), "required", nullable=True) is True

    def test_nan_not_nullable(self) -> None:
        assert validate_field_value(float("nan"), "required", nullable=False) is False

    def test_unknown_type_passes(self) -> None:
        """Unknown validation type should pass (no handler)."""
        assert validate_field_value("anything", "unknown_type") is True

    def test_math_nan(self) -> None:
        assert validate_field_value(math.nan, "non_empty", nullable=True) is True

    def test_empty_string_non_empty_url(self) -> None:
        """Empty string fails both non_empty and url."""
        assert validate_field_value("", "non_empty") is False
        assert validate_field_value("", "url") is False

    def test_json_array_mixed_element_types(self) -> None:
        """Mixed types in json_array when element_type not specified."""
        assert validate_field_value('[1, "a", null]', "json_array") is True

    def test_boolean_strict_with_int_one(self) -> None:
        """int 1 is not a valid boolean_strict."""
        assert validate_field_value(1, "boolean_strict") is False

    def test_boolean_strict_with_int_zero(self) -> None:
        """int 0 is not a valid boolean_strict."""
        assert validate_field_value(0, "boolean_strict") is False
