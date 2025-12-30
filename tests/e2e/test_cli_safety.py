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
        patch(
            "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service"
        ) as mock_get_service,
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
            return_value=mock_registry,
        ),
    ):
        result = cli_runner.invoke(
            cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild"]
        )

        # Should prompt for confirmation (message format from merged CLI)
        assert "rebuild will clear existing data" in result.output.lower()
        assert result.exit_code != 0  # Click aborts when no input provided
        mock_get_service.assert_not_called()


def test_cli_rebuild_with_yes(cli_runner, mock_registry):
    """Test that rebuild works with --yes."""
    import asyncio

    from bioetl.application.services import RunResult, RunStatus

    with (
        patch(
            "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service"
        ) as mock_get_service,
        patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run"
        ) as mock_asyncio_run,
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.get_default_registry",
            return_value=mock_registry,
        ),
    ):
        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=RunStatus.SUCCESS,
                pipeline_name="test_pipe",
                run_id="test-run-id",
                run_type="rebuild",
            )
        )
        mock_get_service.return_value = mock_service
        mock_asyncio_run.side_effect = lambda coro: asyncio.get_event_loop().run_until_complete(coro)

        result = cli_runner.invoke(
            cli, ["run", "--pipeline", "test_pipe", "--run-type", "rebuild", "--yes"]
        )

        assert result.exit_code == 0
        mock_get_service.assert_called_once()


def test_cli_dry_run_flag(cli_runner, mock_registry):
    """Test that --dry-run flag shows preview and does NOT execute pipeline."""
    with (
        patch(
            "bioetl.interfaces.cli.commands.run.get_pipeline_runner_service"
        ) as mock_get_service,
        patch(
            "bioetl.interfaces.cli.commands.run_helpers.show_cleanup_preview"
        ) as mock_preview,
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
        # Dry-run should NOT call get_pipeline_runner_service (returns early)
        mock_get_service.assert_not_called()
        # But should call preview
        mock_preview.assert_called_once()
