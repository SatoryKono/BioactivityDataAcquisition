"""Tests for GoldFilterConfig.

Tests the complete Gold layer filter configuration and evaluation.
"""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.column_filter import FilterOperator, GoldColumnFilter
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

    def test_json_string_list_uses_decoded_length(self) -> None:
        """Test JSON-encoded list strings use list semantics for length checks."""
        config = GoldFilterConfig(
            list_length_filters=(GoldListLengthFilter(column="tags", max_length=2),),
        )
        assert config.should_include({"tags": '["a", "b"]'}) is True
        assert config.should_include({"tags": '["a", "b", "c"]'}) is False


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

    def test_json_string_list_matches_contains_filters(self) -> None:
        """Test JSON-encoded list strings are decoded for contains checks."""
        config = GoldFilterConfig(
            list_contains_filters=(
                GoldListContainsFilter(
                    column="component_types",
                    values=frozenset({"PROTEIN"}),
                    mode="all",
                ),
            ),
        )
        assert config.should_include({"component_types": '["PROTEIN"]'}) is True
        assert (
            config.should_include({"component_types": '["PROTEIN", "RNA"]'}) is False
        )

    def test_chembl_target_gold_filters_accept_stringified_component_lists(self) -> None:
        """Test chembl_target Gold filters accept stringified list fields."""
        config = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="target_type",
                    values=frozenset({"SINGLE PROTEIN"}),
                ),
            ),
            list_length_filters=(
                GoldListLengthFilter(
                    column="component_accessions",
                    min_length=1,
                    max_length=1,
                ),
                GoldListLengthFilter(column="component_ids", min_length=1),
            ),
            list_contains_filters=(
                GoldListContainsFilter(
                    column="component_types",
                    values=frozenset({"PROTEIN"}),
                    mode="all",
                ),
            ),
            required_fields=("pref_name", "organism"),
        )
        record = {
            "target_type": "SINGLE PROTEIN",
            "pref_name": "Cytochrome b",
            "organism": "Plasmodium falciparum",
            "component_accessions": '["Q02768"]',
            "component_ids": "[67]",
            "component_types": '["PROTEIN"]',
        }
        assert config.should_include(record) is True


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


@pytest.mark.unit
class TestGoldFilterConfigInOperator:
    """Tests for IN operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("IC50", True),
            ("Ki", True),
            ("XYZ", False),
            (None, False),  # "None" not in values
        ],
    )
    def test_in_operator(self, val: str | None, expected: bool) -> None:
        """Test IN operator matches values in the allowed set."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="type",
                    operator=FilterOperator.IN,
                    values=frozenset(["IC50", "Ki"]),
                ),
            )
        )
        assert cfg.should_include({"type": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigNotInOperator:
    """Tests for NOT_IN operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            ("UNKNOWN", False),
            ("UNCHECKED", False),
            ("PROTEIN", True),
            ("SINGLE_PROTEIN", True),
        ],
    )
    def test_not_in_operator(self, val: str, expected: bool) -> None:
        """Test NOT_IN operator excludes values in the set."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="target_type",
                    operator=FilterOperator.NOT_IN,
                    values=frozenset(["UNKNOWN", "UNCHECKED"]),
                ),
            )
        )
        assert cfg.should_include({"target_type": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigIsNullOperator:
    """Tests for IS_NULL operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, True),
            ("", True),
            ("value", False),
            (0, False),
            (0.0, False),
            (False, False),
            ([], False),  # Empty list is not null (use IS_EMPTY)
        ],
    )
    def test_is_null_operator(self, val: object, expected: bool) -> None:
        """Test IS_NULL operator matches None or empty string."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="field", operator=FilterOperator.IS_NULL),
            )
        )
        assert cfg.should_include({"field": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigIsNotNullOperator:
    """Tests for IS_NOT_NULL operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, False),
            ("", False),
            ("value", True),
            (0, True),
            (0.0, True),
            (False, True),
            ([], True),  # Empty list is not null
        ],
    )
    def test_is_not_null_operator(self, val: object, expected: bool) -> None:
        """Test IS_NOT_NULL operator matches non-None and non-empty-string."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="field", operator=FilterOperator.IS_NOT_NULL),
            )
        )
        assert cfg.should_include({"field": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigIsEmptyOperator:
    """Tests for IS_EMPTY operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, True),
            ("", True),
            ("  ", True),  # Whitespace only
            ("\t\n", True),  # Tabs and newlines
            ([], True),
            ({}, True),
            (set(), True),
            ([1, 2], False),
            ({"a": 1}, False),
            ({1, 2}, False),
            ("text", False),
            (0, False),
            (False, False),
        ],
    )
    def test_is_empty_operator(self, val: object, expected: bool) -> None:
        """Test IS_EMPTY operator matches empty values."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="data", operator=FilterOperator.IS_EMPTY),
            )
        )
        assert cfg.should_include({"data": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigIsNotEmptyOperator:
    """Tests for IS_NOT_EMPTY operator in column filters."""

    @pytest.mark.parametrize(
        ("val", "expected"),
        [
            (None, False),
            ("", False),
            ("  ", False),  # Whitespace only
            ([], False),
            ({}, False),
            ([1, 2], True),
            ({"a": 1}, True),
            ("text", True),
            (0, True),  # 0 is not empty
            (False, True),  # False is not empty
        ],
    )
    def test_is_not_empty_operator(self, val: object, expected: bool) -> None:
        """Test IS_NOT_EMPTY operator matches non-empty values."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="smiles", operator=FilterOperator.IS_NOT_EMPTY),
            )
        )
        assert cfg.should_include({"smiles": val}) == expected


@pytest.mark.unit
class TestGoldFilterConfigMixedOperators:
    """Tests for combining multiple operators."""

    def test_multiple_column_filters_with_different_operators(self) -> None:
        """Test combining IN, NOT_IN, and NULL operators."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="type",
                    operator=FilterOperator.IN,
                    values=frozenset(["IC50", "Ki"]),
                ),
                GoldColumnFilter(
                    column="status",
                    operator=FilterOperator.NOT_IN,
                    values=frozenset(["DEPRECATED"]),
                ),
                GoldColumnFilter(
                    column="value",
                    operator=FilterOperator.IS_NOT_NULL,
                ),
            )
        )
        # All pass
        assert (
            cfg.should_include({"type": "IC50", "status": "ACTIVE", "value": 5.0})
            is True
        )
        # Fails IN
        assert (
            cfg.should_include({"type": "EC50", "status": "ACTIVE", "value": 5.0})
            is False
        )
        # Fails NOT_IN
        assert (
            cfg.should_include({"type": "IC50", "status": "DEPRECATED", "value": 5.0})
            is False
        )
        # Fails IS_NOT_NULL
        assert (
            cfg.should_include({"type": "IC50", "status": "ACTIVE", "value": None})
            is False
        )

    def test_operator_with_missing_column(self) -> None:
        """Test operator behavior when column is missing from record."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(column="missing", operator=FilterOperator.IS_NULL),
            )
        )
        # Missing column returns None from dict.get()
        assert cfg.should_include({}) is True

    def test_is_not_empty_with_missing_column(self) -> None:
        """Test IS_NOT_EMPTY fails when column is missing."""
        cfg = GoldFilterConfig(
            column_filters=(
                GoldColumnFilter(
                    column="missing", operator=FilterOperator.IS_NOT_EMPTY
                ),
            )
        )
        # Missing column returns None, which is empty
        assert cfg.should_include({}) is False
