"""Tests for DQ metrics calculation helper functions.

Tests for compute_column_stats, collect_all_columns, compute_single_column_stats,
filter_non_null, calculate_null_rate, make_hashable, calculate_unique_count,
compute_numeric_stats, is_valid_numeric, extract_numeric_values.
"""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.dq_metrics_calculations import (
    calculate_null_rate,
    calculate_unique_count,
    collect_all_columns,
    compute_column_stats,
    compute_numeric_stats,
    compute_single_column_stats,
    extract_numeric_values,
    filter_non_null,
    is_valid_numeric,
    make_hashable,
)


# ===========================================================================
# filter_non_null
# ===========================================================================


class TestFilterNonNull:
    """Tests for filter_non_null function."""

    def test_removes_none_values(self) -> None:
        """Test None values are removed."""
        result = filter_non_null([1, None, 2, None, 3])
        assert result == [1, 2, 3]

    def test_empty_list_returns_empty(self) -> None:
        """Test empty input returns empty list."""
        assert filter_non_null([]) == []

    def test_all_none_returns_empty(self) -> None:
        """Test all-None list returns empty list."""
        assert filter_non_null([None, None, None]) == []

    def test_no_none_returns_same(self) -> None:
        """Test list with no None values returns all values."""
        result = filter_non_null([1, 2, 3])
        assert result == [1, 2, 3]

    def test_mixed_types_preserved(self) -> None:
        """Test mixed types (strings, ints) are preserved."""
        result = filter_non_null(["a", None, 42, None, True])
        assert result == ["a", 42, True]


# ===========================================================================
# calculate_null_rate
# ===========================================================================


class TestCalculateNullRate:
    """Tests for calculate_null_rate function."""

    def test_no_nulls(self) -> None:
        """Test zero null rate when no None values."""
        result = calculate_null_rate([1, 2, 3], 3)
        assert result == pytest.approx(0.0)

    def test_all_nulls(self) -> None:
        """Test null rate of 1.0 when all values are None."""
        result = calculate_null_rate([None, None], 2)
        assert result == pytest.approx(1.0)

    def test_half_nulls(self) -> None:
        """Test null rate of 0.5 when half values are None."""
        result = calculate_null_rate([1, None, 2, None], 4)
        assert result == pytest.approx(0.5)

    def test_rounded_to_four_decimals(self) -> None:
        """Test result is rounded to 4 decimal places."""
        result = calculate_null_rate([None], 3)  # 1/3 = 0.333...
        assert result == round(1 / 3, 4)
        assert len(str(result).split(".")[-1]) <= 4


# ===========================================================================
# make_hashable
# ===========================================================================


class TestMakeHashable:
    """Tests for make_hashable function."""

    def test_int_unchanged(self) -> None:
        """Test integer passes through unchanged."""
        assert make_hashable(42) == 42

    def test_string_unchanged(self) -> None:
        """Test string passes through unchanged."""
        assert make_hashable("hello") == "hello"

    def test_dict_becomes_frozenset(self) -> None:
        """Test dict is converted to frozenset of pairs."""
        result = make_hashable({"a": 1, "b": 2})
        assert isinstance(result, frozenset)
        assert hash(result)  # Verify it is hashable

    def test_list_becomes_tuple(self) -> None:
        """Test list is converted to tuple."""
        result = make_hashable([1, 2, 3])
        assert result == (1, 2, 3)
        assert isinstance(result, tuple)

    def test_nested_dict_in_list(self) -> None:
        """Test nested structures are recursively converted."""
        result = make_hashable([{"key": "val"}])
        assert isinstance(result, tuple)
        assert isinstance(result[0], frozenset)


# ===========================================================================
# calculate_unique_count
# ===========================================================================


class TestCalculateUniqueCount:
    """Tests for calculate_unique_count function."""

    def test_empty_list_returns_zero(self) -> None:
        """Test empty list returns 0."""
        assert calculate_unique_count([]) == 0

    def test_all_same_values(self) -> None:
        """Test all-same values returns 1."""
        assert calculate_unique_count([5, 5, 5]) == 1

    def test_all_unique_values(self) -> None:
        """Test all-unique values returns count."""
        assert calculate_unique_count([1, 2, 3]) == 3

    def test_mixed_duplicates(self) -> None:
        """Test mixed values returns distinct count."""
        assert calculate_unique_count([1, 2, 2, 3, 3, 3]) == 3

    def test_unhashable_values_handled(self) -> None:
        """Test unhashable values (dicts) are handled via make_hashable fallback."""
        result = calculate_unique_count([{"a": 1}, {"a": 1}, {"b": 2}])
        assert result == 2

    def test_string_values(self) -> None:
        """Test string uniqueness."""
        assert calculate_unique_count(["a", "b", "a", "c"]) == 3


# ===========================================================================
# is_valid_numeric
# ===========================================================================


class TestIsValidNumeric:
    """Tests for is_valid_numeric TypeGuard function."""

    def test_int_is_valid(self) -> None:
        """Test plain integer is valid."""
        assert is_valid_numeric(42) is True

    def test_float_is_valid(self) -> None:
        """Test plain float is valid."""
        assert is_valid_numeric(3.14) is True

    def test_bool_is_invalid(self) -> None:
        """Test bool is rejected (bool is subclass of int)."""
        assert is_valid_numeric(True) is False
        assert is_valid_numeric(False) is False

    def test_nan_is_invalid(self) -> None:
        """Test NaN is rejected."""
        assert is_valid_numeric(float("nan")) is False

    def test_inf_is_invalid(self) -> None:
        """Test infinity is rejected."""
        assert is_valid_numeric(float("inf")) is False
        assert is_valid_numeric(float("-inf")) is False

    def test_string_is_invalid(self) -> None:
        """Test string is rejected."""
        assert is_valid_numeric("42") is False

    def test_none_is_invalid(self) -> None:
        """Test None is rejected."""
        assert is_valid_numeric(None) is False

    def test_zero_is_valid(self) -> None:
        """Test zero is valid."""
        assert is_valid_numeric(0) is True

    def test_negative_is_valid(self) -> None:
        """Test negative value is valid."""
        assert is_valid_numeric(-3.14) is True


# ===========================================================================
# extract_numeric_values
# ===========================================================================


class TestExtractNumericValues:
    """Tests for extract_numeric_values function."""

    def test_extracts_ints_and_floats(self) -> None:
        """Test integers and floats are extracted."""
        result = extract_numeric_values([1, 2.5, "text", None, 3])
        assert result == [1.0, 2.5, 3.0]

    def test_booleans_excluded(self) -> None:
        """Test boolean values are excluded."""
        result = extract_numeric_values([True, False, 1, 2])
        assert result == [1.0, 2.0]

    def test_nan_and_inf_excluded(self) -> None:
        """Test NaN and Inf are excluded."""
        result = extract_numeric_values([1.0, float("nan"), float("inf"), 2.0])
        assert result == [1.0, 2.0]

    def test_empty_input(self) -> None:
        """Test empty list returns empty list."""
        assert extract_numeric_values([]) == []

    def test_all_non_numeric(self) -> None:
        """Test all-non-numeric input returns empty list."""
        assert extract_numeric_values(["a", None, True]) == []


# ===========================================================================
# compute_numeric_stats
# ===========================================================================


class TestComputeNumericStats:
    """Tests for compute_numeric_stats function."""

    def test_basic_stats(self) -> None:
        """Test min, max, mean for simple values."""
        min_v, max_v, mean_v = compute_numeric_stats([1.0, 2.0, 3.0])
        assert min_v == pytest.approx(1.0)
        assert max_v == pytest.approx(3.0)
        assert mean_v == pytest.approx(2.0)

    def test_single_value(self) -> None:
        """Test single value yields min=max=mean."""
        min_v, max_v, mean_v = compute_numeric_stats([5.0])
        assert min_v == pytest.approx(5.0)
        assert max_v == pytest.approx(5.0)
        assert mean_v == pytest.approx(5.0)

    def test_empty_returns_none_triple(self) -> None:
        """Test empty list returns (None, None, None)."""
        result = compute_numeric_stats([])
        assert result == (None, None, None)

    def test_all_non_numeric_returns_none_triple(self) -> None:
        """Test list with no valid numerics returns (None, None, None)."""
        result = compute_numeric_stats(["text", None, True])
        assert result == (None, None, None)

    def test_rounded_to_six_decimals(self) -> None:
        """Test results are rounded to 6 decimal places."""
        _, _, mean_v = compute_numeric_stats([1.0, 2.0])
        assert mean_v == pytest.approx(1.5)
        # Verify it uses at most 6 decimal places
        if mean_v is not None:
            decimal_part = str(mean_v).split(".")
            if len(decimal_part) > 1:
                assert len(decimal_part[1]) <= 6


# ===========================================================================
# collect_all_columns
# ===========================================================================


class TestCollectAllColumns:
    """Tests for collect_all_columns function."""

    def test_collects_all_keys(self) -> None:
        """Test all unique keys from records are collected."""
        records = [{"a": 1, "b": 2}, {"b": 3, "c": 4}]
        result = collect_all_columns(records)
        assert result == {"a", "b", "c"}

    def test_empty_records(self) -> None:
        """Test empty list of records returns empty set."""
        assert collect_all_columns([]) == set()

    def test_single_record(self) -> None:
        """Test single record returns its keys."""
        result = collect_all_columns([{"x": 1, "y": 2}])
        assert result == {"x", "y"}


# ===========================================================================
# compute_column_stats
# ===========================================================================


class TestComputeColumnStats:
    """Tests for compute_column_stats function."""

    def test_basic_stats(self) -> None:
        """Test basic column stats for simple records."""
        records = [
            {"value": 1.0, "name": "a"},
            {"value": 2.0, "name": "b"},
            {"value": None, "name": "c"},
        ]
        result = compute_column_stats(records)
        assert "value" in result
        assert "name" in result
        assert result["value"].null_rate == pytest.approx(1 / 3, rel=1e-3)
        assert result["value"].unique_count == 2

    def test_private_columns_excluded(self) -> None:
        """Test columns starting with '_' are excluded."""
        records = [{"_internal": 1, "public": 2}]
        result = compute_column_stats(records)
        assert "_internal" not in result
        assert "public" in result

    def test_empty_records_returns_empty(self) -> None:
        """Test empty records list returns empty dict."""
        result = compute_column_stats([])
        assert result == {}

    def test_all_null_column(self) -> None:
        """Test column with all None values has null_rate=1.0."""
        records = [{"col": None}, {"col": None}]
        result = compute_column_stats(records)
        assert result["col"].null_rate == pytest.approx(1.0)
        assert result["col"].unique_count == 0


# ===========================================================================
# compute_single_column_stats
# ===========================================================================


class TestComputeSingleColumnStats:
    """Tests for compute_single_column_stats function."""

    def test_numeric_column(self) -> None:
        """Test numeric stats computed correctly."""
        records = [{"ic50": 100.0}, {"ic50": 200.0}, {"ic50": 300.0}]
        stats = compute_single_column_stats(records, "ic50")
        assert stats.min_value == pytest.approx(100.0)
        assert stats.max_value == pytest.approx(300.0)
        assert stats.mean_value == pytest.approx(200.0)
        assert stats.null_rate == pytest.approx(0.0)

    def test_string_column_no_numeric_stats(self) -> None:
        """Test string column yields None for numeric stats."""
        records = [{"name": "aspirin"}, {"name": "ibuprofen"}]
        stats = compute_single_column_stats(records, "name")
        assert stats.min_value is None
        assert stats.max_value is None
        assert stats.mean_value is None

    def test_missing_key_treated_as_null(self) -> None:
        """Test missing key in a record is treated as None."""
        records = [{"col": 1.0}, {}]  # second record has no 'col' key
        stats = compute_single_column_stats(records, "col")
        assert stats.null_rate == pytest.approx(0.5)
