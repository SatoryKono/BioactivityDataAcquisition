"""Tests for composition layer builders.

Tests FilterConfigBuilder which merges YAML config with CLI overrides.
"""

from unittest.mock import MagicMock

import pytest

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.domain.filter_config import InputFilterConfig


class TestFilterConfigBuilder:
    """Tests for FilterConfigBuilder."""

    @pytest.fixture
    def yaml_filter_enabled(self) -> MagicMock:
        """Create a mock YAML filter config with filtering enabled."""
        mock = MagicMock()
        mock.enabled = True
        mock.source_path = "/yaml/path.csv"
        mock.column_name = "yaml_col"
        mock.filter_field = "yaml_field"
        mock.batch_size = 100
        return mock

    @pytest.fixture
    def yaml_filter_disabled(self) -> MagicMock:
        """Create a mock YAML filter config with filtering disabled."""
        mock = MagicMock()
        mock.enabled = False
        mock.source_path = None
        mock.column_name = "default_col"
        mock.filter_field = "default_field"
        mock.batch_size = 100
        return mock

    def test_cli_overrides_yaml_values(self, yaml_filter_enabled: MagicMock) -> None:
        """CLI arguments should override YAML values."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv="/cli/path.csv",
            cli_column="cli_col",
            cli_field="cli_field",
        )

        assert result is not None
        assert result.source_path == "/cli/path.csv"
        assert result.column_name == "cli_col"
        assert result.filter_field == "cli_field"
        assert result.enabled is True

    def test_yaml_defaults_when_cli_none(self, yaml_filter_enabled: MagicMock) -> None:
        """YAML values should be used when CLI args are None."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv=None,
            cli_column=None,
            cli_field=None,
        )

        assert result is not None
        assert result.source_path == "/yaml/path.csv"
        assert result.column_name == "yaml_col"
        assert result.filter_field == "yaml_field"
        assert result.batch_size == 100

    def test_returns_none_when_disabled_and_no_cli(
        self, yaml_filter_disabled: MagicMock
    ) -> None:
        """Should return None when filtering is disabled and no CLI csv provided."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_disabled,
            cli_csv=None,
            cli_column=None,
            cli_field=None,
        )

        assert result is None

    def test_cli_csv_enables_filter_even_when_yaml_disabled(
        self, yaml_filter_disabled: MagicMock
    ) -> None:
        """Providing --input-csv should enable filtering even if YAML disabled."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_disabled,
            cli_csv="/cli/path.csv",
            cli_column="cli_col",
            cli_field="cli_field",
        )

        assert result is not None
        assert result.enabled is True
        assert result.source_path == "/cli/path.csv"

    def test_partial_cli_overrides(self, yaml_filter_enabled: MagicMock) -> None:
        """CLI should only override provided values, use YAML for rest."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv="/cli/path.csv",  # Override
            cli_column=None,  # Use YAML
            cli_field=None,  # Use YAML
        )

        assert result is not None
        assert result.source_path == "/cli/path.csv"
        assert result.column_name == "yaml_col"  # From YAML
        assert result.filter_field == "yaml_field"  # From YAML

    def test_batch_size_from_yaml(self, yaml_filter_enabled: MagicMock) -> None:
        """Batch size should always come from YAML config."""
        yaml_filter_enabled.batch_size = 50

        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv="/cli/path.csv",
            cli_column=None,
            cli_field=None,
        )

        assert result is not None
        assert result.batch_size == 50

    def test_returns_frozen_dataclass(self, yaml_filter_enabled: MagicMock) -> None:
        """Result should be an immutable InputFilterConfig."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv=None,
            cli_column=None,
            cli_field=None,
        )

        assert result is not None
        assert isinstance(result, InputFilterConfig)

        # Verify immutability
        with pytest.raises(AttributeError):
            result.source_path = "/new/path.csv"  # type: ignore[misc]

    def test_logger_called_when_filter_enabled(
        self, yaml_filter_enabled: MagicMock
    ) -> None:
        """Logger should be called with filter config details."""
        mock_logger = MagicMock()

        FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv="/cli/path.csv",
            cli_column="col",
            cli_field="field",
            logger=mock_logger,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[0][0] == "input_filter_enabled"
        assert call_args[1]["csv_path"] == "/cli/path.csv"
        assert call_args[1]["source"] == "cli"

    def test_logger_reports_config_source_when_using_yaml(
        self, yaml_filter_enabled: MagicMock
    ) -> None:
        """Logger should report 'config' as source when using YAML values."""
        mock_logger = MagicMock()

        FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv=None,  # Not from CLI
            cli_column=None,
            cli_field=None,
            logger=mock_logger,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert call_args[1]["source"] == "config"

    def test_logger_not_called_when_filter_disabled(
        self, yaml_filter_disabled: MagicMock
    ) -> None:
        """Logger should not be called when filter is disabled."""
        mock_logger = MagicMock()

        FilterConfigBuilder.build(
            yaml_filter=yaml_filter_disabled,
            cli_csv=None,
            cli_column=None,
            cli_field=None,
            logger=mock_logger,
        )

        mock_logger.info.assert_not_called()

    def test_no_logger_no_error(self, yaml_filter_enabled: MagicMock) -> None:
        """Should work without logger (logger=None)."""
        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter_enabled,
            cli_csv="/path.csv",
            cli_column="col",
            cli_field="field",
            logger=None,
        )

        assert result is not None

    def test_enabled_but_no_source_path_returns_none(self) -> None:
        """Should return None if enabled but no source path available."""
        yaml_filter = MagicMock()
        yaml_filter.enabled = True
        yaml_filter.source_path = None  # No path in YAML
        yaml_filter.column_name = "col"
        yaml_filter.filter_field = "field"
        yaml_filter.batch_size = 100

        result = FilterConfigBuilder.build(
            yaml_filter=yaml_filter,
            cli_csv=None,  # No path from CLI either
            cli_column=None,
            cli_field=None,
        )

        assert result is None
