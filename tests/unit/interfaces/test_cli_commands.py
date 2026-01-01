"""Unit tests for CLI commands (cleanup, config, lock).

Tests for CLI commands with mocked services, covering:
- cleanup.py: bronze_cleanup_command
- config.py: show_command, validate_command, show_settings_command, list_pipelines_command
- lock.py: release_command, check_command

Uses Click's CliRunner for command testing without real bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


# =============================================================================
# cleanup.py Tests - bronze_cleanup_command
# =============================================================================


@dataclass
class MockCleanupResult:
    """Mock CleanupResult for testing."""

    files_removed: int
    bytes_freed: int
    directories_removed: int


@pytest.fixture
def mock_bronze_cleanup_service():
    """Create a mock BronzeCleanupService."""
    service = MagicMock()
    service.cleanup = AsyncMock(
        return_value=MockCleanupResult(
            files_removed=10, bytes_freed=1024 * 1024, directories_removed=2
        )
    )
    return service


@pytest.mark.unit
class TestBronzeCleanupCommand:
    """Tests for bronze-cleanup command."""

    def test_bronze_cleanup_help(self, cli_runner):
        """Test bronze-cleanup --help shows correct options."""
        result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup", "--help"])

        assert result.exit_code == 0
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output

    def test_bronze_cleanup_success(self, cli_runner, mock_bronze_cleanup_service):
        """Test successful bronze cleanup operation."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup"])

        assert result.exit_code == 0
        assert "10 files" in result.output
        assert "2 empty directories" in result.output
        mock_bronze_cleanup_service.cleanup.assert_called_once_with(
            retention_days=90, dry_run=False
        )

    def test_bronze_cleanup_with_custom_retention(
        self, cli_runner, mock_bronze_cleanup_service
    ):
        """Test bronze cleanup with custom retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "bronze-cleanup", "-r", "30"]
            )

        assert result.exit_code == 0
        mock_bronze_cleanup_service.cleanup.assert_called_once_with(
            retention_days=30, dry_run=False
        )

    def test_bronze_cleanup_dry_run(self, cli_runner, mock_bronze_cleanup_service):
        """Test bronze cleanup dry-run mode."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "bronze-cleanup", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would remove" in result.output
        mock_bronze_cleanup_service.cleanup.assert_called_once_with(
            retention_days=90, dry_run=True
        )

    def test_bronze_cleanup_formats_bytes(self, cli_runner):
        """Test bronze cleanup formats bytes correctly."""
        mock_service = MagicMock()
        mock_service.cleanup = AsyncMock(
            return_value=MockCleanupResult(
                files_removed=5, bytes_freed=1024 * 1024 * 100, directories_removed=1
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup"])

        assert result.exit_code == 0
        # 100 MB should be formatted
        assert "MB" in result.output or "100" in result.output


# =============================================================================
# config.py Tests - show_command
# =============================================================================


@dataclass
class MockPipelineConfig:
    """Mock PipelineConfig for testing."""

    provider: str = "chembl"
    entity_type: str = "activity"
    silver_table: str = "chembl_activity"
    gold_table: str | None = "chembl_activity_gold"

    def model_dump(self) -> dict:
        """Mock Pydantic model_dump method."""
        return {
            "provider": self.provider,
            "entity_type": self.entity_type,
            "silver_table": self.silver_table,
            "gold_table": self.gold_table,
        }


@pytest.mark.unit
class TestConfigShowCommand:
    """Tests for config show command."""

    def test_config_show_help(self, cli_runner):
        """Test config show --help shows correct options."""
        result = cli_runner.invoke(cli, ["config", "show", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--format" in result.output

    def test_config_show_yaml_format(self, cli_runner):
        """Test config show with YAML format (default)."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            return_value=MockPipelineConfig(),
        ):
            result = cli_runner.invoke(cli, ["config", "show", "chembl_activity"])

        assert result.exit_code == 0
        assert "provider: chembl" in result.output
        assert "entity_type: activity" in result.output

    def test_config_show_json_format(self, cli_runner):
        """Test config show with JSON format."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            return_value=MockPipelineConfig(),
        ):
            result = cli_runner.invoke(
                cli, ["config", "show", "chembl_activity", "--format", "json"]
            )

        assert result.exit_code == 0
        assert '"provider": "chembl"' in result.output
        assert '"entity_type": "activity"' in result.output

    def test_config_show_file_not_found(self, cli_runner):
        """Test config show handles missing config file."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            side_effect=FileNotFoundError("Config not found"),
        ):
            result = cli_runner.invoke(cli, ["config", "show", "nonexistent"])

        assert "Config file not found" in result.output or "not found" in result.output

    def test_config_show_validation_error(self, cli_runner):
        """Test config show handles validation errors."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            side_effect=ValueError("Invalid configuration"),
        ):
            result = cli_runner.invoke(cli, ["config", "show", "invalid"])

        assert "error" in result.output.lower()


# =============================================================================
# config.py Tests - validate_command
# =============================================================================


@pytest.mark.unit
class TestConfigValidateCommand:
    """Tests for config validate command."""

    def test_config_validate_help(self, cli_runner):
        """Test config validate --help shows correct options."""
        result = cli_runner.invoke(cli, ["config", "validate", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output

    def test_config_validate_success(self, cli_runner):
        """Test successful config validation."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            return_value=MockPipelineConfig(),
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "Configuration valid" in result.output
        assert "Provider: chembl" in result.output
        assert "Entity type: activity" in result.output
        assert "Silver table: chembl_activity" in result.output
        assert "Gold table: chembl_activity_gold" in result.output

    def test_config_validate_without_gold(self, cli_runner):
        """Test config validation without gold table."""
        config = MockPipelineConfig(gold_table=None)
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            return_value=config,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "Configuration valid" in result.output
        # Gold table line should not appear if None
        assert "Gold table:" not in result.output

    def test_config_validate_file_not_found(self, cli_runner):
        """Test config validate handles missing config file."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            side_effect=FileNotFoundError("Config not found"),
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "nonexistent"])

        assert "Config file not found" in result.output or "not found" in result.output

    def test_config_validate_invalid_config(self, cli_runner):
        """Test config validate handles invalid configuration."""
        with patch(
            "bioetl.interfaces.cli.commands.config.load_pipeline_config",
            side_effect=ValueError("Missing required field"),
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "invalid"])

        assert "invalid" in result.output.lower() or "error" in result.output.lower()


# =============================================================================
# config.py Tests - show_settings_command
# =============================================================================


@pytest.mark.unit
class TestConfigShowSettingsCommand:
    """Tests for config show-settings command."""

    def test_show_settings_help(self, cli_runner):
        """Test show-settings --help shows correct options."""
        result = cli_runner.invoke(cli, ["config", "show-settings", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output

    def test_show_settings_yaml_format(self, cli_runner):
        """Test show-settings with YAML format (default)."""
        mock_settings = MagicMock()
        mock_settings.model_dump.return_value = {
            "data_dir": "/data",
            "log_level": "INFO",
            "pubmed_api_key": None,
        }

        with patch(
            "bioetl.interfaces.cli.commands.config.get_settings",
            return_value=mock_settings,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "data_dir" in result.output
        assert "log_level" in result.output

    def test_show_settings_json_format(self, cli_runner):
        """Test show-settings with JSON format."""
        mock_settings = MagicMock()
        mock_settings.model_dump.return_value = {
            "data_dir": "/data",
            "log_level": "INFO",
            "pubmed_api_key": None,
        }

        with patch(
            "bioetl.interfaces.cli.commands.config.get_settings",
            return_value=mock_settings,
        ):
            result = cli_runner.invoke(
                cli, ["config", "show-settings", "--format", "json"]
            )

        assert result.exit_code == 0
        assert '"data_dir"' in result.output
        assert '"log_level"' in result.output

    def test_show_settings_masks_api_key(self, cli_runner):
        """Test show-settings masks sensitive API keys."""
        mock_settings = MagicMock()
        mock_settings.model_dump.return_value = {
            "data_dir": "/data",
            "log_level": "INFO",
            "pubmed_api_key": "secret_api_key_12345",
        }

        with patch(
            "bioetl.interfaces.cli.commands.config.get_settings",
            return_value=mock_settings,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "secret_api_key_12345" not in result.output
        assert "MASKED" in result.output


# =============================================================================
# config.py Tests - list_pipelines_command
# =============================================================================


@pytest.mark.unit
class TestConfigListPipelinesCommand:
    """Tests for config list-pipelines command."""

    def test_list_pipelines_help(self, cli_runner):
        """Test list-pipelines --help shows help text."""
        result = cli_runner.invoke(cli, ["config", "list-pipelines", "--help"])

        assert result.exit_code == 0
        assert "List all registered pipelines" in result.output

    def test_list_pipelines_success(self, cli_runner):
        """Test successful pipeline listing."""
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_molecule",
            "pubchem_compound",
        ]

        with (
            patch(
                "bioetl.composition.factories.pipeline_factories.register_all_pipelines",
            ),
            patch(
                "bioetl.interfaces.cli.commands.config.get_default_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "Available pipelines:" in result.output
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output
        assert "pubchem_compound" in result.output

    def test_list_pipelines_empty(self, cli_runner):
        """Test list-pipelines with no registered pipelines."""
        mock_registry = MagicMock()
        mock_registry.list_pipelines.return_value = []

        with (
            patch(
                "bioetl.composition.factories.pipeline_factories.register_all_pipelines",
            ),
            patch(
                "bioetl.interfaces.cli.commands.config.get_default_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "No pipelines registered" in result.output

    def test_list_pipelines_sorted(self, cli_runner):
        """Test list-pipelines returns sorted list."""
        mock_registry = MagicMock()
        # Return unsorted list
        mock_registry.list_pipelines.return_value = [
            "z_pipeline",
            "a_pipeline",
            "m_pipeline",
        ]

        with (
            patch(
                "bioetl.composition.factories.pipeline_factories.register_all_pipelines",
            ),
            patch(
                "bioetl.interfaces.cli.commands.config.get_default_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        # Check that pipelines appear in sorted order
        output = result.output
        a_pos = output.find("a_pipeline")
        m_pos = output.find("m_pipeline")
        z_pos = output.find("z_pipeline")
        assert a_pos < m_pos < z_pos, "Pipelines should be sorted alphabetically"


# =============================================================================
# lock.py Tests - release_command
# =============================================================================


@pytest.fixture
def mock_lock_service():
    """Create a mock LockService."""
    service = MagicMock()
    service.release_lock = AsyncMock(return_value=True)
    service.check_lock = AsyncMock(return_value=True)
    return service


@pytest.mark.unit
class TestLockReleaseCommand:
    """Tests for lock release command."""

    def test_lock_release_help(self, cli_runner):
        """Test lock release --help shows correct options."""
        result = cli_runner.invoke(cli, ["lock", "release", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-id" in result.output
        assert "--exclusive" in result.output

    def test_lock_release_success(self, cli_runner, mock_lock_service):
        """Test successful lock release."""
        run_id = str(uuid4())

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    run_id,
                ],
            )

        assert result.exit_code == 0
        assert "Lock released" in result.output
        mock_lock_service.release_lock.assert_called_once()

    def test_lock_release_not_held(self, cli_runner, mock_lock_service):
        """Test lock release when lock is not held."""
        mock_lock_service.release_lock.return_value = False
        run_id = str(uuid4())

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    run_id,
                ],
            )

        assert result.exit_code == 0
        assert "Lock not released" in result.output or "not held" in result.output

    def test_lock_release_with_exclusive(self, cli_runner, mock_lock_service):
        """Test lock release with exclusive flag."""
        run_id = str(uuid4())

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    run_id,
                    "--exclusive",
                ],
            )

        assert result.exit_code == 0
        # Verify exclusive=True was passed
        call_args = mock_lock_service.release_lock.call_args
        assert call_args[1]["exclusive"] is True

    def test_lock_release_invalid_uuid(self, cli_runner):
        """Test lock release with invalid UUID."""
        result = cli_runner.invoke(
            cli,
            [
                "lock",
                "release",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                "not-a-valid-uuid",
            ],
        )

        assert "Invalid run-id" in result.output or "valid UUID" in result.output


# =============================================================================
# lock.py Tests - check_command
# =============================================================================


@pytest.mark.unit
class TestLockCheckCommand:
    """Tests for lock check command."""

    def test_lock_check_help(self, cli_runner):
        """Test lock check --help shows correct options."""
        result = cli_runner.invoke(cli, ["lock", "check", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-id" in result.output

    def test_lock_check_held(self, cli_runner, mock_lock_service):
        """Test lock check when lock is held."""
        run_id = str(uuid4())

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["lock", "check", "--pipeline", "chembl_activity", "--run-id", run_id],
            )

        assert result.exit_code == 0
        assert "IS held" in result.output
        mock_lock_service.check_lock.assert_called_once()

    def test_lock_check_not_held(self, cli_runner, mock_lock_service):
        """Test lock check when lock is not held."""
        mock_lock_service.check_lock.return_value = False
        run_id = str(uuid4())

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["lock", "check", "--pipeline", "chembl_activity", "--run-id", run_id],
            )

        assert result.exit_code == 0
        assert "NOT held" in result.output

    def test_lock_check_invalid_uuid(self, cli_runner):
        """Test lock check with invalid UUID."""
        result = cli_runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                "invalid-uuid-format",
            ],
        )

        assert "Invalid run-id" in result.output or "valid UUID" in result.output


# =============================================================================
# config.py Tests - _config_to_dict helper
# =============================================================================


@pytest.mark.unit
class TestConfigToDict:
    """Tests for _config_to_dict helper function."""

    def test_config_to_dict_pydantic_model(self):
        """Test _config_to_dict with Pydantic model."""
        from bioetl.interfaces.cli.commands.config import _config_to_dict

        mock_model = MagicMock()
        mock_model.model_dump.return_value = {"field": "value"}

        result = _config_to_dict(mock_model)

        assert result == {"field": "value"}
        mock_model.model_dump.assert_called_once()

    def test_config_to_dict_dataclass(self):
        """Test _config_to_dict with dataclass-like object."""
        from bioetl.interfaces.cli.commands.config import _config_to_dict

        @dataclass
        class TestConfig:
            name: str
            value: int

        config = TestConfig(name="test", value=42)
        result = _config_to_dict(config)

        assert result["name"] == "test"
        assert result["value"] == 42

    def test_config_to_dict_nested(self):
        """Test _config_to_dict with nested objects."""
        from bioetl.interfaces.cli.commands.config import _config_to_dict

        @dataclass
        class Inner:
            inner_value: str

        @dataclass
        class Outer:
            inner: Inner
            outer_value: int

        config = Outer(inner=Inner(inner_value="nested"), outer_value=10)
        result = _config_to_dict(config)

        assert result["outer_value"] == 10
        assert isinstance(result["inner"], dict)
        assert result["inner"]["inner_value"] == "nested"

    def test_config_to_dict_primitive(self):
        """Test _config_to_dict with primitive value."""
        from bioetl.interfaces.cli.commands.config import _config_to_dict

        result = _config_to_dict("simple_string")

        assert result == {"value": "simple_string"}

    def test_config_to_dict_excludes_private(self):
        """Test _config_to_dict excludes private attributes."""
        from bioetl.interfaces.cli.commands.config import _config_to_dict

        class ConfigWithPrivate:
            def __init__(self):
                self.public = "visible"
                self._private = "hidden"

        config = ConfigWithPrivate()
        result = _config_to_dict(config)

        assert "public" in result
        assert "_private" not in result


# =============================================================================
# Formatters Tests - format_bytes
# =============================================================================


@pytest.mark.unit
class TestFormatBytes:
    """Tests for format_bytes formatter function."""

    def test_format_bytes_bytes(self):
        """Test format_bytes with small byte values."""
        from bioetl.interfaces.cli.formatters import format_bytes

        assert format_bytes(0) == "0 bytes"
        assert format_bytes(512) == "512 bytes"
        assert format_bytes(1023) == "1023 bytes"

    def test_format_bytes_kb(self):
        """Test format_bytes with kilobyte values."""
        from bioetl.interfaces.cli.formatters import format_bytes

        assert "KB" in format_bytes(1024)
        assert "KB" in format_bytes(1024 * 512)

    def test_format_bytes_mb(self):
        """Test format_bytes with megabyte values."""
        from bioetl.interfaces.cli.formatters import format_bytes

        assert "MB" in format_bytes(1024 * 1024)
        assert "MB" in format_bytes(1024 * 1024 * 512)

    def test_format_bytes_gb(self):
        """Test format_bytes with gigabyte values."""
        from bioetl.interfaces.cli.formatters import format_bytes

        assert "GB" in format_bytes(1024 * 1024 * 1024)
        assert "GB" in format_bytes(1024 * 1024 * 1024 * 10)

    def test_format_bytes_precision(self):
        """Test format_bytes precision."""
        from bioetl.interfaces.cli.formatters import format_bytes

        # 1.5 GB
        result = format_bytes(int(1.5 * 1024 * 1024 * 1024))
        assert "1.50 GB" in result


# =============================================================================
# Formatters Tests - echo functions
# =============================================================================


@pytest.mark.unit
class TestEchoFunctions:
    """Tests for CLI echo formatter functions."""

    def test_echo_error_with_detail(self, capsys):
        """Test echo_error with detail message."""
        from bioetl.interfaces.cli.formatters import echo_error

        echo_error("Main error", "Additional detail")

        captured = capsys.readouterr()
        assert "Main error: Additional detail" in captured.err

    def test_echo_error_without_detail(self, capsys):
        """Test echo_error without detail message."""
        from bioetl.interfaces.cli.formatters import echo_error

        echo_error("Simple error")

        captured = capsys.readouterr()
        assert "Simple error" in captured.err

    def test_echo_info(self, capsys):
        """Test echo_info outputs to stdout."""
        from bioetl.interfaces.cli.formatters import echo_info

        echo_info("Information message")

        captured = capsys.readouterr()
        assert "Information message" in captured.out

    def test_echo_warning(self, capsys):
        """Test echo_warning adds WARNING prefix."""
        from bioetl.interfaces.cli.formatters import echo_warning

        echo_warning("Something is wrong")

        captured = capsys.readouterr()
        assert "WARNING: Something is wrong" in captured.out

    def test_echo_dry_run_prefix(self, capsys):
        """Test echo_dry_run_prefix adds [DRY-RUN] prefix."""
        from bioetl.interfaces.cli.formatters import echo_dry_run_prefix

        echo_dry_run_prefix("Would do something")

        captured = capsys.readouterr()
        assert "[DRY-RUN] Would do something" in captured.out
