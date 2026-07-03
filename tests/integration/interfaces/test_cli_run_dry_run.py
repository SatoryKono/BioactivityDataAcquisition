"""Integration tests for CLI run --dry-run command.

Tests the dry-run mode which previews cleanup operations
without actually executing the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner

pytestmark = pytest.mark.integration


def _get_cli():
    from bioetl.interfaces.cli import cli

    return cli


def _register_all_pipelines() -> None:
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines()


class TestCliRunDryRun:
    """Test CLI run command with --dry-run flag."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        _register_all_pipelines()

    def test_dry_run_option_available(self, cli_runner: CliRunner):
        """Test that --dry-run option is available."""
        result = cli_runner.invoke(_get_cli(), ["run", "--help"])

        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "preview" in result.output.lower() or "cleanup" in result.output.lower()

    def test_dry_run_with_incremental_runs_pipeline(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that --dry-run with incremental mode runs the pipeline.

        Dry-run only affects rebuild/backfill cleanup preview.
        For incremental, the pipeline executes normally.
        """
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
            RunResult,
        )

        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run"
        ) as mock_asyncio_run:
            mock_asyncio_run.return_value = RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )

            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity", "--dry-run"],
            )

        # Incremental with dry-run proceeds normally (dry-run doesn't affect incremental)
        assert result.exit_code == 0
        # Verify asyncio.run was called (meaning pipeline was executed)
        mock_asyncio_run.assert_called_once()

    def test_dry_run_with_rebuild_shows_preview(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
        storage_paths: dict[str, Path],
    ):
        """Test that --dry-run with rebuild shows cleanup preview."""
        # Create mock CleanupPreview that preview_cleanup returns directly
        mock_preview = MagicMock()
        mock_preview.silver = MagicMock(
            exists=True,
            path=str(storage_paths["silver"] / "chembl_activity"),
            file_count=10,
        )
        mock_preview.gold = MagicMock(
            exists=True,
            path=str(storage_paths["gold"] / "chembl" / "activity"),
            file_count=5,
        )
        mock_preview.total_files = 15

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
            new=AsyncMock(return_value=mock_preview),
        ):
            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "rebuild",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0

        # Check preview output
        assert "[DRY-RUN]" in result.output
        assert "rebuild" in result.output.lower()
        assert "No changes were made" in result.output

    def test_dry_run_with_backfill_shows_preview(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
        storage_paths: dict[str, Path],
    ):
        """Test that --dry-run with backfill shows cleanup preview."""
        mock_preview = MagicMock()
        mock_preview.silver = MagicMock(
            exists=True,
            path=str(storage_paths["silver"] / "chembl_activity"),
            file_count=10,
        )
        mock_preview.gold = None  # No gold table configured
        mock_preview.total_files = 10

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
            new=AsyncMock(return_value=mock_preview),
        ):
            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "backfill",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "backfill" in result.output.lower()

    def test_dry_run_shows_non_existent_tables(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
        tmp_path: Path,
    ):
        """Test that --dry-run handles non-existent tables gracefully."""
        mock_preview = MagicMock()
        mock_preview.silver = MagicMock(
            exists=False,
            path=str(tmp_path / "silver" / "chembl_activity"),
            file_count=0,
        )
        mock_preview.gold = MagicMock(
            exists=False,
            path=str(tmp_path / "gold" / "chembl" / "activity"),
            file_count=0,
        )
        mock_preview.total_files = 0

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
            new=AsyncMock(return_value=mock_preview),
        ):
            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "rebuild",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "does not exist" in result.output
        assert "No changes were made" in result.output

    def test_dry_run_shows_file_counts(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
        tmp_path: Path,
    ):
        """Test that --dry-run shows file counts for existing tables."""
        mock_preview = MagicMock()
        mock_preview.silver = MagicMock(
            exists=True,
            path=str(tmp_path / "silver" / "chembl_activity"),
            file_count=42,
        )
        mock_preview.gold = MagicMock(
            exists=True,
            path=str(tmp_path / "gold" / "chembl" / "activity"),
            file_count=17,
        )
        mock_preview.total_files = 59

        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
            new=AsyncMock(return_value=mock_preview),
        ):
            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "rebuild",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        # Check that file counts are displayed
        assert "42 files" in result.output or "42" in result.output
        assert "17 files" in result.output or "17" in result.output
        assert "59" in result.output  # Total


class TestCliDryRunErrorHandling:
    """Test error handling in dry-run mode."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        _register_all_pipelines()

    def test_dry_run_handles_preview_error(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that --dry-run handles preview errors gracefully."""
        with patch(
            "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
            new=AsyncMock(side_effect=RuntimeError("Preview failed")),
        ):
            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "rebuild",
                    "--dry-run",
                ],
            )

        # Should show error message but not crash
        assert "Error" in result.output or "error" in result.output.lower()

    def test_dry_run_with_invalid_pipeline(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that --dry-run with invalid pipeline fails appropriately."""
        result = cli_runner.invoke(
            _get_cli(),
            ["run", "--pipeline", "nonexistent", "--run-type", "rebuild", "--dry-run"],
        )

        assert result.exit_code != 0
        assert "Unknown pipeline" in result.output or "Invalid" in result.output
