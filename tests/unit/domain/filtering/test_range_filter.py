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
"""Tests for GoldRangeFilter dataclass.

Tests the numeric range filter for Gold layer records.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.range_filter import GoldRangeFilter


@pytest.mark.unit
class TestGoldRangeFilter:
    """Test GoldRangeFilter dataclass."""

    def test_valid_with_min_value_only(self) -> None:
        """Test valid filter with only min_value."""
        filter_obj = GoldRangeFilter(
            column="price",
            min_value=10.0,
        )
        assert filter_obj.column == "price"
        assert filter_obj.min_value == pytest.approx(10.0)
        assert filter_obj.max_value is None
        assert filter_obj.include_min is True
        assert filter_obj.include_max is True

    def test_valid_with_max_value_only(self) -> None:
        """Test valid filter with only max_value."""
        filter_obj = GoldRangeFilter(
            column="score",
            max_value=100.0,
        )
        assert filter_obj.max_value == pytest.approx(100.0)
        assert filter_obj.min_value is None

    def test_valid_with_both_values(self) -> None:
        """Test valid filter with both min and max values."""
        filter_obj = GoldRangeFilter(
            column="weight",
            min_value=0.0,
            max_value=1000.0,
        )
        assert filter_obj.min_value == pytest.approx(0.0)
        assert filter_obj.max_value == pytest.approx(1000.0)

    def test_exclusive_bounds(self) -> None:
        """Test filter with exclusive bounds."""
        filter_obj = GoldRangeFilter(
            column="value",
            min_value=0.0,
            max_value=100.0,
            include_min=False,
            include_max=False,
        )
        assert filter_obj.include_min is False
        assert filter_obj.include_max is False

    def test_gold_range_filter__column_raises_error__0ebde9ac(self) -> None:
        """Test that empty column name raises ValueError."""
        with pytest.raises(ValueError, match="column name cannot be empty"):
            GoldRangeFilter(column="", min_value=0.0)

    def test_no_range_constraints_raises_error(self) -> None:
        """Test that missing both min and max value raises ValueError."""
        with pytest.raises(ValueError, match="min_value or max_value"):
            GoldRangeFilter(column="value")

    def test_negative_values(self) -> None:
        """Test filter with negative values."""
        filter_obj = GoldRangeFilter(
            column="temperature",
            min_value=-273.15,
            max_value=1000.0,
        )
        assert filter_obj.min_value == pytest.approx(-273.15)

    def test_zero_values(self) -> None:
        """Test filter with zero as boundary."""
        filter_obj = GoldRangeFilter(
            column="count",
            min_value=0.0,
        )
        assert filter_obj.min_value == pytest.approx(0.0)

    def test_gold_range_filter__immutability__bf216eb8(self) -> None:
        """Test that filter is immutable (frozen)."""
        filter_obj = GoldRangeFilter(column="value", min_value=0.0)
        with pytest.raises(AttributeError):
            filter_obj.min_value = 10.0  # type: ignore[misc]

    def test_integer_values(self) -> None:
        """Test filter accepts integer values (coerced to float)."""
        filter_obj = GoldRangeFilter(
            column="count",
            min_value=0,
            max_value=100,
        )
        assert filter_obj.min_value == 0
        assert filter_obj.max_value == 100
