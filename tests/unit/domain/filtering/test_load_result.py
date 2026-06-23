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
