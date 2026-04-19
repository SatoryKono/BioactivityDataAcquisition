"""Unit tests for CLI commands (cleanup, config, lock).

Tests for CLI commands with mocked services, covering:
- cleanup.py: bronze_cleanup_command
- config.py: show_command, validate_command, show_settings_command, list_pipelines_command
- lock.py: release_command, check_command

Uses Click's CliRunner for command testing without real bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import ANY, AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview, LayerInfo
from bioetl.interfaces.cli.main import cli

TEST_SILVER_PATH = "test-output/silver/chembl/activity"
TEST_GOLD_PATH = "test-output/gold/chembl/activity"


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


@pytest.mark.unit
class TestCleanupPreviewCommand:
    """Tests for maintenance cleanup-preview command."""

    def test_cleanup_preview_help(self, cli_runner):
        """Test cleanup-preview --help shows required options."""
        result = cli_runner.invoke(cli, ["maintenance", "cleanup-preview", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output

    def test_cleanup_preview_success(self, cli_runner):
        """Test cleanup-preview renders dry-run layer preview."""
        preview = CleanupPreview(
            silver=LayerInfo(
                path=TEST_SILVER_PATH,
                file_count=3,
                exists=True,
            ),
            gold=LayerInfo(
                path=TEST_GOLD_PATH,
                file_count=1,
                exists=True,
            ),
            total_files=4,
        )

        with patch(
            "bioetl.interfaces.cli.commands.cleanup.preview_pipeline_cleanup",
            new=AsyncMock(return_value=preview),
        ) as mock_preview:
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "cleanup-preview",
                    "--pipeline",
                    "chembl_activity",
                ],
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Silver:" in result.output
        assert "Gold:" in result.output
        assert "Total items that would be cleared: ~4" in result.output
        mock_preview.assert_awaited_once_with("chembl_activity")

    def test_cleanup_preview_handles_exception(self, cli_runner):
        """Test cleanup-preview returns non-zero exit code on failures."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.preview_pipeline_cleanup",
            new=AsyncMock(side_effect=RuntimeError("preview failed")),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "cleanup-preview",
                    "--pipeline",
                    "chembl_activity",
                ],
            )

        assert result.exit_code == 1
        assert "cleanup-preview" in result.output


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


@dataclass
class MockPipelineInfo:
    """Mock PipelineInfo for testing validate command."""

    name: str = "chembl_activity"
    provider: str = "chembl"
    entity_type: str = "activity"
    silver_table: str = "chembl_activity"
    gold_table: str | None = "chembl_activity_gold"


@dataclass
class MockSettingsInfo:
    """Mock SettingsInfo for testing show-settings command."""

    env: str = "dev"
    data_dir: str = "/data"
    bronze_path: str = "/data/bronze"
    silver_path: str = "/data/silver"
    gold_path: str = "/data/gold"
    checkpoint_path: str = "/data/checkpoints"
    quarantine_path: str = "/data/quarantine"
    debug: bool = False
    test_mode: bool = False
    metrics_enabled: bool = True
    metrics_port: int = 8000
    batch_size: int = 100
    additional: dict[str, object] | None = None

    def __post_init__(self) -> None:
        if self.additional is None:
            self.additional = {}


@pytest.fixture
def mock_config_service():
    """Create a mock ConfigService."""
    service = MagicMock()
    # Default implementations
    service.get_pipeline_yaml_config.return_value = {
        "provider": "chembl",
        "entity_type": "activity",
        "silver_table": "chembl_activity",
        "gold_table": "chembl_activity_gold",
    }
    service.validate_pipeline_config.return_value = MockPipelineInfo()
    service.get_settings.return_value = MockSettingsInfo()
    service.list_pipelines.return_value = ["chembl_activity", "chembl_molecule"]
    return service


@pytest.mark.unit
class TestConfigShowCommand:
    """Tests for config show command."""

    def test_config_show_help(self, cli_runner):
        """Test config show --help shows correct options."""
        result = cli_runner.invoke(cli, ["config", "show", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--format" in result.output

    def test_config_show_yaml_format(self, cli_runner, mock_config_service):
        """Test config show with YAML format (default)."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show", "chembl_activity"])

        assert result.exit_code == 0
        assert "provider: chembl" in result.output
        assert "entity_type: activity" in result.output

    def test_config_show_json_format(self, cli_runner, mock_config_service):
        """Test config show with JSON format."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(
                cli, ["config", "show", "chembl_activity", "--format", "json"]
            )

        assert result.exit_code == 0
        assert '"provider": "chembl"' in result.output
        assert '"entity_type": "activity"' in result.output

    def test_config_show_file_not_found(self, cli_runner, mock_config_service):
        """Test config show handles missing config file."""
        mock_config_service.get_pipeline_yaml_config.side_effect = FileNotFoundError(
            "Config not found"
        )
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show", "nonexistent"])

        assert "Config file not found" in result.output or "not found" in result.output

    def test_config_show_validation_error(self, cli_runner, mock_config_service):
        """Test config show handles validation errors."""
        mock_config_service.get_pipeline_yaml_config.side_effect = ValueError(
            "Invalid configuration"
        )
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
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

    def test_config_validate_success(self, cli_runner, mock_config_service):
        """Test successful config validation."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "Configuration valid" in result.output
        assert "Provider: chembl" in result.output
        assert "Entity type: activity" in result.output
        assert "Silver table: chembl_activity" in result.output
        assert "Gold table: chembl_activity_gold" in result.output

    def test_config_validate_without_gold(self, cli_runner, mock_config_service):
        """Test config validation without gold table."""
        mock_config_service.validate_pipeline_config.return_value = MockPipelineInfo(
            gold_table=None
        )
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "Configuration valid" in result.output
        # Gold table line should not appear if None
        assert "Gold table:" not in result.output

    def test_config_validate_file_not_found(self, cli_runner, mock_config_service):
        """Test config validate handles missing config file."""
        mock_config_service.validate_pipeline_config.side_effect = FileNotFoundError(
            "Config not found"
        )
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "nonexistent"])

        assert "Config file not found" in result.output or "not found" in result.output

    def test_config_validate_invalid_config(self, cli_runner, mock_config_service):
        """Test config validate handles invalid configuration."""
        mock_config_service.validate_pipeline_config.side_effect = ValueError(
            "Missing required field"
        )
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
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

    def test_show_settings_yaml_format(self, cli_runner, mock_config_service):
        """Test show-settings with YAML format (default)."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "data_dir" in result.output
        assert "env" in result.output

    def test_show_settings_json_format(self, cli_runner, mock_config_service):
        """Test show-settings with JSON format."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(
                cli, ["config", "show-settings", "--format", "json"]
            )

        assert result.exit_code == 0
        assert '"data_dir"' in result.output
        assert '"env"' in result.output

    def test_show_settings_masks_api_key(self, cli_runner, mock_config_service):
        """Test show-settings masks sensitive API keys."""
        mock_config_service.get_settings.return_value = MockSettingsInfo(
            additional={"pubmed_api_key": "test_value_for_masking"}
        )

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "test_value_for_masking" not in result.output
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

    def test_list_pipelines_success(self, cli_runner, mock_config_service):
        """Test successful pipeline listing."""
        mock_config_service.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_molecule",
            "pubchem_compound",
        ]

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "Available pipelines:" in result.output
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output
        assert "pubchem_compound" in result.output

    def test_list_pipelines_empty(self, cli_runner, mock_config_service):
        """Test list-pipelines with no registered pipelines."""
        mock_config_service.list_pipelines.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "No pipelines registered" in result.output

    def test_list_pipelines_sorted(self, cli_runner, mock_config_service):
        """Test list-pipelines returns sorted list."""
        # Return unsorted list - the command should sort it
        mock_config_service.list_pipelines.return_value = [
            "z_pipeline",
            "a_pipeline",
            "m_pipeline",
        ]

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
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


# =============================================================================
# quarantine.py Tests - quarantine_inspect
# =============================================================================


@pytest.fixture
def mock_quarantine_manager():
    """Create a mock QuarantineManager."""
    manager = MagicMock()
    # echo_quarantine_record expects dict[str, Any], not dataclass
    manager.inspect = AsyncMock(
        return_value=[
            {
                "record_id": "rec_001",
                "pipeline": "chembl_activity",
                "reason": "Invalid SMILES",
                "timestamp": "2025-01-01T00:00:00Z",
            },
            {
                "record_id": "rec_002",
                "pipeline": "chembl_activity",
                "reason": "Missing field",
                "timestamp": "2025-01-01T00:01:00Z",
            },
        ]
    )
    return manager


@pytest.mark.unit
class TestQuarantineInspectCommand:
    """Tests for quarantine inspect command."""

    def test_quarantine_help(self, cli_runner):
        """Test quarantine --help shows subcommands."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])

        assert result.exit_code == 0
        assert "inspect" in result.output

    def test_quarantine_inspect_help(self, cli_runner):
        """Test quarantine inspect --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--limit" in result.output

    def test_quarantine_inspect_success(self, cli_runner, mock_quarantine_manager):
        """Test successful quarantine inspection."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "inspect", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=100, error_code=None
        )

    def test_quarantine_inspect_with_custom_limit(
        self, cli_runner, mock_quarantine_manager
    ):
        """Test quarantine inspection with custom limit."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "50",
                ],
            )

        assert result.exit_code == 0
        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=50, error_code=None
        )

    def test_quarantine_inspect_no_records(self, cli_runner):
        """Test quarantine inspection with no records."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "inspect", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "No records found" in result.output


# =============================================================================
# checkpoint.py Tests - checkpoint_list
# =============================================================================


@dataclass
class MockCheckpoint:
    """Mock Checkpoint for testing."""

    checkpoint_id: str
    pipeline: str
    created_at: str
    offset: int


@pytest.fixture
def mock_checkpoint_manager():
    """Create a mock CheckpointManager."""
    manager = MagicMock()
    manager.list_all = AsyncMock(
        return_value=[
            MockCheckpoint(
                checkpoint_id="cp_001",
                pipeline="chembl_activity",
                created_at="2025-01-01T00:00:00Z",
                offset=1000,
            ),
            MockCheckpoint(
                checkpoint_id="cp_002",
                pipeline="chembl_activity",
                created_at="2025-01-01T01:00:00Z",
                offset=2000,
            ),
        ]
    )
    return manager


@pytest.mark.unit
class TestCheckpointListCommand:
    """Tests for checkpoint list command."""

    def test_checkpoint_help(self, cli_runner):
        """Test checkpoint --help shows subcommands."""
        result = cli_runner.invoke(cli, ["checkpoint", "--help"])

        assert result.exit_code == 0
        assert "list" in result.output

    def test_checkpoint_list_help(self, cli_runner):
        """Test checkpoint list --help shows options."""
        result = cli_runner.invoke(cli, ["checkpoint", "list", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output

    def test_checkpoint_list_success(self, cli_runner, mock_checkpoint_manager):
        """Test successful checkpoint listing."""
        with patch(
            "bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_manager",
            return_value=mock_checkpoint_manager,
        ):
            result = cli_runner.invoke(
                cli, ["checkpoint", "list", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        mock_checkpoint_manager.list_all.assert_called_once()


# =============================================================================
# archive.py Tests - archive_command
# =============================================================================


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock MedallionLifecycleService."""
    service = MagicMock()
    service.archive = AsyncMock(return_value=42)  # 42 files archived
    return service


@pytest.mark.unit
class TestArchiveCommand:
    """Tests for archive command."""

    def test_archive_help(self, cli_runner):
        """Test archive --help shows options."""
        result = cli_runner.invoke(cli, ["maintenance", "archive", "--help"])

        assert result.exit_code == 0
        assert "TABLE" in result.output
        assert "TARGET_PATH" in result.output
        assert "--remove-source" in result.output

    def test_archive_success(self, cli_runner, mock_lifecycle_service):
        """Test successful archive operation."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/chembl"],
            )

        assert result.exit_code == 0
        assert "Archived 42 files" in result.output
        mock_lifecycle_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="/archive/chembl",
            remove_source=False,
        )

    def test_archive_with_remove_source(self, cli_runner, mock_lifecycle_service):
        """Test archive with --remove-source flag."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "archive",
                    "chembl.activity",
                    "/archive/chembl",
                    "--remove-source",
                ],
            )

        assert result.exit_code == 0
        mock_lifecycle_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="/archive/chembl",
            remove_source=True,
        )


# =============================================================================
# exit_codes.py Tests - get_exit_code_for_exception
# =============================================================================


@pytest.mark.unit
class TestGetExitCodeForException:
    """Tests for get_exit_code_for_exception function."""

    def test_direct_mapping_value_error(self):
        """Test direct mapping for ValueError."""
        from bioetl.interfaces.cli.exit_codes import (
            ExitCode,
            get_exit_code_for_exception,
        )

        exc = ValueError("Invalid value")
        result = get_exit_code_for_exception(exc)

        assert result == ExitCode.CONFIG_ERROR

    def test_direct_mapping_file_not_found(self):
        """Test direct mapping for FileNotFoundError."""
        from bioetl.interfaces.cli.exit_codes import (
            ExitCode,
            get_exit_code_for_exception,
        )

        exc = FileNotFoundError("File not found")
        result = get_exit_code_for_exception(exc)

        assert result == ExitCode.EX_NOINPUT

    def test_direct_mapping_keyboard_interrupt(self):
        """Test direct mapping for KeyboardInterrupt."""
        from bioetl.interfaces.cli.exit_codes import (
            ExitCode,
            get_exit_code_for_exception,
        )

        exc = KeyboardInterrupt()
        result = get_exit_code_for_exception(exc)

        assert result == ExitCode.SIGINT

    def test_mro_fallback_for_subclass(self):
        """Test MRO fallback for exception subclass."""
        from bioetl.interfaces.cli.exit_codes import (
            ExitCode,
            get_exit_code_for_exception,
        )

        # Create a custom ValueError subclass
        class CustomValueError(ValueError):
            pass

        exc = CustomValueError("Custom error")
        result = get_exit_code_for_exception(exc)

        # Should fall back to ValueError mapping via MRO
        assert result == ExitCode.CONFIG_ERROR

    def test_unknown_exception_returns_fail(self):
        """Test unknown exception returns FAIL."""
        from bioetl.interfaces.cli.exit_codes import (
            ExitCode,
            get_exit_code_for_exception,
        )

        # Create an exception not in the mapping
        class UnknownError(Exception):
            pass

        exc = UnknownError("Unknown")
        result = get_exit_code_for_exception(exc)

        assert result == ExitCode.FAIL


# =============================================================================
# run.py Tests - _map_status_to_exit_code
# =============================================================================


@pytest.mark.unit
class TestMapStatusToExitCode:
    """Tests for _map_status_to_exit_code function."""

    def test_success_status(self):
        """Test SUCCESS status maps to OK."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.SUCCESS, None)

        assert result == ExitCode.OK

    def test_dry_run_status(self):
        """Test DRY_RUN status maps to OK."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.DRY_RUN, None)

        assert result == ExitCode.OK

    def test_shutdown_status(self):
        """Test SHUTDOWN status maps to SIGINT."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.SHUTDOWN, None)

        assert result == ExitCode.SIGINT

    def test_failed_with_value_error(self):
        """Test FAILED with ValueError maps to CONFIG_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "ValueError")

        assert result == ExitCode.CONFIG_ERROR

    def test_failed_with_data_quality_error(self):
        """Test FAILED with DataQualityError maps to DATA_QUALITY_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "DataQualityError")

        assert result == ExitCode.DATA_QUALITY_ERROR

    def test_failed_with_lock_error(self):
        """Test FAILED with LockAcquisitionError maps to LOCK_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(
            PipelineRunResult.FAILED, "LockAcquisitionError"
        )

        assert result == ExitCode.LOCK_ERROR

    def test_failed_with_network_error(self):
        """Test FAILED with NetworkError maps to NETWORK_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "NetworkError")

        assert result == ExitCode.NETWORK_ERROR

    def test_failed_with_unknown_error(self):
        """Test FAILED with unknown error type maps to PIPELINE_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, "SomeUnknownError")

        assert result == ExitCode.PIPELINE_ERROR

    def test_failed_without_error_type(self):
        """Test FAILED without error type maps to PIPELINE_ERROR."""
        from bioetl.application.services import PipelineRunResult
        from bioetl.interfaces.cli.commands.run import _map_status_to_exit_code
        from bioetl.interfaces.cli.exit_codes import ExitCode

        result = _map_status_to_exit_code(PipelineRunResult.FAILED, None)

        assert result == ExitCode.PIPELINE_ERROR


@pytest.mark.unit
def test_run_prepared_request_async_uses_compat_runtime_path():
    """Prepared CLI request should still delegate through _run_pipeline_async."""
    import asyncio

    from bioetl.application.services import PipelineRunResult, RunResult
    from bioetl.application.services.cli_run_orchestration_models import (
        RunExecutionRequest,
    )
    from bioetl.interfaces.cli.commands import run as run_module

    options = MagicMock(name="run_options")
    request = RunExecutionRequest(
        pipeline="chembl_activity",
        options=options,
        health_server=False,
        health_port=8081,
    )
    expected = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="test-run-id",
        run_type="incremental",
    )
    registry = MagicMock(name="registry")

    with patch(
        "bioetl.interfaces.cli.commands.run._run_pipeline_async",
        new=AsyncMock(return_value=expected),
    ) as mock_run_pipeline_async:
        result = asyncio.run(
            run_module._run_prepared_request_async(request, registry=registry)
        )

    assert result is expected
    mock_run_pipeline_async.assert_awaited_once_with(
        "chembl_activity",
        options,
        health_server_enabled=False,
        health_port=8081,
        registry=registry,
    )


@pytest.mark.unit
def test_run_module_declares_expected_seam_inventory() -> None:
    """run.py should keep an explicit inventory of canonical and compatibility seams."""
    from bioetl.interfaces.cli.commands import run as run_module

    assert run_module._RUN_CANONICAL_BOUNDARY_SEAMS == (
        "get_cli_run_orchestration_service",
        "_build_run_command_input",
        "_build_run_pipeline_callable",
        "_map_status_to_exit_code",
        "_present_run_health_info",
        "_finalize_run_result",
        "_run_pipeline_async",
        "_run_prepared_request_async",
    )
    assert run_module._RUN_COMPATIBILITY_SEAMS == (
        "_get_runner_logger",
        "_handle_destructive_run_confirmation",
        "_validate_start_offset",
        "echo_health_server_info",
        "ensure_metrics_server_started",
        "health_server_context",
        "get_pipeline_runner_service",
    )

    for seam_name in (
        *run_module._RUN_CANONICAL_BOUNDARY_SEAMS,
        *run_module._RUN_COMPATIBILITY_SEAMS,
    ):
        assert hasattr(run_module, seam_name)

    assert (
        run_module._build_run_command_input is run_module._build_run_command_input_impl
    )
    assert (
        run_module._build_run_pipeline_callable
        is run_module._build_run_pipeline_callable_impl
    )
    assert run_module._map_status_to_exit_code is run_module.map_status_to_exit_code
    assert run_module._get_runner_logger is run_module.get_runner_logger
    assert (
        run_module._handle_destructive_run_confirmation
        is run_module.handle_destructive_run_confirmation
    )
    assert run_module._validate_start_offset is run_module.validate_options
    assert (
        run_module.echo_health_server_info is run_module._echo_health_server_info_impl
    )
    assert (
        run_module.ensure_metrics_server_started
        is run_module._ensure_metrics_server_started_impl
    )
    assert run_module.health_server_context is run_module._health_server_context_impl
    assert (
        run_module.get_pipeline_runner_service
        is run_module._get_pipeline_runner_service_impl
    )


@pytest.mark.unit
def test_execute_run_uses_canonical_runtime_callable_builder() -> None:
    """execute_run should delegate prepared-request runtime wiring to helper builder."""
    from bioetl.interfaces.cli.commands import run as run_module

    request = MagicMock(name="prepared_request")
    registry = MagicMock(name="registry")
    expected = MagicMock(name="run_result")
    run_pipeline_callable = AsyncMock(name="run_pipeline_callable")
    service = MagicMock(name="cli_run_service")
    service.execute_pipeline.return_value = expected

    with (
        patch.object(
            run_module,
            "_build_run_pipeline_callable",
            return_value=run_pipeline_callable,
        ) as mock_build_callable,
        patch.object(
            run_module,
            "get_cli_run_orchestration_service",
            return_value=service,
        ),
    ):
        result = run_module.execute_run(request, registry=registry)

    assert result is expected
    mock_build_callable.assert_called_once_with(
        registry=registry,
        run_pipeline_async_callable=run_module._run_pipeline_async,
    )
    service.execute_pipeline.assert_called_once_with(
        request=request,
        run_pipeline_async=run_pipeline_callable,
        run_coroutine=run_module.asyncio.run,
        flush_metrics=ANY,
    )


@pytest.mark.unit
def test_finalize_run_result_presents_and_exits() -> None:
    """CLI finalizer should render output before terminating with mapped exit code."""
    from bioetl.application.services import PipelineRunResult, RunResult
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.exit_codes import ExitCode

    result = RunResult(
        status=PipelineRunResult.SUCCESS,
        pipeline_name="chembl_activity",
        run_id="test-run-id",
        run_type="incremental",
    )

    with (
        patch.object(run_module, "_echo_run_result") as mock_presenter,
        patch.object(run_module, "_exit_with_code") as mock_exit,
        patch.object(
            run_module,
            "_map_status_to_exit_code",
            return_value=ExitCode.OK,
        ) as mock_map_status,
    ):
        run_module._finalize_run_result(result)

    mock_presenter.assert_called_once_with(result)
    mock_map_status.assert_called_once_with(PipelineRunResult.SUCCESS, None)
    mock_exit.assert_called_once_with(ExitCode.OK)


@pytest.mark.unit
def test_run_command_with_cli_policy_wires_registry_and_cli_seams() -> None:
    """CLI policy helper should resolve registry and inject canonical run seams."""
    from bioetl.interfaces.cli.commands import run as run_module
    from bioetl.interfaces.cli.commands.domains.run.command_policy import (
        RunCommandInput,
    )

    ctx = MagicMock(name="click_context")
    registry = MagicMock(name="registry")
    cli_input = RunCommandInput(
        pipeline="chembl_activity",
        run_type="incremental",
        resume=False,
        start_offset=None,
        limit=None,
        input_csv=None,
        filter_column=None,
        filter_field=None,
        dry_run=False,
        yes=True,
        vacuum_after_run=None,
        vacuum_retention_days=None,
        debug=False,
        health_server=True,
        health_port=8081,
        enable_tracing=True,
        use_cached_bronze=False,
        cached_bronze_date=None,
        cached_bronze_path=None,
    )

    with (
        patch.object(
            run_module,
            "resolve_context_registry",
            return_value=registry,
        ) as mock_resolve_registry,
        patch.object(run_module, "run_command_flow") as mock_run_command_flow,
    ):
        run_module._run_command_with_cli_policy(ctx, cli_input)

    mock_resolve_registry.assert_called_once_with(ctx)
    assert mock_run_command_flow.call_count == 1
    kwargs = mock_run_command_flow.call_args.kwargs
    assert kwargs["cli_input"] is cli_input
    assert kwargs["service"] is run_module.get_cli_run_orchestration_service()
    assert kwargs["health_info_presenter"] is run_module._present_run_health_info
    assert kwargs["result_finalizer"] is run_module._finalize_run_result
    assert kwargs["exit_func"] is run_module._exit_with_code
    execute_run_callable = kwargs["execute_run"]
    assert execute_run_callable.func is run_module.execute_run
    assert execute_run_callable.keywords == {"registry": registry}


@pytest.mark.unit
def test_run_callback_delegates_to_input_builder_and_cli_policy() -> None:
    """Click callback should stay a thin entrypoint over the run-policy seams."""
    from bioetl.interfaces.cli.commands import run as run_module

    ctx = MagicMock(name="click_context")
    cli_input = MagicMock(name="cli_input")

    with (
        patch.object(
            run_module,
            "_build_run_command_input",
            return_value=cli_input,
        ) as mock_build_input,
        patch.object(
            run_module,
            "_run_command_with_cli_policy",
        ) as mock_run_with_policy,
    ):
        run_module.run.callback.__wrapped__(
            ctx,
            pipeline="chembl_activity",
            run_type="incremental",
            resume=False,
            start_offset=None,
            limit=10,
            input_csv=None,
            filter_column="compound_id",
            filter_field="compound_id",
            dry_run=False,
            yes=True,
            vacuum_after_run=None,
            vacuum_retention_days=None,
            debug=False,
            health_server=True,
            health_port=8081,
            enable_tracing=True,
            use_cached_bronze=False,
            cached_bronze_date=None,
            cached_bronze_path=None,
            replay_of_run_id=None,
            replay_of_manifest_id=None,
            exact_replay=False,
        )

    mock_build_input.assert_called_once_with(
        pipeline="chembl_activity",
        run_type="incremental",
        resume=False,
        start_offset=None,
        limit=10,
        input_csv=None,
        filter_column="compound_id",
        filter_field="compound_id",
        dry_run=False,
        yes=True,
        vacuum_after_run=None,
        vacuum_retention_days=None,
        debug=False,
        health_server=True,
        health_port=8081,
        enable_tracing=True,
        use_cached_bronze=False,
        cached_bronze_date=None,
        cached_bronze_path=None,
        replay_of_run_id=None,
        replay_of_manifest_id=None,
    )
    mock_run_with_policy.assert_called_once_with(ctx, cli_input)


@pytest.mark.unit
def test_run_all_with_cli_policy_wires_registry_and_cli_seams() -> None:
    """Run-all policy helper should resolve registry and inject canonical seams."""
    from bioetl.interfaces.cli.commands import run_all as run_all_module
    from bioetl.interfaces.cli.commands.domains.run_all.command_policy import (
        RunAllCommandInput,
    )

    ctx = MagicMock(name="click_context")
    registry = MagicMock(name="registry")
    cli_input = RunAllCommandInput(
        source="chembl",
        run_type="incremental",
        limit=None,
        dry_run=False,
        yes=True,
        list_only=False,
        debug=False,
        health_server=True,
        health_port=8081,
    )

    with (
        patch.object(
            run_all_module,
            "resolve_context_registry",
            return_value=registry,
        ) as mock_resolve_registry,
        patch.object(
            run_all_module, "run_all_command_flow"
        ) as mock_run_all_command_flow,
    ):
        run_all_module._run_all_with_cli_policy(ctx, cli_input)

    mock_resolve_registry.assert_called_once_with(ctx)
    assert mock_run_all_command_flow.call_count == 1
    kwargs = mock_run_all_command_flow.call_args.kwargs
    assert kwargs["cli_input"] is cli_input
    assert kwargs["registry"] is registry
    assert (
        kwargs["destructive_confirmation"]
        is run_all_module._handle_destructive_confirmation
    )
    assert kwargs["listing_emitter"] is run_all_module.emit_run_all_listing
    assert kwargs["preview_emitter"] is run_all_module.emit_run_all_preview
    assert kwargs["health_info_presenter"] is run_all_module.echo_health_server_info
    assert kwargs["execute_batch"] is run_all_module._run_batch_with_policy
    assert kwargs["summary_presenter"] is run_all_module._echo_batch_summary
    assert kwargs["determine_exit_code"] is run_all_module._determine_exit_code
    assert kwargs["exit_func"] is run_all_module.exit_with_code


@pytest.mark.unit
def test_run_all_callback_delegates_to_input_builder_and_cli_policy() -> None:
    """Run-all Click callback should stay a thin entrypoint over policy seams."""
    from bioetl.interfaces.cli.commands import run_all as run_all_module

    ctx = MagicMock(name="click_context")
    cli_input = MagicMock(name="cli_input")

    with (
        patch.object(
            run_all_module,
            "build_run_all_command_input",
            return_value=cli_input,
        ) as mock_build_input,
        patch.object(
            run_all_module,
            "_run_all_with_cli_policy",
        ) as mock_run_with_policy,
    ):
        run_all_module.run_all.callback.__wrapped__(
            ctx,
            source="chembl",
            run_type="incremental",
            limit=10,
            dry_run=False,
            yes=True,
            list_only=False,
            debug=False,
            health_server=True,
            health_port=8081,
        )

    mock_build_input.assert_called_once_with(
        source="chembl",
        run_type="incremental",
        limit=10,
        dry_run=False,
        yes=True,
        list_only=False,
        debug=False,
        health_server=True,
        health_port=8081,
    )
    mock_run_with_policy.assert_called_once_with(ctx, cli_input)


# =============================================================================
# run.py Tests - Exception handlers in run command
# =============================================================================


@dataclass
class MockRunResult:
    """Mock RunResult for testing."""

    status: object
    error_message: str | None = None
    error_type: str | None = None


@pytest.mark.unit
class TestRunCommandExceptionHandlers:
    """Tests for exception handlers in run command."""

    def test_run_pipeline_not_found(self, cli_runner):
        """Test run command handles PipelineNotFoundError."""
        from bioetl.application.services import PipelineNotFoundError

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            side_effect=PipelineNotFoundError("foo", available=["bar", "baz"])
        )

        with (
            patch(
                "bioetl.interfaces.cli.registry_helpers.build_cli_registry"
            ) as mock_registry,
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch("bioetl.interfaces.cli.commands.run.ensure_metrics_server_started"),
            patch(
                "bioetl.interfaces.cli.commands.run.health_server_context", MagicMock()
            ),
        ):
            mock_registry.return_value.list_pipelines.return_value = ["foo"]
            result = cli_runner.invoke(cli, ["run", "--pipeline", "foo"])

        assert result.exit_code == 80  # CONFIG_ERROR
        assert "Pipeline not found" in result.output

    def test_run_unexpected_exception(self, cli_runner):
        """Test run command handles unexpected exceptions."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock(side_effect=RuntimeError("Unexpected failure"))

        with (
            patch(
                "bioetl.interfaces.cli.registry_helpers.build_cli_registry"
            ) as mock_registry,
            patch(
                "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service",
                return_value=mock_service,
            ),
            patch("bioetl.interfaces.cli.commands.run.ensure_metrics_server_started"),
            patch(
                "bioetl.interfaces.cli.commands.run.health_server_context", MagicMock()
            ),
        ):
            mock_registry.return_value.list_pipelines.return_value = ["foo"]
            result = cli_runner.invoke(cli, ["run", "--pipeline", "foo"])

        assert result.exit_code == 1  # FAIL
        assert "Unexpected error" in result.output


# =============================================================================
# canonical run support Tests - show_cleanup_preview error handling
# =============================================================================


@pytest.mark.unit
class TestShowCleanupPreview:
    """Tests for show_cleanup_preview function."""

    def test_show_cleanup_preview_success(self, capsys):
        """Test show_cleanup_preview success path."""
        from bioetl.interfaces.cli.commands.domains.run.support import (
            show_cleanup_preview,
        )

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support._preview_cleanup_async",
            new_callable=AsyncMock,
        ) as mock_preview:
            show_cleanup_preview("chembl_activity")

        mock_preview.assert_awaited_once_with("chembl_activity")

    def test_show_cleanup_preview_error(self, capsys):
        """Test show_cleanup_preview handles errors."""
        from bioetl.interfaces.cli.commands.domains.run.support import (
            show_cleanup_preview,
        )

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support._preview_cleanup_async",
            side_effect=RuntimeError("Preview failed"),
        ):
            show_cleanup_preview("chembl_activity")

        captured = capsys.readouterr()
        assert "Error previewing cleanup" in captured.err
