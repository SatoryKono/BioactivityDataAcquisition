"""Unit tests for the CLI module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

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

    @patch("bioetl.interfaces.cli.bootstrap_checkpoint")
    def test_checkpoint_list_command(self, mock_bootstrap_checkpoint, runner):
        """Test that checkpoint list command works."""
        mock_checkpoint_service = AsyncMock()
        mock_checkpoint_service.list_all.return_value = ["cp1", "cp2"]
        mock_bootstrap_checkpoint.return_value = mock_checkpoint_service

        result = runner.invoke(cli, ["checkpoint", "list", "--pipeline", "dummy"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Listing checkpoints" in result.output
        assert "cp1" in result.output


class TestQuarantineCommands:
    """Tests for quarantine CLI commands."""

    @patch("bioetl.interfaces.cli.bootstrap_quarantine")
    def test_quarantine_inspect_command(self, mock_bootstrap_quarantine, runner):
        """Test that quarantine inspect command works."""
        mock_quarantine_service = AsyncMock()
        mock_quarantine_service.inspect.return_value = [
            {"error_code": "ERR01", "payload": "{}"}
        ]
        mock_bootstrap_quarantine.return_value = mock_quarantine_service

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Inspecting quarantine for test_pipeline" in result.output
        assert "ERR01" in result.output


class TestRunCommand:
    """Tests for the run CLI command."""

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_success(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test that run command works with valid arguments."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_bootstrap.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_bootstrap.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_with_options(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test run command with all options."""
        from bioetl.domain.context import PipelineRunContext
        from bioetl.domain.types import RunType

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_bootstrap.return_value = mock_runner_instance

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
        # bootstrap_pipeline is now called with PipelineRunContext as positional arg
        call_args = mock_bootstrap.call_args[0]
        ctx = call_args[0]
        assert isinstance(ctx, PipelineRunContext)
        assert ctx.pipeline_name == "chembl_activity"
        assert ctx.run_type == RunType.BACKFILL
        assert ctx.resume is True
        assert ctx.limit == 1000

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_shutdown_error(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test run command handles shutdown error."""
        from bioetl.application.core.shutdown import PipelineShutdownError

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(side_effect=PipelineShutdownError())
        mock_bootstrap.return_value = mock_runner_instance
        mock_asyncio_run.side_effect = PipelineShutdownError("Shutdown")

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 130  # Shutdown exit code

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_exception(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test run command handles general exceptions."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock(side_effect=RuntimeError("Test error"))
        mock_bootstrap.return_value = mock_runner_instance
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
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output


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

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    def test_run_command_bootstrap_value_error(self, mock_bootstrap, runner):
        """Test run command handles ValueError during bootstrap."""
        mock_bootstrap.side_effect = ValueError("Invalid config")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    def test_run_command_bootstrap_file_not_found(self, mock_bootstrap, runner):
        """Test run command handles FileNotFoundError during bootstrap."""
        mock_bootstrap.side_effect = FileNotFoundError("Config not found")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Configuration error" in result.output

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    def test_run_command_bootstrap_generic_error(self, mock_bootstrap, runner):
        """Test run command handles generic Exception during bootstrap."""
        mock_bootstrap.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Initialization failed" in result.output

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_run_command_with_filter_options(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
        tmp_path,
    ):
        """Test run command with CSV filter options."""
        from bioetl.domain.context import PipelineRunContext

        # Create a temporary CSV file
        csv_file = tmp_path / "filter.csv"
        csv_file.write_text("id\nCHEMBL123\nCHEMBL456")

        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_bootstrap.return_value = mock_runner_instance

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
        ctx = mock_bootstrap.call_args[0][0]
        assert isinstance(ctx, PipelineRunContext)
        assert ctx.input_csv == str(csv_file)
        assert ctx.filter_column == "id"
        assert ctx.filter_field == "molecule_chembl_id"

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    def test_run_command_missing_logger(self, mock_bootstrap, runner):
        """Test run command handles missing logger gracefully."""
        mock_runner_instance = MagicMock(spec=[])  # Empty spec, no logger attribute
        mock_bootstrap.return_value = mock_runner_instance

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == 1
        assert "Logger not initialized" in result.output


class TestMetricsServerIntegration:
    """Tests for metrics server integration in CLI."""

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    @patch("bioetl.composition.bootstrap.start_metrics_server")
    @patch("bioetl.interfaces.cli.get_settings")
    def test_metrics_server_failure_non_blocking(
        self,
        mock_get_settings,
        mock_start_metrics,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test that metrics server failure doesn't block pipeline run."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_bootstrap.return_value = mock_runner_instance

        mock_settings = MagicMock()
        mock_settings.metrics_port = 8000
        mock_get_settings.return_value = mock_settings

        mock_start_metrics.side_effect = Exception("Port already in use")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        # Pipeline should still succeed even if metrics server fails
        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()


class TestDryRunMode:
    """Tests for dry-run mode and _preview_cleanup function."""

    @patch("bioetl.interfaces.cli.load_pipeline_config")
    @patch("bioetl.interfaces.cli.get_settings")
    def test_dry_run_shows_preview(
        self,
        mock_get_settings,
        mock_load_config,
        runner,
        tmp_path,
    ):
        """Test that dry-run mode shows file preview without execution."""
        mock_settings = MagicMock()
        mock_settings.silver_path = tmp_path / "silver"
        mock_settings.gold_path = tmp_path / "gold"
        mock_get_settings.return_value = mock_settings

        mock_config = MagicMock()
        mock_config.silver_table = "test.table"
        mock_config.gold_table = "test.gold_table"
        mock_load_config.return_value = mock_config

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "No changes were made" in result.output

    @patch("bioetl.interfaces.cli.load_pipeline_config")
    @patch("bioetl.interfaces.cli.get_settings")
    def test_dry_run_counts_existing_files(
        self,
        mock_get_settings,
        mock_load_config,
        runner,
        tmp_path,
    ):
        """Test that dry-run correctly counts existing files."""
        # Create some test files
        silver_path = tmp_path / "silver" / "test" / "table"
        silver_path.mkdir(parents=True)
        (silver_path / "file1.parquet").write_text("test")
        (silver_path / "file2.parquet").write_text("test")

        mock_settings = MagicMock()
        mock_settings.silver_path = tmp_path / "silver"
        mock_settings.gold_path = tmp_path / "gold"
        mock_get_settings.return_value = mock_settings

        mock_config = MagicMock()
        mock_config.silver_table = "test.table"
        mock_config.gold_table = None
        mock_load_config.return_value = mock_config

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "--dry-run"],
        )

        assert result.exit_code == 0
        assert "2 files" in result.output

    def test_rebuild_requires_confirmation(self, runner):
        """Test that rebuild without -y prompts for confirmation."""
        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild"],
            input="n\n",  # Answer 'no' to confirmation
        )

        assert result.exit_code == 0
        assert "cancelled" in result.output.lower()

    @patch("bioetl.interfaces.cli.bootstrap_pipeline")
    @patch("bioetl.interfaces.cli.setup_shutdown_handlers")
    @patch("bioetl.interfaces.cli.asyncio.run")
    def test_rebuild_with_yes_skips_confirmation(
        self,
        mock_asyncio_run,
        mock_setup_handlers,
        mock_bootstrap,
        runner,
    ):
        """Test that rebuild with -y skips confirmation."""
        mock_runner_instance = MagicMock()
        mock_runner_instance.run = AsyncMock()
        mock_bootstrap.return_value = mock_runner_instance

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "-y"],
        )

        assert result.exit_code == 0
        mock_bootstrap.assert_called_once()


class TestValidatePipelineName:
    """Tests for validate_pipeline_name callback."""

    def test_valid_pipeline_returns_value(self):
        """Test that valid pipeline name is returned unchanged."""
        from bioetl.interfaces.cli import validate_pipeline_name

        result = validate_pipeline_name(None, None, "chembl_activity")
        assert result == "chembl_activity"

    def test_invalid_pipeline_raises_bad_parameter(self):
        """Test that invalid pipeline raises BadParameter."""
        from bioetl.interfaces.cli import validate_pipeline_name

        with pytest.raises(click.BadParameter) as exc_info:
            validate_pipeline_name(None, None, "definitely_not_a_real_pipeline")

        assert "Unknown pipeline" in str(exc_info.value)
        assert "Available" in str(exc_info.value)
