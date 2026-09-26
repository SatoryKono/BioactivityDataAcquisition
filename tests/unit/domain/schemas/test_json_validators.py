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
"""Tests for JSON validators."""

from __future__ import annotations

import pytest

import pandas as pd

from bioetl.domain.schemas.validators import (
    rows_are_valid_json,
    rows_are_valid_json_array,
    rows_are_valid_json_object,
)


pytestmark = pytest.mark.unit


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

    def test_are_valid_json_array__null_values_pass__5e6cb1af(self) -> None:
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

    def test_are_valid_json_array__invalid_json_fails__b7be53f7(self) -> None:
        """Should reject invalid JSON."""
        series = pd.Series(["[unclosed", "not json"])
        result = rows_are_valid_json_array(series)
        assert not result.any()

    def test_are_valid_json_array__mixed_values__c2d7876e(self) -> None:
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

    def test_are_valid_json_object__null_values_pass__de4b9c0d(self) -> None:
        """Should accept null/NaN values."""
        series = pd.Series([None, pd.NA, float("nan")])
        result = rows_are_valid_json_object(series)
        assert result.all()

    def test_json_array_fails(self) -> None:
        """Should reject JSON arrays (not objects)."""
        series = pd.Series(['["a", "b"]', "[]"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_are_valid_json_object__json_primitives_fail__dfc1ced5(self) -> None:
        """Should reject JSON primitives (not objects)."""
        series = pd.Series(['"string"', "123", "true", "null"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_are_valid_json_object__invalid_json_fails__1d6d870d(self) -> None:
        """Should reject invalid JSON."""
        series = pd.Series(["{unclosed", "not json"])
        result = rows_are_valid_json_object(series)
        assert not result.any()

    def test_are_valid_json_object__mixed_values__64166cb7(self) -> None:
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
