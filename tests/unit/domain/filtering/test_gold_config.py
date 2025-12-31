"""Tests for GoldFilterConfig.

Tests the complete Gold layer filter configuration and evaluation.
"""

from __future__ import annotations

from typing import Any

import pytest

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.gold_config import GoldFilterConfig
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter


@pytest.mark.unit
class TestGoldFilterConfigBasic:
    """Test basic GoldFilterConfig functionality."""

    def test_default_config_is_empty(self) -> None:
        """Test that default config is empty."""
        config = GoldFilterConfig()
        assert config.is_empty() is True

    def test_config_with_filters_not_empty(self) -> None:
        """Test that config with filters is not empty."""
        config = GoldFilterConfig(required_fields=("id",))
        assert config.is_empty() is False

    def test_empty_record_passes_empty_config(self) -> None:
        """Test that empty record passes empty config."""
        config = GoldFilterConfig()
        assert config.should_include({}) is True


@pytest.mark.unit
class TestGoldFilterConfigRequiredFields:
    """Test required fields filtering."""

    def test_required_field_present(self) -> None:
        """Test record with required field passes."""
        config = GoldFilterConfig(required_fields=("name",))
        assert config.should_include({"name": "test"}) is True

    def test_required_field_missing(self) -> None:
        """Test record without required field fails."""
        config = GoldFilterConfig(required_fields=("name",))
        assert config.should_include({}) is False

    def test_required_field_is_none(self) -> None:
        """Test record with None required field fails."""
        config = GoldFilterConfig(required_fields=("name",))
        assert config.should_include({"name": None}) is False

    def test_required_field_is_empty_string(self) -> None:
        """Test record with empty string required field fails."""
        config = GoldFilterConfig(required_fields=("name",))
        assert config.should_include({"name": ""}) is False

    def test_multiple_required_fields(self) -> None:
        """Test record must have all required fields."""
        config = GoldFilterConfig(required_fields=("name", "id"))
        assert config.should_include({"name": "test", "id": "123"}) is True
        assert config.should_include({"name": "test"}) is False


@pytest.mark.unit
class TestGoldFilterConfigExcludeIfPresent:
    """Test exclude_if_present filtering."""

    def test_exclude_field_absent(self) -> None:
        """Test record without exclude field passes."""
        config = GoldFilterConfig(exclude_if_present=("deprecated",))
        assert config.should_include({}) is True

    def test_exclude_field_present(self) -> None:
        """Test record with exclude field fails."""
        config = GoldFilterConfig(exclude_if_present=("deprecated",))
        assert config.should_include({"deprecated": True}) is False

    def test_exclude_field_is_none(self) -> None:
        """Test record with None exclude field passes."""
        config = GoldFilterConfig(exclude_if_present=("deprecated",))
        assert config.should_include({"deprecated": None}) is True


@pytest.mark.unit
class TestGoldFilterConfigColumnFilters:
    """Test column value filtering."""

    def test_column_value_in_allowed(self) -> None:
        """Test column value in allowed list passes."""
        config = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="status", values=frozenset({"active", "pending"})
                ),
            ),
        )
        assert config.should_include({"status": "active"}) is True

    def test_column_value_not_in_allowed(self) -> None:
        """Test column value not in allowed list fails."""
        config = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="status", values=frozenset({"active"})),
            ),
        )
        assert config.should_include({"status": "inactive"}) is False


@pytest.mark.unit
class TestGoldFilterConfigRangeFilters:
    """Test numeric range filtering."""

    def test_value_in_range(self) -> None:
        """Test value within range passes."""
        config = GoldFilterConfig(
            range_filters=(
                GoldRangeFilter(column="score", min_value=0.0, max_value=100.0),
            ),
        )
        assert config.should_include({"score": 50}) is True

    def test_value_below_min(self) -> None:
        """Test value below min fails."""
        config = GoldFilterConfig(
            range_filters=(GoldRangeFilter(column="score", min_value=0.0),),
        )
        assert config.should_include({"score": -1}) is False

    def test_value_above_max(self) -> None:
        """Test value above max fails."""
        config = GoldFilterConfig(
            range_filters=(GoldRangeFilter(column="score", max_value=100.0),),
        )
        assert config.should_include({"score": 101}) is False

    def test_value_at_inclusive_boundary(self) -> None:
        """Test value at inclusive boundary passes."""
        config = GoldFilterConfig(
            range_filters=(
                GoldRangeFilter(
                    column="score",
                    min_value=0.0,
                    max_value=100.0,
                    include_min=True,
                    include_max=True,
                ),
            ),
        )
        assert config.should_include({"score": 0}) is True
        assert config.should_include({"score": 100}) is True

    def test_value_at_exclusive_boundary(self) -> None:
        """Test value at exclusive boundary fails."""
        config = GoldFilterConfig(
            range_filters=(
                GoldRangeFilter(
                    column="score",
                    min_value=0.0,
                    max_value=100.0,
                    include_min=False,
                    include_max=False,
                ),
            ),
        )
        assert config.should_include({"score": 0}) is False
        assert config.should_include({"score": 100}) is False

    def test_none_value_fails_range(self) -> None:
        """Test None value fails range check."""
        config = GoldFilterConfig(
            range_filters=(GoldRangeFilter(column="score", min_value=0.0),),
        )
        assert config.should_include({"score": None}) is False

    def test_empty_string_fails_range(self) -> None:
        """Test empty string fails range check."""
        config = GoldFilterConfig(
            range_filters=(GoldRangeFilter(column="score", min_value=0.0),),
        )
        assert config.should_include({"score": ""}) is False

    def test_non_numeric_fails_range(self) -> None:
        """Test non-numeric value fails range check."""
        config = GoldFilterConfig(
            range_filters=(GoldRangeFilter(column="score", min_value=0.0),),
        )
        assert config.should_include({"score": "abc"}) is False


@pytest.mark.unit
class TestGoldFilterConfigListLengthFilters:
    """Test list length filtering."""

    def test_list_length_in_range(self) -> None:
        """Test list length within range passes."""
        config = GoldFilterConfig(
            list_length_filters=(
                GoldListLengthFilter(column="tags", min_length=1, max_length=5),
            ),
        )
        assert config.should_include({"tags": ["a", "b", "c"]}) is True

    def test_list_too_short(self) -> None:
        """Test list shorter than min fails."""
        config = GoldFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", min_length=2),),
        )
        assert config.should_include({"tags": ["a"]}) is False

    def test_list_too_long(self) -> None:
        """Test list longer than max fails."""
        config = GoldFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", max_length=2),),
        )
        assert config.should_include({"tags": ["a", "b", "c"]}) is False

    def test_none_value_length_zero(self) -> None:
        """Test None value has length 0."""
        config = GoldFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", min_length=1),),
        )
        assert config.should_include({"tags": None}) is False

    def test_scalar_value_length_one(self) -> None:
        """Test scalar value has length 1."""
        config = GoldFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", min_length=1),),
        )
        assert config.should_include({"tags": "single"}) is True


@pytest.mark.unit
class TestGoldFilterConfigListContainsFilters:
    """Test list contains filtering."""

    def test_list_contains_all_allowed(self) -> None:
        """Test list with all allowed values passes (mode='all')."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a", "b", "c"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"tags": ["a", "b"]}) is True

    def test_list_contains_disallowed(self) -> None:
        """Test list with disallowed values fails (mode='all')."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a", "b"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"tags": ["a", "c"]}) is False

    def test_list_contains_any(self) -> None:
        """Test list with any allowed value passes (mode='any')."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a", "b"}),
                    mode="any",
                ),
            ),
        )
        assert config.should_include({"tags": ["a", "x"]}) is True

    def test_list_contains_none_any(self) -> None:
        """Test list with no allowed value fails (mode='any')."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a", "b"}),
                    mode="any",
                ),
            ),
        )
        assert config.should_include({"tags": ["x", "y"]}) is False

    def test_empty_list_vacuous_truth(self) -> None:
        """Test empty list passes (vacuous truth)."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"tags": []}) is True

    def test_none_value_vacuous_truth(self) -> None:
        """Test None value passes (vacuous truth)."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tags",
                    values=frozenset({"a"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"tags": None}) is True

    def test_scalar_value_converted_to_set(self) -> None:
        """Test scalar value is converted to set."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="tag",
                    values=frozenset({"valid"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"tag": "valid"}) is True
        assert config.should_include({"tag": "invalid"}) is False


@pytest.mark.unit
class TestGoldFilterConfigCombined:
    """Test combined filter configurations."""

    def test_all_filters_must_pass(self) -> None:
        """Test record must pass all filters."""
        config = GoldFilterConfig(
            required_fields=("name",),
            exclude_if_present=("deleted",),
            range_filters=(GoldRangeFilter(column="score", min_value=0.0),),
        )
        # Passes all
        assert config.should_include({"name": "test", "score": 50}) is True
        # Missing required field
        assert config.should_include({"score": 50}) is False
        # Has excluded field
        assert (
            config.should_include({"name": "test", "score": 50, "deleted": True})
            is False
        )
        # Fails range
        assert config.should_include({"name": "test", "score": -1}) is False
