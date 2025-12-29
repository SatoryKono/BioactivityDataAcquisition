"""End-to-end tests for CLI dry-run and safety features."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_registry():
    """Create a mock registry for CLI tests."""
    mock = MagicMock()
    mock.list_pipelines.return_value = ["test_pipe"]
    mock.contains.return_value = True
    return mock


def test_cli_rebuild_requires_confirmation(cli_runner, mock_registry):
    """Test that rebuild requires confirmation without --yes."""
    with (
        patch("bioetl.interfaces.cli.create_pipeline_runner") as mock_create_runner,
        patch("bioetl.interfaces.cli.get_default_registry", return_value=mock_registry),
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
            return_value=mock_registry,
        ),
    ):
        result = cli_runner.invoke(
            cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild"]
        )

        # Should prompt for confirmation (message format from merged CLI)
        assert "WARNING: rebuild will clear existing data" in result.output
        assert result.exit_code == 1  # Click aborts when no input provided
        mock_create_runner.assert_not_called()


def test_cli_rebuild_with_yes(cli_runner, mock_registry):
    """Test that rebuild works with --yes."""
    with (
        patch("bioetl.interfaces.cli.create_pipeline_runner") as mock_create_runner,
        patch("bioetl.interfaces.cli.get_default_registry", return_value=mock_registry),
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
            return_value=mock_registry,
        ),
    ):
        mock_runner = MagicMock()
        mock_runner.run = AsyncMock()  # Make run awaitable
        mock_runner.logger = MagicMock()  # Satisfy logger check
        mock_create_runner.return_value = mock_runner

        result = cli_runner.invoke(
            cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--yes"]
        )

        assert result.exit_code == 0
        mock_create_runner.assert_called_once()


def test_cli_dry_run_flag(cli_runner, mock_registry):
    """Test that --dry-run flag shows preview and does NOT execute pipeline."""
    with (
        patch("bioetl.interfaces.cli.create_pipeline_runner") as mock_create_runner,
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.show_cleanup_preview"
        ) as mock_preview,
        patch("bioetl.interfaces.cli.get_default_registry", return_value=mock_registry),
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
            return_value=mock_registry,
        ),
    ):
        result = cli_runner.invoke(
            cli,
            ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--dry-run"],
        )

        assert result.exit_code == 0
        # Dry-run outputs preview info, not warning
        assert "[DRY-RUN]" in result.output
        # Dry-run should NOT call create_pipeline_runner (returns early)
        mock_create_runner.assert_not_called()
        # But should call preview
        mock_preview.assert_called_once()
