# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for composition/builders.py.

Tests FilterConfigBuilder for merging YAML and CLI configurations.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.builders import FilterConfigBuilder
from bioetl.domain.filtering import InputFilterConfig


@pytest.fixture
def yaml_filter_disabled():
    """Create a mock YAML filter config that is disabled."""
    yaml_filter = MagicMock()
    yaml_filter.enabled = False
    yaml_filter.source_path = None
    yaml_filter.column_name = None
    yaml_filter.filter_field = None
    yaml_filter.batch_size = 100
    yaml_filter.columns = None
    yaml_filter.fallback_column = None
    return yaml_filter


@pytest.fixture
def yaml_filter_enabled():
    """Create a mock YAML filter config that is enabled."""
    yaml_filter = MagicMock()
    yaml_filter.enabled = True
    yaml_filter.source_path = "/yaml/path/ids.csv"
    yaml_filter.column_name = "yaml_column"
    yaml_filter.filter_field = "yaml_field"
    yaml_filter.batch_size = 50
    yaml_filter.columns = None
    yaml_filter.fallback_column = None
    return yaml_filter


@pytest.fixture
def yaml_filter_multi_column():
    """Create a mock YAML filter config with multi-column support."""
    yaml_filter = MagicMock()
    yaml_filter.enabled = True
    yaml_filter.source_path = "/yaml/path/multi.csv"
    yaml_filter.column_name = None
    yaml_filter.filter_field = None
    yaml_filter.batch_size = 100

    # Mock columns
    col1 = MagicMock()
    col1.column_name = "target_id"
    col1.filter_field = "target_id"
    col2 = MagicMock()
    col2.column_name = "assay_id"
    col2.filter_field = "assay_id"
    yaml_filter.columns = [col1, col2]

    yaml_filter.fallback_column = None
    return yaml_filter


@pytest.fixture
def yaml_filter_with_fallback():
    """Create a mock YAML filter config with fallback column."""
    yaml_filter = MagicMock()
    yaml_filter.enabled = True
    yaml_filter.source_path = "/yaml/path/fallback.csv"
    yaml_filter.column_name = "doi"
    yaml_filter.filter_field = "doi"
    yaml_filter.batch_size = 100
    yaml_filter.columns = None
    yaml_filter.fallback_column = "title"
    return yaml_filter


@pytest.mark.unit
class TestFilterConfigBuilderIsFilterEnabled:
    """Tests for FilterConfigBuilder._is_filter_enabled method."""

    def test_filter_disabled_when_yaml_disabled_and_no_cli(self, yaml_filter_disabled):
        """Test filter is disabled when YAML disabled and no CLI csv."""
        result = FilterConfigBuilder._is_filter_enabled(
            yaml_filter_disabled, cli_csv=None, test_mode=False
        )
        assert result is False

    def test_filter_enabled_when_cli_csv_provided(self, yaml_filter_disabled):
        """Test filter is enabled when CLI csv is provided."""
        result = FilterConfigBuilder._is_filter_enabled(
            yaml_filter_disabled, cli_csv="/cli/path.csv", test_mode=False
        )
        assert result is True

    def test_filter_enabled_when_yaml_enabled(self, yaml_filter_enabled):
        """Test filter is enabled when YAML has enabled=True."""
        result = FilterConfigBuilder._is_filter_enabled(
            yaml_filter_enabled, cli_csv=None, test_mode=False
        )
        assert result is True

    def test_filter_disabled_in_test_mode_without_cli(self, yaml_filter_enabled):
        """Test YAML-based filters are disabled in test mode without CLI csv."""
        result = FilterConfigBuilder._is_filter_enabled(
            yaml_filter_enabled, cli_csv=None, test_mode=True
        )
        assert result is False

    def test_filter_enabled_in_test_mode_with_cli(self, yaml_filter_disabled):
        """Test filter is enabled in test mode when CLI csv is provided."""
        result = FilterConfigBuilder._is_filter_enabled(
            yaml_filter_disabled, cli_csv="/cli/path.csv", test_mode=True
        )
        assert result is True


@pytest.mark.unit
class TestFilterConfigBuilderBuildMultiColumn:
    """Tests for FilterConfigBuilder._build_multi_column_config method."""

    def test_build_multi_column_config_creates_config(self, yaml_filter_multi_column):
        """Test _build_multi_column_config creates InputFilterConfig."""
        result = FilterConfigBuilder._build_multi_column_config(
            yaml_filter_multi_column, "/effective/path.csv"
        )

        assert isinstance(result, InputFilterConfig)
        assert result.enabled is True
        assert result.source_path == "/effective/path.csv"

    def test_build_multi_column_config_converts_columns(self, yaml_filter_multi_column):
        """Test _build_multi_column_config converts YAML columns to domain columns."""
        result = FilterConfigBuilder._build_multi_column_config(
            yaml_filter_multi_column, "/effective/path.csv"
        )

        assert result.columns is not None
        assert len(result.columns) == 2

        # Check first column
        assert result.columns[0].column_name == "target_id"
        assert result.columns[0].filter_field == "target_id"

        # Check second column
        assert result.columns[1].column_name == "assay_id"
        assert result.columns[1].filter_field == "assay_id"

    def test_build_multi_column_config_preserves_batch_size(
        self, yaml_filter_multi_column
    ):
        """Test _build_multi_column_config preserves batch_size from YAML."""
        yaml_filter_multi_column.batch_size = 200

        result = FilterConfigBuilder._build_multi_column_config(
            yaml_filter_multi_column, "/effective/path.csv"
        )

        assert result.batch_size == 200


@pytest.mark.unit
class TestFilterConfigBuilderBuildSingleColumn:
    """Tests for FilterConfigBuilder._build_single_column_config method."""

    def test_build_single_column_config_creates_config(self, yaml_filter_enabled):
        """Test _build_single_column_config creates InputFilterConfig."""
        result = FilterConfigBuilder._build_single_column_config(
            yaml_filter_enabled, "/effective/path.csv", None, None, None
        )

        assert isinstance(result, InputFilterConfig)
        assert result.enabled is True
        assert result.source_path == "/effective/path.csv"

    def test_build_single_column_uses_yaml_defaults(self, yaml_filter_enabled):
        """Test _build_single_column_config uses YAML values when no CLI override."""
        result = FilterConfigBuilder._build_single_column_config(
            yaml_filter_enabled, "/effective/path.csv", None, None, None
        )

        assert result.column_name == "yaml_column"
        assert result.filter_field == "yaml_field"

    def test_build_single_column_cli_overrides_yaml(self, yaml_filter_enabled):
        """Test _build_single_column_config CLI values override YAML."""
        result = FilterConfigBuilder._build_single_column_config(
            yaml_filter_enabled,
            "/effective/path.csv",
            cli_column="cli_column",
            cli_field="cli_field",
            cli_fallback_column=None,
        )

        assert result.column_name == "cli_column"
        assert result.filter_field == "cli_field"

    def test_build_single_column_preserves_fallback(self, yaml_filter_with_fallback):
        """Test _build_single_column_config preserves fallback_column from YAML."""
        result = FilterConfigBuilder._build_single_column_config(
            yaml_filter_with_fallback, "/effective/path.csv", None, None, None
        )

        assert result.fallback_column == "title"


@pytest.mark.unit
class TestFilterConfigBuilderBuild:
    """Tests for FilterConfigBuilder.build method."""

    def test_build_returns_none_when_disabled(self, yaml_filter_disabled):
        """Test build returns None when filter is disabled."""
        result = FilterConfigBuilder.build(yaml_filter_disabled)

        assert result is None

    def test_build_returns_none_when_no_csv_path(self, yaml_filter_disabled):
        """Test build returns None when no CSV path available."""
        yaml_filter_disabled.enabled = True
        yaml_filter_disabled.source_path = None

        result = FilterConfigBuilder.build(yaml_filter_disabled)

        assert result is None

    def test_build_uses_cli_csv_when_provided(self, yaml_filter_disabled):
        """Test build uses CLI csv path when provided."""
        result = FilterConfigBuilder.build(
            yaml_filter_disabled,
            cli_csv="/cli/path.csv",
            cli_column="cli_col",
            cli_field="cli_field",
        )

        assert result is not None
        assert result.source_path == "/cli/path.csv"
        assert result.column_name == "cli_col"
        assert result.filter_field == "cli_field"

    def test_build_uses_yaml_path_when_enabled(self, yaml_filter_enabled):
        """Test build uses YAML path when YAML enabled and no CLI."""
        result = FilterConfigBuilder.build(yaml_filter_enabled)

        assert result is not None
        assert result.source_path == "/yaml/path/ids.csv"
        assert result.column_name == "yaml_column"
        assert result.filter_field == "yaml_field"

    def test_build_multi_column_mode_without_cli(self, yaml_filter_multi_column):
        """Test build uses multi-column mode from YAML when no CLI csv."""
        result = FilterConfigBuilder.build(yaml_filter_multi_column)

        assert result is not None
        assert result.columns is not None
        assert len(result.columns) == 2

    def test_build_multi_column_mode_ignored_with_cli(self, yaml_filter_multi_column):
        """Test build falls back to single-column mode when CLI csv provided."""
        result = FilterConfigBuilder.build(
            yaml_filter_multi_column,
            cli_csv="/cli/path.csv",
            cli_column="cli_col",
            cli_field="cli_field",
        )

        assert result is not None
        # Should be single-column mode since CLI csv was provided
        assert result.column_name == "cli_col"
        assert result.filter_field == "cli_field"

    def test_build_in_test_mode_ignores_yaml(self, yaml_filter_enabled):
        """Test build ignores YAML-based filters in test mode."""
        result = FilterConfigBuilder.build(yaml_filter_enabled, test_mode=True)

        assert result is None

    def test_build_in_test_mode_uses_cli(self, yaml_filter_disabled):
        """Test build uses CLI filters in test mode."""
        result = FilterConfigBuilder.build(
            yaml_filter_disabled,
            cli_csv="/cli/test.csv",
            cli_column="test_col",
            cli_field="test_field",
            test_mode=True,
        )

        assert result is not None
        assert result.source_path == "/cli/test.csv"

    def test_build_with_fallback_column(self, yaml_filter_with_fallback):
        """Test build preserves fallback_column in single-column mode."""
        result = FilterConfigBuilder.build(yaml_filter_with_fallback)

        assert result is not None
        assert result.fallback_column == "title"
