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
"""Unit tests for InputFilterConfig and FilterColumn."""

from __future__ import annotations

import pytest

from bioetl.domain.filtering.input_config import FilterColumn, InputFilterConfig


@pytest.mark.unit
class TestFilterColumn:
    """Tests for FilterColumn dataclass."""

    def test_config_filter_column__creation__92809f78(self) -> None:
        """Test creating a FilterColumn."""
        col = FilterColumn(column_name="chembl_id", filter_field="molecule_chembl_id")
        assert col.column_name == "chembl_id"
        assert col.filter_field == "molecule_chembl_id"

    def test_config_filter_column__is_frozen__03db029d(self) -> None:
        """Test FilterColumn is immutable."""
        col = FilterColumn(column_name="id", filter_field="field")
        with pytest.raises((AttributeError, TypeError)):
            col.column_name = "other"  # type: ignore[misc]


@pytest.mark.unit
class TestInputFilterConfigDisabled:
    """Tests for InputFilterConfig when disabled."""

    def test_default_is_disabled(self) -> None:
        """Test default InputFilterConfig is disabled."""
        config = InputFilterConfig()
        assert config.enabled is False
        assert config.source_path is None
        assert config.column_name is None
        assert config.filter_field is None
        assert config.columns == ()
        assert config.batch_size == 100

    def test_disabled_config_ignores_missing_fields(self) -> None:
        """Test that disabled config doesn't require any other fields."""
        # Should not raise even without source_path etc.
        config = InputFilterConfig(enabled=False)
        assert config.enabled is False

    def test_is_not_multi_column_when_no_columns(self) -> None:
        """Test is_multi_column is False when columns is empty."""
        config = InputFilterConfig()
        assert config.is_multi_column is False

    def test_is_not_direct_filter_by_default(self) -> None:
        """Test is_direct_filter is False by default."""
        config = InputFilterConfig()
        assert config.is_direct_filter is False

    def test_is_not_direct_multi_filter_by_default(self) -> None:
        """Test is_direct_multi_filter is False by default."""
        config = InputFilterConfig()
        assert config.is_direct_multi_filter is False

    def test_get_columns_returns_empty_when_disabled(self) -> None:
        """Test get_columns returns empty tuple when no columns or column_name."""
        config = InputFilterConfig()
        assert config.get_columns() == ()


@pytest.mark.unit
class TestInputFilterConfigCsvMode:
    """Tests for InputFilterConfig in CSV mode."""

    def test_csv_single_column_mode(self) -> None:
        """Test CSV mode with single column configuration."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            column_name="chembl_id",
            filter_field="molecule_chembl_id",
        )
        assert config.enabled is True
        assert config.is_direct_filter is False

    def test_csv_mode_missing_source_path_raises(self) -> None:
        """Test that enabled CSV mode without source_path raises ValueError."""
        with pytest.raises(ValueError, match="source_path is required"):
            InputFilterConfig(
                enabled=True,
                column_name="chembl_id",
                filter_field="molecule_chembl_id",
            )

    def test_csv_mode_missing_column_config_raises(self) -> None:
        """Test that enabled CSV mode without column config raises ValueError."""
        with pytest.raises(ValueError, match="column_name/filter_field"):
            InputFilterConfig(
                enabled=True,
                source_path="/data/filter.csv",
            )

    def test_csv_multi_column_mode(self) -> None:
        """Test CSV mode with multi-column configuration."""
        columns = (
            FilterColumn("chembl_id", "molecule_chembl_id"),
            FilterColumn("target_id", "target_chembl_id"),
        )
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            columns=columns,
        )
        assert config.is_multi_column is True

    def test_csv_single_column_in_columns_list_is_not_multi(self) -> None:
        """Test is_multi_column is False with only one column in list."""
        columns = (FilterColumn("chembl_id", "molecule_chembl_id"),)
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            columns=columns,
        )
        assert config.is_multi_column is False

    def test_invalid_column_in_columns_list_raises(self) -> None:
        """Test that column with empty fields raises ValueError."""
        columns = (FilterColumn(column_name="", filter_field="some_field"),)
        with pytest.raises(ValueError, match="column_name and filter_field"):
            InputFilterConfig(
                enabled=True,
                source_path="/data/filter.csv",
                columns=columns,
            )

    def test_get_columns_single_mode(self) -> None:
        """Test get_columns returns single-column tuple in single mode."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            column_name="chembl_id",
            filter_field="molecule_chembl_id",
        )
        cols = config.get_columns()
        assert len(cols) == 1
        assert cols[0].column_name == "chembl_id"
        assert cols[0].filter_field == "molecule_chembl_id"

    def test_get_columns_multi_mode(self) -> None:
        """Test get_columns returns columns tuple in multi-column mode."""
        columns = (
            FilterColumn("chembl_id", "molecule_chembl_id"),
            FilterColumn("target_id", "target_chembl_id"),
        )
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            columns=columns,
        )
        assert config.get_columns() == columns


@pytest.mark.unit
class TestInputFilterConfigDirectIdsMode:
    """Tests for InputFilterConfig in direct IDs mode."""

    def test_direct_filter_ids_mode(self) -> None:
        """Test direct filter IDs mode."""
        config = InputFilterConfig(
            enabled=True,
            direct_filter_ids=("CHEMBL25", "CHEMBL100"),
            filter_field="molecule_chembl_id",
        )
        assert config.is_direct_filter is True
        assert config.direct_filter_ids == ("CHEMBL25", "CHEMBL100")

    def test_direct_filter_ids_missing_filter_field_raises(self) -> None:
        """Test that direct IDs mode without filter_field raises ValueError."""
        with pytest.raises(ValueError, match="filter_field is required"):
            InputFilterConfig(
                enabled=True,
                direct_filter_ids=("CHEMBL25",),
            )

    def test_direct_multi_filter_ids_mode(self) -> None:
        """Test direct multi-field filter IDs mode."""
        config = InputFilterConfig(
            enabled=True,
            direct_multi_filter_ids={
                "molecule_chembl_id": ("CHEMBL25", "CHEMBL100"),
                "target_chembl_id": ("CHEMBL240", "CHEMBL301"),
            },
        )
        assert config.is_direct_multi_filter is True

    def test_empty_direct_multi_filter_ids_raises(self) -> None:
        """Test that empty direct_multi_filter_ids raises ValueError."""
        with pytest.raises(ValueError, match="non-empty"):
            InputFilterConfig(
                enabled=True,
                direct_multi_filter_ids={},
            )


@pytest.mark.unit
class TestInputFilterConfigBatchSize:
    """Tests for InputFilterConfig batch_size validation."""

    def test_default_batch_size(self) -> None:
        """Test default batch_size is 100."""
        config = InputFilterConfig()
        assert config.batch_size == 100

    def test_custom_batch_size(self) -> None:
        """Test custom batch_size within range."""
        config = InputFilterConfig(
            enabled=True,
            source_path="/data/filter.csv",
            column_name="id",
            filter_field="field",
            batch_size=50,
        )
        assert config.batch_size == 50

    def test_batch_size_zero_raises(self) -> None:
        """Test that batch_size of 0 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be between"):
            InputFilterConfig(batch_size=0)

    def test_batch_size_too_large_raises(self) -> None:
        """Test that batch_size > 1000 raises ValueError."""
        with pytest.raises(ValueError, match="batch_size must be between"):
            InputFilterConfig(batch_size=1001)

    def test_batch_size_1_is_valid(self) -> None:
        """Test that batch_size of 1 is valid."""
        config = InputFilterConfig(batch_size=1)
        assert config.batch_size == 1

    def test_batch_size_1000_is_valid(self) -> None:
        """Test that batch_size of 1000 is valid."""
        config = InputFilterConfig(batch_size=1000)
        assert config.batch_size == 1000
