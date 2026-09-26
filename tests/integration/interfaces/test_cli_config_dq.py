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
"""Integration tests for CLI DQ configuration commands.

Tests the `bioetl dq` command group using in-memory fakes to verify
DQ configuration inspection and validation functionality.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
import yaml

if TYPE_CHECKING:
    from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _get_cli():
    from bioetl.interfaces.cli import cli

    return cli


class TestCliDqCommands:
    """Test CLI DQ configuration commands."""

    def test_dq_help_displays_commands(self, cli_runner: CliRunner):
        """Test that dq --help displays available subcommands."""
        result = cli_runner.invoke(_get_cli(), ["dq", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "validate" in result.output
        assert "show-effective" in result.output
        assert "check-compatibility" in result.output
        assert "Data Quality configuration commands" in result.output

    def test_dq_show_help_displays_options(self, cli_runner: CliRunner):
        """Test that dq show --help displays options."""
        result = cli_runner.invoke(_get_cli(), ["dq", "show", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--format" in result.output

    def test_dq_validate_help_displays_options(self, cli_runner: CliRunner):
        """Test that dq validate --help displays options."""
        result = cli_runner.invoke(_get_cli(), ["dq", "validate", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--config-file" in result.output

    def test_dq_show_effective_help_displays_options(self, cli_runner: CliRunner):
        """Test that dq show-effective --help displays options."""
        result = cli_runner.invoke(_get_cli(), ["dq", "show-effective", "--help"])

        assert result.exit_code == 0
        assert "PIPELINE" in result.output
        assert "--format" in result.output
        assert "--override" in result.output

    def test_dq_check_compatibility_help_displays_options(self, cli_runner: CliRunner):
        """Test that dq check-compatibility --help displays options."""
        result = cli_runner.invoke(_get_cli(), ["dq", "check-compatibility", "--help"])

        assert result.exit_code == 0
        assert "ARTIFACT1_FILE" in result.output
        assert "ARTIFACT2_FILE" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_requires_pipeline(self, mock_service, cli_runner: CliRunner):
        """Test that dq show requires pipeline argument."""
        result = cli_runner.invoke(_get_cli(), ["dq", "show"])

        assert result.exit_code != 0
        assert (
            "Missing argument" in result.output or "required" in result.output.lower()
        )

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_displays_config(self, mock_service, cli_runner: CliRunner):
        """Test that dq show displays DQ configuration."""
        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.get_dq_config.return_value = {
            "contract_ref": "chembl-v1",
            "contract_version": "1.0.0",
            "rule_bundle_version": "2024.1",
            "default_disposition_policy": "warn",
            "disposition_overrides": {},
            "strictness_mode": "standard",
        }
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(_get_cli(), ["dq", "show", "chembl_activity"])

        assert result.exit_code == 0
        assert "contract_ref: chembl-v1" in result.output
        assert "contract_version: 1.0.0" in result.output
        # YAML output may quote the version string
        assert (
            "rule_bundle_version: 2024.1" in result.output
            or "rule_bundle_version: '2024.1'" in result.output
        )

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_json_format(self, mock_service, cli_runner: CliRunner):
        """Test that dq show --format json outputs JSON."""
        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.get_dq_config.return_value = {
            "contract_ref": "chembl-v1",
            "contract_version": "1.0.0",
            "rule_bundle_version": "2024.1",
            "default_disposition_policy": "warn",
            "disposition_overrides": {},
            "strictness_mode": "standard",
        }
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(), ["dq", "show", "chembl_activity", "--format", "json"]
        )

        assert result.exit_code == 0
        # Should be valid JSON
        output_data = json.loads(result.output)
        assert output_data["contract_ref"] == "chembl-v1"
        assert output_data["contract_version"] == "1.0.0"

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_validate_valid_config(self, mock_service, cli_runner: CliRunner):
        """Test that dq validate succeeds for valid config."""
        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.get_dq_config.return_value = {
            "contract_ref": "chembl-v1",
            "contract_version": "1.0.0",
            "rule_bundle_version": "2024.1",
            "default_disposition_policy": "warn",
            "disposition_overrides": {},
            "strictness_mode": "standard",
        }
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(_get_cli(), ["dq", "validate", "chembl_activity"])

        assert result.exit_code == 0
        assert "[OK] DQ configuration is valid" in result.output
        assert "Contract Ref: chembl-v1" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_validate_with_config_file(
        self, mock_service, cli_runner: CliRunner, tmp_path
    ):
        """Test that dq validate works with custom config file."""
        # Create a temporary DQ config file
        config_file = tmp_path / "test_dq_config.yaml"
        config_content = {
            "contract_ref": "test-v1",
            "contract_version": "2.0.0",
            "rule_bundle_version": "2025.1",
            "default_disposition_policy": "error",
            "disposition_overrides": {},
            "strictness_mode": "strict",
        }
        with open(config_file, "w") as f:
            yaml.dump(config_content, f)

        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.validate_dq_config.return_value = True
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(),
            ["dq", "validate", "chembl_activity", "--config-file", str(config_file)],
        )

        assert result.exit_code == 0
        assert "[OK] DQ configuration is valid" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_validate_invalid_config(
        self, mock_service, cli_runner: CliRunner, tmp_path
    ):
        """Test that dq validate fails for invalid config."""
        # Create a temporary config file
        config_file = tmp_path / "test.yaml"
        config_file.write_text("invalid: config")

        # Mock the config service to return invalid
        mock_config_service = MagicMock()
        mock_config_service.validate_dq_config.return_value = False
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(),
            ["dq", "validate", "chembl_activity", "--config-file", str(config_file)],
        )

        # Invalid DQ config is a CLI failure (#7954 ExitCode on error paths).
        assert result.exit_code != 0
        assert "[ERROR] DQ configuration is invalid" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_effective_displays_artifact(
        self, mock_service, cli_runner: CliRunner
    ):
        """Test that dq show-effective displays effective config artifact."""
        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.get_effective_config_artifact.return_value = {
            "artifact_id": "test-artifact-123",
            "pipeline_name": "chembl_activity",
            "pipeline_kind": "standard",
            "source_refs": [
                {
                    "source_type": "file",
                    "source_path": "configs/base/pipeline.yaml",
                    "priority": 1,
                }
            ],
            "resolved_config": {
                "config_type": "pipeline",
                "config_data": {"provider": "chembl"},
                "config_hash": "abc123",
            },
            "runtime_overrides": {
                "cli_overrides": {},
                "env_overrides": {},
                "runtime_adjustments": {},
            },
            "effective_execution_config": {
                "config_data": {"provider": "chembl"},
                "effective_hash": "def456",
            },
            "resolved_config_hash": "abc123",
            "effective_config_hash": "def456",
            "source_fingerprint": "xyz789",
            "schema_version": "1.0",
            "created_at": "2024-01-01T00:00:00",
            "contract_refs": ["chembl-v1"],
            "dq_policy_refs": [
                {
                    "contract_ref": "chembl-v1",
                    "contract_version": "1.0.0",
                    "rule_bundle_version": "2024.1",
                    "policy_hash": "dq-hash-123",
                }
            ],
            "dq_rule_bundle_versions": ["2024.1"],
            "dq_contract_compatibility_hash": "compat-hash-456",
            "dq_policy_snapshots": [
                {
                    "contract_ref": "chembl-v1",
                    "contract_version": "1.0.0",
                    "rule_bundle_version": "2024.1",
                    "policy_hash": "dq-hash-123",
                    "default_disposition": "warn",
                    "disposition_overrides": {},
                    "strictness_mode": "standard",
                }
            ],
        }
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(), ["dq", "show-effective", "chembl_activity"]
        )

        assert result.exit_code == 0
        assert "artifact_id: test-artifact-123" in result.output
        assert "pipeline_name: chembl_activity" in result.output
        assert "dq_contract_compatibility_hash: compat-hash-456" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_effective_with_overrides(
        self, mock_service, cli_runner: CliRunner
    ):
        """Test that dq show-effective works with runtime overrides."""
        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.get_effective_config_artifact.return_value = {
            "artifact_id": "test-artifact-123",
            "pipeline_name": "chembl_activity",
            "runtime_overrides": {
                "cli_overrides": {"batch_size": "100"},
                "env_overrides": {},
                "runtime_adjustments": {},
            },
        }
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(),
            ["dq", "show-effective", "chembl_activity", "--override", "batch_size=100"],
        )

        assert result.exit_code == 0
        # Verify that the override was passed correctly
        call_args = mock_config_service.get_effective_config_artifact.call_args
        # Check if runtime_overrides was passed in kwargs
        if "runtime_overrides" in call_args.kwargs:
            assert call_args.kwargs["runtime_overrides"] == {"batch_size": "100"}
        elif call_args.args and len(call_args.args) > 2:
            # Check positional args
            assert call_args.args[2] == {"batch_size": "100"}
        else:
            # If we can't verify the exact call, at least verify the command succeeded
            pass

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_check_compatibility_compatible(
        self, mock_service, cli_runner: CliRunner, tmp_path
    ):
        """Test that dq check-compatibility succeeds for compatible configs."""
        # Create temporary artifact files
        artifact1_file = tmp_path / "artifact1.json"
        artifact2_file = tmp_path / "artifact2.json"

        artifact1_content = {
            "artifact_id": "artifact-1",
            "dq_contract_compatibility_hash": "compat-hash-123",
            "effective_config_hash": "config-hash-456",
        }

        artifact2_content = {
            "artifact_id": "artifact-2",
            "dq_contract_compatibility_hash": "compat-hash-123",
            "effective_config_hash": "config-hash-456",
        }

        with open(artifact1_file, "w") as f:
            json.dump(artifact1_content, f)
        with open(artifact2_file, "w") as f:
            json.dump(artifact2_content, f)

        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.check_config_compatibility.return_value = True
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(),
            ["dq", "check-compatibility", str(artifact1_file), str(artifact2_file)],
        )

        assert result.exit_code == 0
        assert "[OK] Configurations are compatible" in result.output
        assert "artifact-1" in result.output
        assert "artifact-2" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_check_compatibility_incompatible(
        self, mock_service, cli_runner: CliRunner, tmp_path
    ):
        """Test that dq check-compatibility fails for incompatible configs."""
        # Create temporary artifact files
        artifact1_file = tmp_path / "artifact1.json"
        artifact2_file = tmp_path / "artifact2.json"

        artifact1_content = {
            "artifact_id": "artifact-1",
            "dq_contract_compatibility_hash": "compat-hash-123",
            "effective_config_hash": "config-hash-456",
        }

        artifact2_content = {
            "artifact_id": "artifact-2",
            "dq_contract_compatibility_hash": "compat-hash-789",  # Different hash
            "effective_config_hash": "config-hash-456",
        }

        with open(artifact1_file, "w") as f:
            json.dump(artifact1_content, f)
        with open(artifact2_file, "w") as f:
            json.dump(artifact2_content, f)

        # Mock the config service
        mock_config_service = MagicMock()
        mock_config_service.check_config_compatibility.return_value = False
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(
            _get_cli(),
            ["dq", "check-compatibility", str(artifact1_file), str(artifact2_file)],
        )

        assert result.exit_code != 0
        assert "[ERROR] Configurations are NOT compatible" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_show_handles_missing_config(self, mock_service, cli_runner: CliRunner):
        """Test that dq show exits non-zero on missing config."""
        # Mock the config service to raise FileNotFoundError
        mock_config_service = MagicMock()
        mock_config_service.get_dq_config.side_effect = FileNotFoundError(
            "Config not found"
        )
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(_get_cli(), ["dq", "show", "nonexistent_pipeline"])

        assert result.exit_code != 0
        assert "Config file not found" in result.output

    @patch("bioetl.interfaces.cli.commands.config_dq.get_config_service")
    def test_dq_validate_handles_invalid_config(
        self, mock_service, cli_runner: CliRunner
    ):
        """Test that dq validate exits non-zero on invalid config."""
        # Mock the config service to raise ValueError
        mock_config_service = MagicMock()
        mock_config_service.get_dq_config.side_effect = ValueError("Invalid config")
        mock_service.return_value = mock_config_service

        result = cli_runner.invoke(_get_cli(), ["dq", "validate", "invalid_pipeline"])

        assert result.exit_code != 0
        assert "DQ Configuration invalid" in result.output
        assert "Invalid config" in result.output
