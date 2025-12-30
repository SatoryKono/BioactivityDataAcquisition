"""Unit tests for the CLI module."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

import pytest
from click.testing import CliRunner

from bioetl.application.core.cleanup_service import CleanupPreview, LayerInfo
from bioetl.application.services import RunResult, RunStatus
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.interfaces.cli import cli, main
from bioetl.interfaces.cli.exit_codes import ExitCode


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

    @patch("bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_manager")
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

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager")
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

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager")
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

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_success(self, mock_get_service, runner):
        """Test that run command works with valid arguments."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        mock_service.run.return_value = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental"
        )
        mock_get_service.return_value = mock_service

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Pipeline completed successfully" in result.output
        mock_service.run.assert_called_once()

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_with_options(self, mock_get_service, runner):
        """Test run command with all options."""
        from bioetl.application.services import RunOptions

        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        mock_service.run.return_value = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="backfill"
        )
        mock_get_service.return_value = mock_service

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

        # Verify run was called with correct options
        call_args = mock_service.run.call_args
        assert call_args[0][0] == "chembl_activity"  # pipeline_name

        # Check kwargs
        options = call_args.kwargs.get('options')
        assert isinstance(options, RunOptions)
        assert options.run_type == "backfill"
        assert options.resume is True
        assert options.limit == 1000

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_shutdown_error(self, mock_get_service, runner):
        """Test run command handles shutdown error."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        # The service returns status=SHUTDOWN, it doesn't raise exception to the caller usually
        # but run.py handles the status.
        mock_service.run.return_value = RunResult(
            status=RunStatus.SHUTDOWN,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental"
        )
        mock_get_service.return_value = mock_service

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        # Map SHUTDOWN status to ExitCode.SIGINT (130)
        assert result.exit_code == 130
        assert "gracefully shut down" in result.output

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_failed_status(self, mock_get_service, runner):
        """Test run command handles failed status."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        mock_service.run.return_value = RunResult(
            status=RunStatus.FAILED,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            error_message="Some error",
            error_type="ValueError"
        )
        mock_get_service.return_value = mock_service

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        # ValueError maps to CONFIG_ERROR (78)
        assert result.exit_code == ExitCode.CONFIG_ERROR
        assert "Pipeline failed" in result.output
        assert "Some error" in result.output

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_exception(self, mock_get_service, runner):
        """Test run command handles unexpected exceptions during execution call."""
        # If the service call itself raises (e.g. during bootstrap inside the service access)
        mock_service = MagicMock()
        mock_service.run.side_effect = RuntimeError("Unexpected execution error")
        mock_get_service.return_value = mock_service

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == ExitCode.FAIL
        assert "Unexpected error" in result.output


class TestMainFunction:
    """Tests for main entry point."""

    @patch("bioetl.interfaces.cli.main.cli")
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

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_run_command_bootstrap_value_error(self, mock_get_service, runner):
        """Test run command handles ValueError during bootstrap (PipelineNotFoundError)."""
        from bioetl.application.services import PipelineNotFoundError

        mock_service = MagicMock()
        mock_service.run.side_effect = PipelineNotFoundError("test_pipeline", [])
        mock_get_service.return_value = mock_service

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        # PipelineNotFoundError maps to CONFIG_ERROR in run.py except block
        assert result.exit_code == ExitCode.CONFIG_ERROR
        assert "Pipeline not found" in result.output

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run.handle_destructive_run_confirmation")
    def test_run_command_with_filter_options(
        self,
        mock_handle_confirmation,
        mock_get_service,
        runner,
        tmp_path,
    ):
        """Test run command with CSV filter options."""
        from bioetl.application.services import RunOptions

        # Create a temporary CSV file
        csv_file = tmp_path / "filter.csv"
        csv_file.write_text("id\nCHEMBL123\nCHEMBL456")

        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        mock_service.run.return_value = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental"
        )
        mock_get_service.return_value = mock_service
        mock_handle_confirmation.return_value = True

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

        call_args = mock_service.run.call_args
        options = call_args.kwargs['options']
        assert isinstance(options, RunOptions)
        assert options.input_csv == str(csv_file)
        assert options.filter_column == "id"
        assert options.filter_field == "molecule_chembl_id"


class TestDryRunMode:
    """Tests for dry-run mode and _preview_cleanup function."""

    @patch("bioetl.interfaces.cli.commands.run_helpers.preview_cleanup")
    def test_dry_run_shows_preview(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test that dry-run mode shows file preview without execution."""
        # preview_cleanup returns CleanupPreview directly (it's async in entrypoints but helper handles it)
        # Note: run_helpers.show_cleanup_preview calls preview_cleanup
        # We patch preview_cleanup in run_helpers

        mock_preview_cleanup.return_value = CleanupPreview(
            silver=LayerInfo(path="silver/path", file_count=5, exists=True),
            gold=LayerInfo(path="gold/path", file_count=0, exists=False),
            total_files=5,
        )

        # We also need to mock get_pipeline_runner_service because dry-run still creates the runner service for logic?
        # Actually run.py logic:
        # 1. handle_destructive_run_confirmation (if destructive)
        # 2. Build options (dry_run=True)
        # 3. Call _run_pipeline_async -> service.run()
        #
        # BUT wait, handle_destructive_run_confirmation calls show_cleanup_preview IF dry_run is True?
        # Let's check run.py.
        # run.py:
        # if not handle_destructive_run_confirmation(pipeline, run_type, dry_run, yes): return

        # We need to mock get_pipeline_runner_service for the actual run call later
        with patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.run = AsyncMock()
            mock_service.run.return_value = RunResult(
                status=RunStatus.DRY_RUN,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="rebuild"
            )
            mock_get_service.return_value = mock_service

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
            # Confirmation message comes from handle_destructive_run_confirmation -> show_cleanup_preview
            assert "[DRY-RUN]" in result.output
            assert "silver/path (5 files)" in result.output
            # "Dry-run completed" is NOT printed for destructive runs because run.py returns early
            # after handle_destructive_run_confirmation returns False

    @patch("bioetl.interfaces.cli.commands.run_helpers.preview_cleanup")
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

        with patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service") as mock_get_service:
            mock_service = MagicMock()
            mock_service.run = AsyncMock()
            mock_service.run.return_value = RunResult(
                status=RunStatus.DRY_RUN,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="rebuild"
            )
            mock_get_service.return_value = mock_service

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

    def test_rebuild_requires_confirmation(self, runner):
        """Test that rebuild without -y prompts for confirmation."""
        # For this test we don't need to patch service because it returns before calling service
        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild"],
            input="n\n",  # Answer 'no' to confirmation
        )

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    def test_rebuild_with_yes_skips_confirmation(self, mock_get_service, runner):
        """Test that rebuild with -y skips confirmation."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock()
        mock_service.run.return_value = RunResult(
            status=RunStatus.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="rebuild"
        )
        mock_get_service.return_value = mock_service

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "-y"],
        )

        assert result.exit_code == 0
        mock_service.run.assert_called_once()


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
