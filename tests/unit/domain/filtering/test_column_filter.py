"""Tests for GoldColumnFilter and FilterOperator.

Tests the column filter with support for multiple operators.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.column_filter import FilterOperator, GoldColumnFilter


@pytest.mark.unit
class TestFilterOperator:
    """Tests for FilterOperator enum."""

    def test_all_operators_defined(self) -> None:
        """Test that all operators are defined."""
        expected = {
            "in",
            "not_in",
            "is_null",
            "is_not_null",
            "is_empty",
            "is_not_empty",
        }
        actual = {op.value for op in FilterOperator}
        assert actual == expected

    def test_operators_are_string_enum(self) -> None:
        """Test that operators can be used as strings."""
        assert FilterOperator.IN == "in"
        assert FilterOperator.NOT_IN == "not_in"
        assert FilterOperator.IS_NULL == "is_null"
        assert FilterOperator.IS_NOT_NULL == "is_not_null"
        assert FilterOperator.IS_EMPTY == "is_empty"
        assert FilterOperator.IS_NOT_EMPTY == "is_not_empty"


@pytest.mark.unit
class TestGoldColumnFilterValidation:
    """Tests for GoldColumnFilter validation."""

    def test_filter_validation__empty_column_raises__42a6f1b0(self) -> None:
        """Test that empty column name raises error."""
        with pytest.raises(ValueError, match="column name cannot be empty"):
            GoldColumnFilter(column="", values=frozenset(["a"]))

    def test_in_operator_requires_values(self) -> None:
        """Test that IN operator requires values."""
        with pytest.raises(ValueError, match="values required"):
            GoldColumnFilter(column="x", operator=FilterOperator.IN, values=None)

    def test_in_operator_requires_non_empty_values(self) -> None:
        """Test that IN operator requires non-empty values."""
        with pytest.raises(ValueError, match="values required"):
            GoldColumnFilter(column="x", operator=FilterOperator.IN, values=frozenset())

    def test_not_in_operator_requires_values(self) -> None:
        """Test that NOT_IN operator requires values."""
        with pytest.raises(ValueError, match="values required"):
            GoldColumnFilter(column="x", operator=FilterOperator.NOT_IN, values=None)

    def test_is_null_rejects_values(self) -> None:
        """Test that IS_NULL operator rejects values."""
        with pytest.raises(ValueError, match="values must be None"):
            GoldColumnFilter(
                column="x",
                operator=FilterOperator.IS_NULL,
                values=frozenset(["a"]),
            )

    def test_is_not_null_rejects_values(self) -> None:
        """Test that IS_NOT_NULL operator rejects values."""
        with pytest.raises(ValueError, match="values must be None"):
            GoldColumnFilter(
                column="x",
                operator=FilterOperator.IS_NOT_NULL,
                values=frozenset(["a"]),
            )

    def test_is_empty_rejects_values(self) -> None:
        """Test that IS_EMPTY operator rejects values."""
        with pytest.raises(ValueError, match="values must be None"):
            GoldColumnFilter(
                column="x",
                operator=FilterOperator.IS_EMPTY,
                values=frozenset(["a"]),
            )

    def test_is_not_empty_rejects_values(self) -> None:
        """Test that IS_NOT_EMPTY operator rejects values."""
        with pytest.raises(ValueError, match="values must be None"):
            GoldColumnFilter(
                column="x",
                operator=FilterOperator.IS_NOT_EMPTY,
                values=frozenset(["a"]),
            )


@pytest.mark.unit
class TestGoldColumnFilterCreation:
    """Tests for successful GoldColumnFilter creation."""

    def test_in_operator_with_values(self) -> None:
        """Test IN operator filter creation."""
        f = GoldColumnFilter(
            column="status",
            operator=FilterOperator.IN,
            values=frozenset(["active", "pending"]),
        )
        assert f.column == "status"
        assert f.operator == FilterOperator.IN
        assert f.values == frozenset(["active", "pending"])

    def test_not_in_operator_with_values(self) -> None:
        """Test NOT_IN operator filter creation."""
        f = GoldColumnFilter(
            column="target_type",
            operator=FilterOperator.NOT_IN,
            values=frozenset(["UNKNOWN", "UNCHECKED"]),
        )
        assert f.column == "target_type"
        assert f.operator == FilterOperator.NOT_IN
        assert f.values == frozenset(["UNKNOWN", "UNCHECKED"])

    def test_is_null_operator(self) -> None:
        """Test IS_NULL operator filter creation."""
        f = GoldColumnFilter(column="field", operator=FilterOperator.IS_NULL)
        assert f.column == "field"
        assert f.operator == FilterOperator.IS_NULL
        assert f.values is None

    def test_is_not_null_operator(self) -> None:
        """Test IS_NOT_NULL operator filter creation."""
        f = GoldColumnFilter(column="pchembl", operator=FilterOperator.IS_NOT_NULL)
        assert f.column == "pchembl"
        assert f.operator == FilterOperator.IS_NOT_NULL
        assert f.values is None

    def test_is_empty_operator(self) -> None:
        """Test IS_EMPTY operator filter creation."""
        f = GoldColumnFilter(column="data", operator=FilterOperator.IS_EMPTY)
        assert f.column == "data"
        assert f.operator == FilterOperator.IS_EMPTY
        assert f.values is None

    def test_is_not_empty_operator(self) -> None:
        """Test IS_NOT_EMPTY operator filter creation."""
        f = GoldColumnFilter(column="smiles", operator=FilterOperator.IS_NOT_EMPTY)
        assert f.column == "smiles"
        assert f.operator == FilterOperator.IS_NOT_EMPTY
        assert f.values is None

    def test_default_operator_is_in(self) -> None:
        """Test that default operator is IN."""
        f = GoldColumnFilter(column="x", values=frozenset(["a"]))
        assert f.operator == FilterOperator.IN

    def test_filter_is_immutable(self) -> None:
        """Test that filter is immutable (frozen dataclass)."""
        f = GoldColumnFilter(column="x", values=frozenset(["a"]))
        with pytest.raises(AttributeError):
            f.column = "y"  # type: ignore[misc]

    def test_filter_has_slots(self) -> None:
        """Test that filter uses slots for memory efficiency."""
        f = GoldColumnFilter(column="x", values=frozenset(["a"]))
        assert hasattr(f, "__slots__") or not hasattr(f, "__dict__")
