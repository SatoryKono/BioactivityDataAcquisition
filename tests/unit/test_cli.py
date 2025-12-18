"""Unit tests for the CLI module."""

from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli, main


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
        mock_quarantine_service.get_stats.return_value = {"errors": 10}
        mock_bootstrap_quarantine.return_value = mock_quarantine_service

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Inspecting quarantine for test_pipeline" in result.output
        assert "errors" in result.output


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
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        call_kwargs = mock_bootstrap.call_args[1]
        assert call_kwargs["resume"] is True
        assert call_kwargs["limit"] == 1000

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
