"""Unit tests for filter configuration classes."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering import (
    GoldColumnFilter,
    GoldFilterConfig,
    InputFilterConfig,
)


@pytest.mark.unit
class TestInputFilterConfigCreation:
    """Tests for InputFilterConfig creation."""

    def test_create_disabled_config(self):
        """Test creating a disabled filter config."""
        config = InputFilterConfig(enabled=False)

        assert config.enabled is False
        assert config.source_path is None
        assert config.column_name is None
        assert config.filter_field is None
        assert config.batch_size == 100

    def test_create_enabled_config_with_all_fields(self):
        """Test creating an enabled filter config with all required fields."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/path/to/file.csv",
            column_name="molecule_id",
            filter_field="molecule_id",
            batch_size=50,
        )

        assert config.enabled is True
        assert config.source_path == "/path/to/file.csv"
        assert config.column_name == "molecule_id"
        assert config.filter_field == "molecule_id"
        assert config.batch_size == 50

    def test_config_is_frozen(self):
        """Test that config is immutable."""
        config = InputFilterConfig(enabled=False)

        with pytest.raises(AttributeError):
            config.enabled = True


@pytest.mark.unit
class TestInputFilterConfigValidation:
    """Tests for InputFilterConfig validation."""

    def test_enabled_without_source_path_raises(self):
        """Test that enabled=True without source_path raises ValueError."""
        with pytest.raises(ValueError, match="source_path is required"):
            InputFilterConfig(
                enabled=True,
                source_path=None,
                column_name="id",
                filter_field="field",
            )

    def test_enabled_without_column_name_raises(self):
        """Test that enabled=True without column_name or columns raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Either columns list or column_name/filter_field is required "
            "when filter is enabled",
        ):
            InputFilterConfig(
                enabled=True,
                source_path="/path/to/file.csv",
                column_name=None,
                filter_field="field",
            )

    def test_enabled_without_filter_field_raises(self):
        """Test that enabled=True without filter_field or columns raises ValueError."""
        with pytest.raises(
            ValueError,
            match="Either columns list or column_name/filter_field is required "
            "when filter is enabled",
        ):
            InputFilterConfig(
                enabled=True,
                source_path="/path/to/file.csv",
                column_name="id",
                filter_field=None,
            )

    def test_batch_size_too_small_raises(self):
        """Test that batch_size < 1 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be between 1 and 1000"):
            InputFilterConfig(
                enabled=False,
                batch_size=0,
            )

    def test_batch_size_too_large_raises__test_input_filter_config_validation_unit_domain_test_filter_config_102(self):
        """Test that batch_size > 1000 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be between 1 and 1000"):
            InputFilterConfig(
                enabled=False,
                batch_size=1001,
            )

    def test_batch_size_at_min_boundary(self):
        """Test batch_size at minimum boundary (1) is valid."""
        config = InputFilterConfig(enabled=False, batch_size=1)
        assert config.batch_size == 1

    def test_batch_size_at_max_boundary(self):
        """Test batch_size at maximum boundary (1000) is valid."""
        config = InputFilterConfig(enabled=False, batch_size=1000)
        assert config.batch_size == 1000

    def test_disabled_config_allows_missing_fields(self):
        """Test that disabled config allows missing optional fields."""
        config = InputFilterConfig(
            enabled=False,
            source_path=None,
            column_name=None,
            filter_field=None,
        )

        assert config.enabled is False


# =============================================================================
# GoldColumnFilter Tests
# =============================================================================


@pytest.mark.unit
class TestGoldColumnFilter:
    """Tests for GoldColumnFilter."""

    def test_create_valid_filter(self):
        """Test creating a valid column filter."""
        filter_ = GoldColumnFilter(
            column="standard_type",
            values=frozenset(["IC50", "Ki"]),
        )

        assert filter_.column == "standard_type"
        assert filter_.values == frozenset(["IC50", "Ki"])

    def test_empty_column_raises(self):
        """Test that empty column name raises ValueError."""
        with pytest.raises(ValueError, match="column name cannot be empty"):
            GoldColumnFilter(column="", values=frozenset(["IC50"]))

    def test_empty_values_raises(self):
        """Test that empty values raises ValueError."""
        with pytest.raises(ValueError, match=r"values required for operator"):
            GoldColumnFilter(column="standard_type", values=frozenset())

    def test_filter_is_frozen(self):
        """Test that filter is immutable."""
        filter_ = GoldColumnFilter(
            column="standard_type",
            values=frozenset(["IC50"]),
        )

        with pytest.raises(AttributeError):
            filter_.column = "new_column"


# =============================================================================
# GoldFilterConfig Tests
# =============================================================================


@pytest.mark.unit
class TestGoldFilterConfig:
    """Tests for GoldFilterConfig."""

    def test_empty_config(self):
        """Test creating an empty filter config."""
        config = GoldFilterConfig()

        assert config.column_filters == ()
        assert config.required_fields == ()
        assert config.exclude_if_present == ()
        assert config.is_empty() is True

    def test_config_with_column_filters(self):
        """Test creating config with column filters."""
        filter1 = GoldColumnFilter(column="col1", values=frozenset(["a", "b"]))
        filter2 = GoldColumnFilter(column="col2", values=frozenset(["x"]))

        config = GoldFilterConfig(column_filters=(filter1, filter2))

        assert len(config.column_filters) == 2
        assert config.is_empty() is False

    def test_config_with_required_fields(self):
        """Test creating config with required fields."""
        config = GoldFilterConfig(required_fields=("field1", "field2"))

        assert config.required_fields == ("field1", "field2")
        assert config.is_empty() is False

    def test_config_with_exclude_if_present(self):
        """Test creating config with exclude_if_present."""
        config = GoldFilterConfig(exclude_if_present=("bad_field",))

        assert config.exclude_if_present == ("bad_field",)
        assert config.is_empty() is False


@pytest.mark.unit
class TestGoldFilterConfigShouldInclude:
    """Tests for GoldFilterConfig.should_include method."""

    def test_empty_config_includes_all(self):
        """Test that empty config includes all records."""
        config = GoldFilterConfig()

        assert config.should_include({}) is True
        assert config.should_include({"any": "field"}) is True

    def test_required_fields_pass(self):
        """Test required fields filter - passes when fields have values."""
        config = GoldFilterConfig(required_fields=("field1", "field2"))

        record = {"field1": "value1", "field2": "value2"}
        assert config.should_include(record) is True

    def test_required_fields_fail_on_none(self):
        """Test required fields filter - fails on None value."""
        config = GoldFilterConfig(required_fields=("field1",))

        assert config.should_include({"field1": None}) is False

    def test_required_fields_fail_on_empty_string(self):
        """Test required fields filter - fails on empty string."""
        config = GoldFilterConfig(required_fields=("field1",))

        assert config.should_include({"field1": ""}) is False

    def test_required_fields_fail_on_missing(self):
        """Test required fields filter - fails on missing field."""
        config = GoldFilterConfig(required_fields=("field1",))

        assert config.should_include({}) is False

    def test_exclude_if_present_pass(self):
        """Test exclude_if_present - passes when field is absent."""
        config = GoldFilterConfig(exclude_if_present=("bad_field",))

        assert config.should_include({}) is True
        assert config.should_include({"other": "value"}) is True

    def test_exclude_if_present_pass_on_none(self):
        """Test exclude_if_present - passes when field is None."""
        config = GoldFilterConfig(exclude_if_present=("bad_field",))

        assert config.should_include({"bad_field": None}) is True

    def test_exclude_if_present_pass_on_empty_string(self):
        """Test exclude_if_present - passes when field is empty string."""
        config = GoldFilterConfig(exclude_if_present=("bad_field",))

        assert config.should_include({"bad_field": ""}) is True

    def test_exclude_if_present_fail(self):
        """Test exclude_if_present - fails when field has value."""
        config = GoldFilterConfig(exclude_if_present=("bad_field",))

        assert config.should_include({"bad_field": "has value"}) is False

    def test_column_filters_pass(self):
        """Test column filters - passes when value is in allowed set."""
        filter_ = GoldColumnFilter(column="type", values=frozenset(["IC50", "Ki"]))
        config = GoldFilterConfig(column_filters=(filter_,))

        assert config.should_include({"type": "IC50"}) is True
        assert config.should_include({"type": "Ki"}) is True

    def test_column_filters_fail(self):
        """Test column filters - fails when value is not in allowed set."""
        filter_ = GoldColumnFilter(column="type", values=frozenset(["IC50", "Ki"]))
        config = GoldFilterConfig(column_filters=(filter_,))

        assert config.should_include({"type": "EC50"}) is False
        assert config.should_include({"type": None}) is False
        assert config.should_include({}) is False

    def test_column_filters_convert_to_string(self):
        """Test column filters convert values to string for comparison."""
        filter_ = GoldColumnFilter(column="score", values=frozenset(["8", "9"]))
        config = GoldFilterConfig(column_filters=(filter_,))

        # Numeric value should be converted to string
        assert config.should_include({"score": 8}) is True
        assert config.should_include({"score": 9}) is True
        assert config.should_include({"score": 7}) is False

    def test_column_filters_accept_typed_scalars_without_string_literals(self):
        """Typed filter literals should match typed normalized record values."""
        filter_ = GoldColumnFilter(column="potential_duplicate", values=frozenset([0]))
        config = GoldFilterConfig(column_filters=(filter_,))

        assert config.should_include({"potential_duplicate": 0}) is True
        assert config.should_include({"potential_duplicate": 1}) is False

    def test_all_filters_combined(self):
        """Test combination of all filter types."""
        filter_ = GoldColumnFilter(column="type", values=frozenset(["IC50"]))
        config = GoldFilterConfig(
            column_filters=(filter_,),
            required_fields=("value",),
            exclude_if_present=("invalid",),
        )

        # Passes all filters
        assert (
            config.should_include(
                {
                    "type": "IC50",
                    "value": 100,
                }
            )
            is True
        )

        # Fails column filter
        assert (
            config.should_include(
                {
                    "type": "Ki",
                    "value": 100,
                }
            )
            is False
        )

        # Fails required field
        assert (
            config.should_include(
                {
                    "type": "IC50",
                    "value": None,
                }
            )
            is False
        )

        # Fails exclude_if_present
        assert (
            config.should_include(
                {
                    "type": "IC50",
                    "value": 100,
                    "invalid": "has value",
                }
            )
            is False
        )
