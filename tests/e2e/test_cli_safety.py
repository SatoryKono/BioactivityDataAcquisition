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

        # Should prompt for confirmation (message format from merged CLI)
        assert "WARNING: rebuild will clear existing data" in result.output
        assert result.exit_code == 1  # Click aborts when no input provided
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
    """Test that --dry-run flag shows preview and does NOT execute pipeline."""
    with patch("bioetl.interfaces.cli.bootstrap_pipeline") as mock_bootstrap, \
         patch("bioetl.interfaces.cli._preview_cleanup") as mock_preview, \
         patch("bioetl.composition.registry.PipelineRegistry.list_pipelines", return_value=["test_pipe"]):

        result = cli_runner.invoke(cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--dry-run"])

        assert result.exit_code == 0
        # Dry-run outputs preview info, not warning
        assert "[DRY-RUN]" in result.output
        # Dry-run should NOT call bootstrap_pipeline (returns early)
        mock_bootstrap.assert_not_called()
        # But should call preview
        mock_preview.assert_called_once()
