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
"""Tests for FilterLoadResult dataclass.

Tests the filter load result container with deduplication metadata.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.load_result import FilterLoadResult


@pytest.mark.unit
class TestFilterLoadResult:
    """Test FilterLoadResult dataclass."""

    def test_valid_creation_no_duplicates(self) -> None:
        """Test valid result creation with no duplicates."""
        result = FilterLoadResult(
            ids=("id1", "id2", "id3"),
            total_count=3,
            unique_count=3,
            duplicate_count=0,
            duplicates=frozenset(),
        )
        assert result.ids == ("id1", "id2", "id3")
        assert result.total_count == 3
        assert result.unique_count == 3
        assert result.duplicate_count == 0
        assert result.has_duplicates is False

    def test_valid_creation_with_duplicates(self) -> None:
        """Test valid result creation with duplicates."""
        result = FilterLoadResult(
            ids=("id1", "id2"),
            total_count=5,
            unique_count=2,
            duplicate_count=3,
            duplicates=frozenset({"id1", "id2"}),
        )
        assert result.total_count == 5
        assert result.unique_count == 2
        assert result.duplicate_count == 3
        assert result.has_duplicates is True
        assert result.duplicates == frozenset({"id1", "id2"})

    def test_unique_count_mismatch_raises_error(self) -> None:
        """Test that unique_count must match len(ids)."""
        with pytest.raises(ValueError, match=r"unique_count .* must match len\(ids\)"):
            FilterLoadResult(
                ids=("id1", "id2"),
                total_count=2,
                unique_count=3,  # Wrong - doesn't match len(ids)
                duplicate_count=0,
                duplicates=frozenset(),
            )

    def test_duplicate_count_mismatch_raises_error(self) -> None:
        """Test that duplicate_count must equal total - unique."""
        with pytest.raises(ValueError, match=r"duplicate_count .* must equal"):
            FilterLoadResult(
                ids=("id1", "id2"),
                total_count=5,
                unique_count=2,
                duplicate_count=2,  # Wrong - should be 3 (5-2)
                duplicates=frozenset(),
            )

    def test_has_duplicates_property_true(self) -> None:
        """Test has_duplicates returns True when duplicates exist."""
        result = FilterLoadResult(
            ids=("id1",),
            total_count=3,
            unique_count=1,
            duplicate_count=2,
            duplicates=frozenset({"id1"}),
        )
        assert result.has_duplicates is True

    def test_has_duplicates_property_false(self) -> None:
        """Test has_duplicates returns False when no duplicates."""
        result = FilterLoadResult(
            ids=("id1", "id2"),
            total_count=2,
            unique_count=2,
            duplicate_count=0,
            duplicates=frozenset(),
        )
        assert result.has_duplicates is False

    def test_filter_load_result__immutability__a49154af(self) -> None:
        """Test that result is immutable (frozen)."""
        result = FilterLoadResult(
            ids=("id1",),
            total_count=1,
            unique_count=1,
            duplicate_count=0,
            duplicates=frozenset(),
        )
        with pytest.raises(AttributeError):
            result.total_count = 10  # type: ignore[misc]

    def test_empty_ids(self) -> None:
        """Test result with empty ids tuple."""
        result = FilterLoadResult(
            ids=(),
            total_count=0,
            unique_count=0,
            duplicate_count=0,
            duplicates=frozenset(),
        )
        assert len(result.ids) == 0
        assert result.has_duplicates is False

    def test_valid_multi_column_result(self) -> None:
        """Ordered fields and row-wise combinations form a valid result."""
        result = FilterLoadResult(
            column_ids={"target_id": ("T1", "T2"), "assay_id": ("A1",)},
            filter_fields=("target_id", "assay_id"),
            valid_combinations=frozenset({("T1", "A1"), ("T2", "A1")}),
        )

        assert result.is_multi_column is True

    def test_multi_column_fields_must_match_mapping_order(self) -> None:
        """Combination positions are bound to the declared mapping order."""
        with pytest.raises(ValueError, match="must match column_ids keys in order"):
            FilterLoadResult(
                column_ids={"target_id": ("T1",), "assay_id": ("A1",)},
                filter_fields=("assay_id", "target_id"),
            )

    def test_multi_column_combination_must_match_field_arity(self) -> None:
        """Every exact combination supplies one value per filter field."""
        with pytest.raises(ValueError, match="must match filter_fields arity"):
            FilterLoadResult(
                column_ids={"target_id": ("T1",), "assay_id": ("A1",)},
                filter_fields=("target_id", "assay_id"),
                valid_combinations=frozenset({("T1",)}),
            )

    def test_multi_column_combination_values_must_be_declared(self) -> None:
        """Each row-wise value belongs to its corresponding column domain."""
        with pytest.raises(ValueError, match="must belong to column_ids"):
            FilterLoadResult(
                column_ids={"target_id": ("T1",), "assay_id": ("A1",)},
                filter_fields=("target_id", "assay_id"),
                valid_combinations=frozenset({("T1", "A2")}),
            )
