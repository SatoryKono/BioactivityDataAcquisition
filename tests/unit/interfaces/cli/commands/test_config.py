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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for config.py CLI commands.

Tests show, validate, show-settings, and list-pipelines subcommands.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli


@dataclass
class _MockPipelineInfo:
    name: str = "chembl_activity"
    provider: str = "chembl"
    entity_type: str = "activity"
    silver_table: str = "chembl_activity"
    gold_table: str | None = "chembl_activity_gold"


@dataclass
class _MockSettingsInfo:
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
    additional: dict = field(default_factory=dict)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_config_service() -> MagicMock:
    """Create a mock ConfigService with standard return values."""
    service = MagicMock()
    service.get_pipeline_yaml_config.return_value = {
        "provider": "chembl",
        "entity_type": "activity",
        "silver_table": "chembl_activity",
    }
    service.validate_pipeline_config.return_value = _MockPipelineInfo()
    service.get_settings.return_value = _MockSettingsInfo()
    service.list_pipelines.return_value = ["chembl_activity", "chembl_molecule"]
    return service


@pytest.mark.unit
class TestConfigGroupHelp:
    """Test the config command group."""

    def test_config_help_displays_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that config --help displays available subcommands."""
        result = cli_runner.invoke(cli, ["config", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "validate" in result.output
        assert "show-settings" in result.output
        assert "list-pipelines" in result.output


@pytest.mark.unit
class TestConfigShowCommand:
    """Tests for config show subcommand."""

    def test_show_help_displays_format_option(self, cli_runner: CliRunner) -> None:
        """Test config show --help shows --format option."""
        result = cli_runner.invoke(cli, ["config", "show", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output
        assert "json" in result.output
        assert "yaml" in result.output

    def test_show_yaml_output(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show command outputs YAML by default."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show", "chembl_activity"])

        assert result.exit_code == 0
        assert "chembl" in result.output

    def test_show_json_output(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show command outputs JSON when --format json is given."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(
                cli, ["config", "show", "chembl_activity", "--format", "json"]
            )

        assert result.exit_code == 0
        # JSON output should contain braces
        assert "{" in result.output
        assert "chembl" in result.output

    def test_show_value_error_prints_error(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show command prints error on ValueError."""
        mock_config_service.get_pipeline_yaml_config.side_effect = ValueError(
            "not found"
        )

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show", "unknown_pipeline"])

        assert result.exit_code == 80
        assert "error" in result.output.lower() or "Configuration" in result.output

    def test_show_file_not_found_prints_error(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show command prints error on FileNotFoundError."""
        mock_config_service.get_pipeline_yaml_config.side_effect = FileNotFoundError(
            "config.yaml not found"
        )

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show", "missing_pipeline"])

        assert result.exit_code == 66
        assert "not found" in result.output.lower() or "Config file" in result.output


@pytest.mark.unit
class TestConfigValidateCommand:
    """Tests for config validate subcommand."""

    def test_validate_help_displays_pipeline_arg(self, cli_runner: CliRunner) -> None:
        """Test config validate --help shows PIPELINE argument."""
        result = cli_runner.invoke(cli, ["config", "validate", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output

    def test_validate_success_prints_info(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test validate outputs provider, entity_type, and silver_table on success."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "chembl" in result.output
        assert "activity" in result.output
        assert "chembl_activity" in result.output

    def test_validate_prints_gold_table_when_present(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test validate also prints gold table when it is present."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "gold" in result.output.lower()

    def test_validate_invalid_config_prints_error(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test validate prints error when config is invalid."""
        mock_config_service.validate_pipeline_config.side_effect = ValueError(
            "invalid schema"
        )

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "validate", "bad_pipeline"])

        assert result.exit_code == 80
        assert "invalid" in result.output.lower() or "Configuration" in result.output


@pytest.mark.unit
class TestConfigShowSettingsCommand:
    """Tests for config show-settings subcommand."""

    def test_show_settings_help_displays_format_option(
        self, cli_runner: CliRunner
    ) -> None:
        """Test config show-settings --help shows --format option."""
        result = cli_runner.invoke(cli, ["config", "show-settings", "--help"])

        assert result.exit_code == 0
        assert "--format" in result.output

    def test_show_settings_yaml_output(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show-settings outputs YAML by default."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "data_dir" in result.output or "/data" in result.output

    def test_show_settings_json_output(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test show-settings outputs JSON when --format json is given."""
        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(
                cli, ["config", "show-settings", "--format", "json"]
            )

        assert result.exit_code == 0
        assert "{" in result.output

    def test_show_settings_command__masks_api_key__32864a70(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test that api_key fields are masked in output."""
        settings_with_key = _MockSettingsInfo(
            additional={"chembl_api_key": "supersecret"}
        )
        mock_config_service.get_settings.return_value = settings_with_key

        with patch(
            "bioetl.interfaces.cli.commands.config.get_config_service",
            return_value=mock_config_service,
        ):
            result = cli_runner.invoke(cli, ["config", "show-settings"])

        assert result.exit_code == 0
        assert "supersecret" not in result.output
        assert "MASKED" in result.output


@pytest.mark.unit
class TestConfigListPipelinesCommand:
    """Tests for config list-pipelines subcommand."""

    def test_list_pipelines_command__pipelines_success__7024e288(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test list-pipelines outputs all configured pipelines."""
        del mock_config_service
        with patch(
            "bioetl.interfaces.cli.commands.config.get_configured_pipeline_names",
            return_value=["chembl_activity", "chembl_molecule"],
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output

    def test_list_pipelines_no_pipelines_registered(
        self, cli_runner: CliRunner, mock_config_service: MagicMock
    ) -> None:
        """Test list-pipelines prints 'No pipelines' when list is empty."""
        del mock_config_service

        with patch(
            "bioetl.interfaces.cli.commands.config.get_configured_pipeline_names",
            return_value=[],
        ):
            result = cli_runner.invoke(cli, ["config", "list-pipelines"])

        assert result.exit_code == 0
        assert "No pipelines" in result.output
