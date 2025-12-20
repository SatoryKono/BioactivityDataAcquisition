"""Unit tests for InputFilterConfig."""

import pytest

from bioetl.domain.filter_config import InputFilterConfig


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
            filter_field="molecule_chembl_id",
            batch_size=50,
        )

        assert config.enabled is True
        assert config.source_path == "/path/to/file.csv"
        assert config.column_name == "molecule_id"
        assert config.filter_field == "molecule_chembl_id"
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
        """Test that enabled=True without column_name raises ValueError."""
        with pytest.raises(ValueError, match="column_name is required"):
            InputFilterConfig(
                enabled=True,
                source_path="/path/to/file.csv",
                column_name=None,
                filter_field="field",
            )

    def test_enabled_without_filter_field_raises(self):
        """Test that enabled=True without filter_field raises ValueError."""
        with pytest.raises(ValueError, match="filter_field is required"):
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

    def test_batch_size_too_large_raises(self):
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
