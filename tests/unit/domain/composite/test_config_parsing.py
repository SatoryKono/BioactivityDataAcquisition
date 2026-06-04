"""Unit tests for config parsing helpers.

Tests for shared parsing functions in config_parsing.py that validate
and normalize configuration values.
"""

from __future__ import annotations

import pytest

from bioetl.domain.composite.config_parsing import (
    optional_bool,
    optional_int,
    optional_str,
    optional_str_tuple,
    require_object_dict,
    require_object_dict_sequence,
    require_str,
    require_str_tuple,
)


pytestmark = pytest.mark.unit


class TestRequireObjectDict:
    """Tests for require_object_dict function."""

    def test_valid_dict_returns_dict_with_str_keys(self):
        """Valid dict should return dict with string keys."""
        result = require_object_dict({"key1": "value1", "key2": "value2"}, "test_field")
        assert result == {"key1": "value1", "key2": "value2"}

    def test_require_object_dict_converts_non_str_keys(self):
        """Dict with non-string keys should convert keys to strings."""
        result = require_object_dict({1: "value1", 2: "value2"}, "test_field")
        assert result == {"1": "value1", "2": "value2"}

    def test_non_dict_raises_value_error(self):
        """Non-dict value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a dictionary"):
            require_object_dict("not_a_dict", "test_field")

    def test_empty_dict_returns_empty_dict(self):
        """Empty dict should return empty dict."""
        result = require_object_dict({}, "test_field")
        assert result == {}


class TestRequireObjectDictSequence:
    """Tests for require_object_dict_sequence function."""

    def test_valid_list_of_dicts_returns_tuple(self):
        """Valid list of dicts should return tuple of dicts."""
        result = require_object_dict_sequence(
            [{"key1": "value1"}, {"key2": "value2"}], "test_field"
        )
        assert result == ({"key1": "value1"}, {"key2": "value2"})

    def test_valid_tuple_of_dicts_returns_tuple(self):
        """Valid tuple of dicts should return tuple of dicts."""
        result = require_object_dict_sequence(
            ({"key1": "value1"}, {"key2": "value2"}), "test_field"
        )
        assert result == ({"key1": "value1"}, {"key2": "value2"})

    def test_require_object_dict_sequence_converts_non_str_keys(self):
        """Dicts with non-string keys should convert keys to strings."""
        result = require_object_dict_sequence([{1: "value1"}], "test_field")
        assert result == ({"1": "value1"},)

    def test_require_object_dict_sequence_non_list_raises_value_error(self):
        """Non-list value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            require_object_dict_sequence("not_a_list", "test_field")

    def test_list_with_non_dict_raises_value_error(self):
        """List containing non-dict items should raise ValueError."""
        with pytest.raises(ValueError, match="must contain dictionaries"):
            require_object_dict_sequence([{"key": "value"}, "not_a_dict"], "test_field")

    def test_require_object_dict_sequence_empty_list_returns_empty_tuple(self):
        """Empty list should return empty tuple."""
        result = require_object_dict_sequence([], "test_field")
        assert result == ()


class TestRequireStr:
    """Tests for require_str function."""

    def test_require_str_valid_string_returns_string(self):
        """Valid non-empty string should return the string."""
        result = require_str("valid_string", "test_field")
        assert result == "valid_string"

    def test_require_str_empty_string_raises_value_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            require_str("", "test_field")

    def test_require_str_non_string_raises_value_error(self):
        """Non-string value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            require_str(123, "test_field")

    def test_none_raises_value_error(self):
        """None value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty string"):
            require_str(None, "test_field")


class TestOptionalStr:
    """Tests for optional_str function."""

    def test_optional_str_valid_string_returns_string(self):
        """Valid non-empty string should return the string."""
        result = optional_str("valid_string", "test_field")
        assert result == "valid_string"

    def test_optional_str_none_returns_none(self):
        """None value should return None."""
        result = optional_str(None, "test_field")
        assert result is None

    def test_optional_str_empty_string_raises_value_error(self):
        """Empty string should raise ValueError."""
        with pytest.raises(
            ValueError, match="must be a non-empty string when provided"
        ):
            optional_str("", "test_field")

    def test_optional_str_non_string_raises_value_error(self):
        """Non-string value should raise ValueError."""
        with pytest.raises(
            ValueError, match="must be a non-empty string when provided"
        ):
            optional_str(123, "test_field")


class TestOptionalBool:
    """Tests for optional_bool function."""

    def test_true_returns_true(self):
        """True value should return True."""
        result = optional_bool(True, False, "test_field")
        assert result is True

    def test_false_returns_false(self):
        """False value should return False."""
        result = optional_bool(False, True, "test_field")
        assert result is False

    def test_optional_bool_none_returns_default(self):
        """None value should return the default."""
        result = optional_bool(None, True, "test_field")
        assert result is True

    def test_default_false(self):
        """None with default False should return False."""
        result = optional_bool(None, False, "test_field")
        assert result is False

    def test_non_bool_raises_value_error(self):
        """Non-bool value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a boolean"):
            optional_bool("not_a_bool", True, "test_field")

    def test_int_raises_value_error(self):
        """Integer value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a boolean"):
            optional_bool(1, True, "test_field")


class TestOptionalInt:
    """Tests for optional_int function."""

    def test_valid_int_returns_int(self):
        """Valid integer should return the integer."""
        result = optional_int(42, "test_field")
        assert result == 42

    def test_optional_int_none_returns_none(self):
        """None value should return None."""
        result = optional_int(None, "test_field")
        assert result is None

    def test_optional_int_none_returns_default(self):
        """None value with default should return the default."""
        result = optional_int(None, "test_field", default=100)
        assert result == 100

    def test_zero_returns_zero(self):
        """Zero value should return zero."""
        result = optional_int(0, "test_field")
        assert result == 0

    def test_negative_int_returns_negative(self):
        """Negative integer should return negative."""
        result = optional_int(-42, "test_field")
        assert result == -42

    def test_optional_int_bool_raises_value_error(self):
        """Boolean value should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            optional_int(True, "test_field")

    def test_string_raises_value_error(self):
        """String value should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            optional_int("42", "test_field")

    def test_float_raises_value_error(self):
        """Float value should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            optional_int(42.0, "test_field")


class TestRequireStrTuple:
    """Tests for require_str_tuple function."""

    def test_require_str_tuple_valid_list_returns_tuple(self):
        """Valid list of strings should return tuple."""
        result = require_str_tuple(["str1", "str2", "str3"], "test_field")
        assert result == ("str1", "str2", "str3")

    def test_valid_tuple_returns_tuple(self):
        """Valid tuple of strings should return tuple."""
        result = require_str_tuple(("str1", "str2"), "test_field")
        assert result == ("str1", "str2")

    def test_single_string_returns_tuple(self):
        """Single string should return single-element tuple."""
        result = require_str_tuple(["single"], "test_field")
        assert result == ("single",)

    def test_require_str_tuple_empty_list_returns_empty_tuple(self):
        """Empty list should return empty tuple."""
        result = require_str_tuple([], "test_field")
        assert result == ()

    def test_require_str_tuple_non_list_raises_value_error(self):
        """Non-list value should raise ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            require_str_tuple("not_a_list", "test_field")

    def test_list_with_empty_string_raises_value_error(self):
        """List containing empty string should raise ValueError."""
        with pytest.raises(ValueError, match="must contain non-empty strings"):
            require_str_tuple(["valid", "", "also_valid"], "test_field")

    def test_list_with_non_string_raises_value_error(self):
        """List containing non-string should raise ValueError."""
        with pytest.raises(ValueError, match="must contain non-empty strings"):
            require_str_tuple(["valid", 123, "also_valid"], "test_field")


class TestOptionalStrTuple:
    """Tests for optional_str_tuple function."""

    def test_optional_str_tuple_valid_list_returns_tuple(self):
        """Valid list of strings should return tuple."""
        result = optional_str_tuple(["str1", "str2"], "test_field")
        assert result == ("str1", "str2")

    def test_optional_str_tuple_none_returns_none(self):
        """None value should return None."""
        result = optional_str_tuple(None, "test_field")
        assert result is None

    def test_optional_str_tuple_empty_list_returns_empty_tuple(self):
        """Empty list should return empty tuple."""
        result = optional_str_tuple([], "test_field")
        assert result == ()

    def test_invalid_list_raises_value_error(self):
        """Invalid list should raise ValueError."""
        with pytest.raises(ValueError, match="must contain non-empty strings"):
            optional_str_tuple(["valid", 123], "test_field")
