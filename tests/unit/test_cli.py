"""Unit tests for the CLI module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.core.cleanup_service import CleanupPreview, LayerInfo
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.interfaces.cli import cli, main


@pytest.fixture(autouse=True)
def ensure_registration():
    """Ensure pipeline factories are registered before CLI tests."""
    register_all_pipelines()


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestCheckpointCommands:
    """Tests for checkpoint CLI commands."""

    @patch("bioetl.interfaces.cli.get_checkpoint_manager")
    def test_checkpoint_list_command(self, mock_get_checkpoint_manager, runner):
        """Test that checkpoint list command works."""
        mock_checkpoint_manager = AsyncMock()
        mock_checkpoint_manager.list_all.return_value = ["cp1", "cp2"]
        mock_get_checkpoint_manager.return_value = mock_checkpoint_manager

        result = runner.invoke(cli, ["checkpoint", "list", "--pipeline", "dummy"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Listing checkpoints" in result.output
        assert "cp1" in result.output


class TestQuarantineCommands:
    """Tests for quarantine CLI commands."""

    @patch("bioetl.interfaces.cli.get_quarantine_manager")
    def test_quarantine_inspect_command(self, mock_get_quarantine_manager, runner):
        """Test that quarantine inspect command works."""
        mock_quarantine_manager = AsyncMock()
        mock_quarantine_manager.inspect.return_value = [
            {"error_code": "ERR01", "payload": "{}"}
        ]
        mock_get_quarantine_manager.return_value = mock_quarantine_manager

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Inspecting quarantine for test_pipeline" in result.output
        assert "ERR01" in result.output

    @patch("bioetl.interfaces.cli.get_quarantine_manager")
    def test_quarantine_inspect_empty_command(
        self, mock_get_quarantine_manager, runner
    ):
        """Test quarantine inspect command with no records."""
        mock_quarantine_manager = AsyncMock()
        mock_quarantine_manager.inspect.return_value = []
        mock_get_quarantine_manager.return_value = mock_quarantine_manager

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0
        assert "No records found" in result.output


class TestRunCommand:
    """Tests for the run CLI command."""

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_success(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
    ):
        """Test that run command works with valid arguments."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_create_runner.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_with_options(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
    ):
        """Test run command with all options."""
        from bioetl.composition.entrypoints import RunOptions

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            [
                "run",
                "--pipeline",
                "chembl_activity",
                "--run-type",
                "backfill",
                "--resume",
                "--limit",
                "1000",
                "-y",  # Skip confirmation prompt
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # create_pipeline_runner is called with (pipeline_name, RunOptions)
        call_args = mock_create_runner.call_args
        assert call_args[0][0] == "chembl_activity"  # pipeline name
        options = call_args[0][1]  # RunOptions
        assert isinstance(options, RunOptions)
        assert options.run_type == "backfill"
        assert options.resume is True
        assert options.limit == 1000

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_shutdown_error(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
    ):
        """Test run command handles shutdown error."""
        from bioetl.application.core.shutdown import PipelineShutdownError

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(side_effect=PipelineShutdownError())
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance
        mock_asyncio_run.side_effect = PipelineShutdownError("Shutdown")

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 130  # Shutdown exit code

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_exception(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
    ):
        """Test run command handles general exceptions."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(side_effect=RuntimeError("Test error"))
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance
        mock_asyncio_run.side_effect = RuntimeError("Test error")

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 1  # Error exit code


class TestMainFunction:
    """Tests for main entry point."""

    @patch("bioetl.interfaces.cli.cli")
    def test_main_calls_cli(self, mock_cli):
        """Test main function calls cli()."""
        main()
        mock_cli.assert_called_once()


class TestCliVersion:
    """Tests for CLI version."""

    def test_version_option(self, runner):
        """Test --version option."""
        from bioetl import __version__

        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert __version__ in result.output


class TestCliHelp:
    """Tests for CLI help."""

    def test_help_option(self, runner):
        """Test --help option."""
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "BioETL" in result.output

    def test_run_help(self, runner):
        """Test run --help option."""
        result = runner.invoke(cli, ["run", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output


class TestPipelineValidation:
    """Tests for pipeline name validation."""

    def test_invalid_pipeline_name_raises_error(self, runner):
        """Test that invalid pipeline name raises BadParameter."""
        result = runner.invoke(cli, ["run", "--pipeline", "nonexistent_pipeline"])

        assert result.exit_code == 2  # Click's error exit code for bad parameter
        assert "Unknown pipeline" in result.output or "Error" in result.output

    def test_valid_pipeline_names_listed_in_error(self, runner):
        """Test that available pipelines are listed in error message."""
        result = runner.invoke(cli, ["run", "--pipeline", "invalid_name"])

        # The error should mention available pipelines
        assert "chembl_activity" in result.output or "Available" in result.output


class TestRunCommandAdvanced:
    """Advanced tests for run command edge cases."""

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    def test_run_command_bootstrap_value_error(self, mock_create_runner, runner):
        """Test run command handles ValueError during bootstrap."""
        mock_create_runner.side_effect = ValueError("Invalid config")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    def test_run_command_bootstrap_file_not_found(self, mock_create_runner, runner):
        """Test run command handles FileNotFoundError during bootstrap."""
        mock_create_runner.side_effect = FileNotFoundError("Config not found")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    def test_run_command_bootstrap_generic_error(self, mock_create_runner, runner):
        """Test run command handles generic Exception during bootstrap."""
        mock_create_runner.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Initialization failed" in result.output

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_with_filter_options(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
        tmp_path,
    ):
        """Test run command with CSV filter options."""
        from bioetl.composition.entrypoints import RunOptions

        # Create a temporary CSV file
        csv_file = tmp_path / "filter.csv"
        csv_file.write_text("id\nCHEMBL123\nCHEMBL456")

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            [
                "run",
                "--pipeline",
                "chembl_activity",
                "--input-csv",
                str(csv_file),
                "--filter-column",
                "id",
                "--filter-field",
                "molecule_chembl_id",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        call_args = mock_create_runner.call_args
        assert call_args[0][0] == "chembl_activity"  # pipeline name
        options = call_args[0][1]  # RunOptions
        assert isinstance(options, RunOptions)
        assert options.input_csv == str(csv_file)
        assert options.filter_column == "id"
        assert options.filter_field == "molecule_chembl_id"

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    def test_run_command_missing_logger(self, mock_create_runner, runner):
        """Test run command handles missing logger gracefully."""
        mock_runner_instance = MagicMock(spec=[])  # Empty spec, no logger attribute
        mock_create_runner.return_value = mock_runner_instance

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Logger not initialized" in result.output


class TestDryRunMode:
    """Tests for dry-run mode and _preview_cleanup function."""

    @patch("bioetl.interfaces.cli.preview_cleanup")
    def test_dry_run_shows_preview(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test that dry-run mode shows file preview without execution."""
        # preview_cleanup returns CleanupPreview directly (it's async in entrypoints)
        mock_preview_cleanup.return_value = CleanupPreview(
            silver=LayerInfo(path="silver/path", file_count=5, exists=True),
            gold=LayerInfo(path="gold/path", file_count=0, exists=False),
            total_files=5,
        )

        result = runner.invoke(
            cli,
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
        assert "[DRY-RUN]" in result.output
        assert "silver/path (5 files)" in result.output
        assert "gold/path (does not exist)" in result.output
        assert "Total items that would be cleared: ~5" in result.output
        assert "No changes were made" in result.output

    @patch("bioetl.interfaces.cli.preview_cleanup")
    def test_dry_run_counts_existing_files(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test that dry-run correctly counts existing files."""
        mock_preview_cleanup.return_value = CleanupPreview(
            silver=LayerInfo(path="silver/path", file_count=2, exists=True),
            gold=None,
            total_files=2,
        )

        result = runner.invoke(
            cli,
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
        assert "2 files" in result.output

    @patch("bioetl.interfaces.cli.preview_cleanup")
    def test_dry_run_preview_exception(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test that dry-run handles exceptions during preview."""
        mock_preview_cleanup.side_effect = Exception("Preview error")

        result = runner.invoke(
            cli,
            [
                "run",
                "--pipeline",
                "chembl_activity",
                "--run-type",
                "rebuild",
                "--dry-run",
            ],
        )

        assert result.exit_code == 0  # Should catch exception and print error
        assert "Error previewing cleanup" in result.output

    @patch("bioetl.interfaces.cli.preview_cleanup")
    def test_dry_run_preview_variations(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test dry-run preview with different file existence combinations."""
        # Case: Silver missing, Gold exists
        mock_preview_cleanup.return_value = CleanupPreview(
            silver=LayerInfo(path="silver/path", file_count=0, exists=False),
            gold=LayerInfo(path="gold/path", file_count=10, exists=True),
            total_files=10,
        )

        result = runner.invoke(
            cli,
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
        assert "Silver: silver/path (does not exist)" in result.output
        assert "Gold: gold/path (10 files)" in result.output

    def test_rebuild_requires_confirmation(self, runner):
        """Test that rebuild without -y prompts for confirmation."""
        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild"],
            input="n\n",  # Answer 'no' to confirmation
        )

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    @patch("bioetl.interfaces.cli.create_pipeline_runner")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_rebuild_with_yes_skips_confirmation(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_create_runner,
        runner,
    ):
        """Test that rebuild with -y skips confirmation."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_runner_instance.logger = MagicMock()  # CLI needs logger
        mock_create_runner.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "-y"],
        )

        assert result.exit_code == 0
        mock_create_runner.assert_called_once()


class TestValidatePipelineName:
    """Tests for validate_pipeline_name callback."""

    def test_valid_pipeline_returns_value(self):
        """Test that valid pipeline name is returned unchanged."""
        from bioetl.interfaces.cli import validate_pipeline_name

        result = validate_pipeline_name(None, None, "chembl_activity")
        assert result == "chembl_activity"

    def test_invalid_pipeline_raises_bad_parameter(self):
        """Test that invalid pipeline raises BadParameter."""
        import click
        from bioetl.interfaces.cli import validate_pipeline_name

        with pytest.raises(click.BadParameter) as exc_info:
            validate_pipeline_name(None, None, "definitely_not_a_real_pipeline")

        assert "Unknown pipeline" in str(exc_info.value)
        assert "Available" in str(exc_info.value)
