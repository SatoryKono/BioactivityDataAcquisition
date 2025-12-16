"""Unit tests for the CLI module."""

import pytest
from click.testing import CliRunner

from bioetl.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestCheckpointCommands:
    """Tests for checkpoint CLI commands."""

    def test_checkpoint_list_command(self, runner):
        """Test that checkpoint list command works."""
        result = runner.invoke(cli, ["checkpoint", "list"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Listing checkpoints" in result.output


class TestQuarantineCommands:
    """Tests for quarantine CLI commands."""

    def test_quarantine_inspect_command(self, runner):
        """Test that quarantine inspect command works."""
        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Inspecting quarantine for test_pipeline" in result.output
