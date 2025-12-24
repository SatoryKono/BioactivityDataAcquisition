"""End-to-end tests for CLI dry-run and safety features."""

import pytest
from click.testing import CliRunner
from unittest.mock import AsyncMock, MagicMock, patch

from bioetl.interfaces.cli import cli, run


@pytest.fixture
def cli_runner():
    return CliRunner()


def test_cli_rebuild_requires_confirmation(cli_runner):
    """Test that rebuild requires confirmation without --yes."""
    with patch("bioetl.interfaces.cli.bootstrap_pipeline") as mock_bootstrap, \
         patch("bioetl.composition.registry.PipelineRegistry.list_pipelines", return_value=["test_pipe"]):

        result = cli_runner.invoke(cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild"])

        # Should prompt for confirmation
        assert "WARNING: REBUILD will delete existing data" in result.output
        assert result.exit_code == 1  # Aborted
        mock_bootstrap.assert_not_called()


def test_cli_rebuild_with_yes(cli_runner):
    """Test that rebuild works with --yes."""
    with patch("bioetl.interfaces.cli.bootstrap_pipeline") as mock_bootstrap, \
         patch("bioetl.composition.registry.PipelineRegistry.list_pipelines", return_value=["test_pipe"]):

        mock_runner = MagicMock()
        mock_runner.run = AsyncMock()  # Make run awaitable
        mock_runner.logger = MagicMock()  # Satisfy logger check
        mock_bootstrap.return_value = mock_runner

        result = cli_runner.invoke(cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--yes"])

        assert result.exit_code == 0
        mock_bootstrap.assert_called_once()


def test_cli_dry_run_flag(cli_runner):
    """Test that --dry-run flag is accepted and skips confirmation."""
    with patch("bioetl.interfaces.cli.bootstrap_pipeline") as mock_bootstrap, \
         patch("bioetl.composition.registry.PipelineRegistry.list_pipelines", return_value=["test_pipe"]):

        mock_runner = MagicMock()
        mock_runner.run = AsyncMock()  # Make run awaitable
        mock_runner.logger = MagicMock()  # Satisfy logger check
        mock_bootstrap.return_value = mock_runner

        result = cli_runner.invoke(cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--dry-run"])

        assert result.exit_code == 0
        assert "WARNING" not in result.output
        mock_bootstrap.assert_called_once()
