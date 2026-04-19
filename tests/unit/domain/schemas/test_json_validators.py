"""Tests for JSON validators."""

from __future__ import annotations

import pandas as pd

from bioetl.domain.schemas.validators import (
    rows_are_valid_json,
    rows_are_valid_json_array,
    rows_are_valid_json_object,
)


class TestRowsAreValidJson:
    """Tests for rows_are_valid_json validator."""

    def test_valid_json_array(self) -> None:
        """Should accept valid JSON arrays."""
        series = pd.Series(['["a", "b"]', "[1, 2, 3]", "[]"])
        result = rows_are_valid_json(series)
        assert isinstance(result, pd.Series)
        assert result.all()

    def test_valid_json_object(self) -> None:
        """Should accept valid JSON objects."""
        series = pd.Series(['{"key": "value"}', '{"a": 1}', "{}"])
        result = rows_are_valid_json(series)
        assert result.all()

    def test_valid_json_primitives(self) -> None:
        """Should accept valid JSON primitives."""
        series = pd.Series(['"string"', "123", "true", "null"])
        result = rows_are_valid_json(series)
        assert result.all()

    def test_null_values_pass(self) -> None:
        """Should accept null/NaN values."""
        series = pd.Series([None, pd.NA, float("nan")])
        result = rows_are_valid_json(series)
        assert result.all()

    def test_invalid_json_fails(self) -> None:
        """Should reject invalid JSON."""
        series = pd.Series(["not json", "{invalid}", "[unclosed"])
        result = rows_are_valid_json(series)
        assert not result.any()

    def test_mixed_values(self) -> None:
        """Should handle mixed valid/invalid values."""
        series = pd.Series(['["valid"]', "invalid", None])
        result = rows_are_valid_json(series)
        assert result.tolist() == [True, False, True]


class TestRowsAreValidJsonArray:
    """Tests for rows_are_valid_json_array validator."""

    def test_valid_arrays(self) -> None:
        """Should accept valid JSON arrays."""
        series = pd.Series(['["a", "b"]', "[1, 2, 3]", "[]", "[[1], [2]]"])
        result = rows_are_valid_json_array(series)
        assert isinstance(result, pd.Series)
        assert result.all()

    def test_null_values_pass(self) -> None:
        """Should accept null/NaN values."""
        series = pd.Series([None, pd.NA, float("nan")])
        result = rows_are_valid_json_array(series)
        assert result.all()

    def test_json_object_fails(self) -> None:
        """Should reject JSON objects (not arrays)."""
        series = pd.Series(['{"key": "value"}', "{}"])
        result = rows_are_valid_json_array(series)
        assert not result.any()

    def test_json_primitives_fail(self) -> None:
        """Should reject JSON primitives (not arrays)."""
        series = pd.Series(['"string"', "123", "true", "null"])
        result = rows_are_valid_json_array(series)
        assert not result.any()

    def test_invalid_json_fails(self) -> None:
        """Should reject invalid JSON."""
        series = pd.Series(["[unclosed", "not json"])
        result = rows_are_valid_json_array(series)
        assert not result.any()

    def test_mixed_values(self) -> None:
        """Should handle mixed valid/invalid values."""
        series = pd.Series(['["valid"]', '{"object": 1}', None, "invalid"])
        result = rows_are_valid_json_array(series)
        assert result.tolist() == [True, False, True, False]


class TestRowsAreValidJsonObject:
    """Tests for rows_are_valid_json_object validator."""

    def test_valid_objects(self) -> None:
        """Should accept valid JSON objects."""
        series = pd.Series(['{"key": "value"}', '{"a": 1, "b": 2}', "{}"])
        result = rows_are_valid_json_object(series)
        assert isinstance(result, pd.Series)
        assert result.all()

    def test_nested_objects(self) -> None:
        """Should accept nested JSON objects."""
        series = pd.Series(['{"outer": {"inner": 1}}', '{"arr": [1, 2]}'])
        result = rows_are_valid_json_object(series)
        assert result.all()

    def test_null_values_pass(self) -> None:
        """Should accept null/NaN values."""
        series = pd.Series([None, pd.NA, float("nan")])
        result = rows_are_valid_json_object(series)
        assert result.all()

    def test_json_array_fails(self) -> None:
        """Should reject JSON arrays (not objects)."""
        series = pd.Series(['["a", "b"]', "[]"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_json_primitives_fail(self) -> None:
        """Should reject JSON primitives (not objects)."""
        series = pd.Series(['"string"', "123", "true", "null"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_invalid_json_fails(self) -> None:
        """Should reject invalid JSON."""
        series = pd.Series(["{unclosed", "not json"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_mixed_values(self) -> None:
        """Should handle mixed valid/invalid values."""
        series = pd.Series(['{"valid": 1}', '["array"]', None, "invalid"])
        result = rows_are_valid_json_object(series)
        assert result.tolist() == [True, False, True, False]


class TestPanderaChecks:
    """Tests for pre-built Pandera checks."""

    def test_json_check_importable(self) -> None:
        """Should be able to import JSON_CHECK."""
        from bioetl.domain.schemas.validators import JSON_CHECK

        assert JSON_CHECK is not None
        assert JSON_CHECK.name == "valid_json"

    def test_json_array_check_importable(self) -> None:
        """Should be able to import JSON_ARRAY_CHECK."""
        from bioetl.domain.schemas.validators import JSON_ARRAY_CHECK

        assert JSON_ARRAY_CHECK is not None
        assert JSON_ARRAY_CHECK.name == "valid_json_array"

    def test_json_object_check_importable(self) -> None:
        """Should be able to import JSON_OBJECT_CHECK."""
        from bioetl.domain.schemas.validators import JSON_OBJECT_CHECK

        assert JSON_OBJECT_CHECK is not None
        assert JSON_OBJECT_CHECK.name == "valid_json_object"
