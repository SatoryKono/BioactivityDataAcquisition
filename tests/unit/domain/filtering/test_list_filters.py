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
"""Tests for Gold layer list-based filters.

Tests GoldListLengthFilter and GoldListContainsFilter validation and behavior.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)


@pytest.mark.unit
class TestGoldListLengthFilter:
    """Test GoldListLengthFilter dataclass."""

    def test_valid_with_min_length(self) -> None:
        """Test valid filter with only min_length."""
        filter_obj = GoldListLengthFilter(
            column="tags",
            min_length=1,
        )
        assert filter_obj.column == "tags"
        assert filter_obj.min_length == 1
        assert filter_obj.max_length is None

    def test_valid_with_max_length(self) -> None:
        """Test valid filter with only max_length."""
        filter_obj = GoldListLengthFilter(
            column="items",
            max_length=10,
        )
        assert filter_obj.max_length == 10
        assert filter_obj.min_length is None

    def test_valid_with_both_lengths(self) -> None:
        """Test valid filter with both min and max length."""
        filter_obj = GoldListLengthFilter(
            column="values",
            min_length=1,
            max_length=100,
        )
        assert filter_obj.min_length == 1
        assert filter_obj.max_length == 100

    def test_empty_column_raises_error(self) -> None:
        """Test that empty column name raises ValueError."""
        with pytest.raises(ValueError, match="column name cannot be empty"):
            GoldListLengthFilter(column="", min_length=1)

    def test_no_length_constraints_raises_error(self) -> None:
        """Test that missing both min and max length raises ValueError."""
        with pytest.raises(ValueError, match="min_length or max_length"):
            GoldListLengthFilter(column="tags")

    def test_list_length_filter__immutability__2de067c8(self) -> None:
        """Test that filter is immutable (frozen)."""
        filter_obj = GoldListLengthFilter(column="tags", min_length=1)
        with pytest.raises(AttributeError):
            filter_obj.min_length = 5  # type: ignore[misc]


@pytest.mark.unit
class TestGoldListContainsFilter:
    """Test GoldListContainsFilter dataclass."""

    def test_valid_with_default_mode(self) -> None:
        """Test valid filter with default 'all' mode."""
        filter_obj = GoldListContainsFilter(
            column="tags",
            values=frozenset({"a", "b", "c"}),
        )
        assert filter_obj.column == "tags"
        assert filter_obj.values == frozenset({"a", "b", "c"})
        assert filter_obj.mode == "all"

    def test_valid_with_any_mode(self) -> None:
        """Test valid filter with 'any' mode."""
        filter_obj = GoldListContainsFilter(
            column="categories",
            values=frozenset({"cat1", "cat2"}),
            mode="any",
        )
        assert filter_obj.mode == "any"

    def test_list_contains_filter__column_raises_error__c5a69a58(self) -> None:
        """Test that empty column name raises ValueError."""
        with pytest.raises(ValueError, match="column name cannot be empty"):
            GoldListContainsFilter(column="", values=frozenset({"a"}))

    def test_empty_values_raises_error(self) -> None:
        """Test that empty values set raises ValueError."""
        with pytest.raises(ValueError, match=r"values .* cannot be empty"):
            GoldListContainsFilter(column="tags", values=frozenset())

    def test_invalid_mode_raises_error(self) -> None:
        """Test that invalid mode raises ValueError."""
        with pytest.raises(ValueError, match="mode must be 'all' or 'any'"):
            GoldListContainsFilter(
                column="tags",
                values=frozenset({"a"}),
                mode="invalid",
            )

    def test_list_contains_filter__immutability__95acd01a(self) -> None:
        """Test that filter is immutable (frozen)."""
        filter_obj = GoldListContainsFilter(
            column="tags",
            values=frozenset({"a"}),
        )
        with pytest.raises(AttributeError):
            filter_obj.mode = "any"  # type: ignore[misc]
