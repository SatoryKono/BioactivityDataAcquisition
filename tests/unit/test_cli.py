"""Unit tests for the CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.cli import cli


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestCheckpointCommands:
    """Tests for checkpoint CLI commands."""

    def test_checkpoint_delete_invokes_correctly(self, runner):
        """Test that checkpoint delete command invokes without uuid errors."""
        with (
            patch("bioetl.cli.bootstrap") as mock_bootstrap,
            patch("bioetl.cli.bootstrap_logger") as mock_logger,
        ):
            # Setup mocks
            mock_container = MagicMock()
            mock_container.checkpoint.delete = MagicMock()
            mock_bootstrap.return_value = mock_container
            mock_logger.return_value = MagicMock()

            # Run command with --yes to skip confirmation
            result = runner.invoke(
                cli,
                ["checkpoint", "delete", "--pipeline", "test_pipeline", "--yes"],
            )

            # Should not fail with NameError for uuid44
            assert "uuid44" not in str(result.exception) if result.exception else True
            assert result.exit_code == 0, f"Command failed: {result.output}"

            # Verify delete was called
            mock_container.checkpoint.delete.assert_called_once_with("test_pipeline")

    def test_checkpoint_list_command(self, runner):
        """Test that checkpoint list command works."""
        with (
            patch("bioetl.cli.bootstrap") as mock_bootstrap,
            patch("bioetl.cli.bootstrap_logger") as mock_logger,
        ):
            mock_container = MagicMock()
            mock_container.checkpoint.list_all = MagicMock(return_value=[])
            mock_bootstrap.return_value = mock_container
            mock_logger.return_value = MagicMock()

            result = runner.invoke(cli, ["checkpoint", "list"])

            assert result.exit_code == 0, f"Command failed: {result.output}"


class TestQuarantineCommands:
    """Tests for quarantine CLI commands."""

    def test_quarantine_inspect_command(self, runner):
        """Test that quarantine inspect command works."""
        with (
            patch("bioetl.cli.bootstrap") as mock_bootstrap,
            patch("bioetl.cli.bootstrap_logger") as mock_logger,
        ):
            mock_container = MagicMock()
            mock_container.quarantine.inspect = MagicMock(return_value=[])
            mock_bootstrap.return_value = mock_container
            mock_logger.return_value = MagicMock()

            result = runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "test_pipeline"],
            )

            assert result.exit_code == 0, f"Command failed: {result.output}"

    def test_quarantine_stats_command(self, runner):
        """Test that quarantine stats command works."""
        with (
            patch("bioetl.cli.bootstrap") as mock_bootstrap,
            patch("bioetl.cli.bootstrap_logger") as mock_logger,
        ):
            mock_container = MagicMock()
            mock_container.quarantine.get_stats = MagicMock(
                return_value={"total": 0, "by_error": {}}
            )
            mock_bootstrap.return_value = mock_container
            mock_logger.return_value = MagicMock()

            result = runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "test_pipeline"],
            )

            assert result.exit_code == 0, f"Command failed: {result.output}"
