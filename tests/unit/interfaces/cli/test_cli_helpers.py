"""Unit tests for BioETL CLI.

Tests for cli package helper functions and Click commands.
Uses Click's CliRunner for command testing without real bootstrap.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli, main, validate_pipeline_name
from bioetl.interfaces.cli.commands.run import (
    _get_runner_logger,
    _handle_destructive_run_confirmation,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_registry():
    """Mock default registry for validation tests."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_molecule",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with patch(
        "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
        return_value=mock,
    ):
        yield mock


# =============================================================================
# validate_pipeline_name tests
# =============================================================================


@pytest.mark.unit
class TestValidatePipelineName:
    """Tests for validate_pipeline_name callback."""

    def test_valid_pipeline_returns_value(self, mock_registry):
        """Test that valid pipeline name is returned."""
        result = validate_pipeline_name(None, None, "chembl_activity")
        assert result == "chembl_activity"

    def test_invalid_pipeline_raises_bad_parameter(self, mock_registry):
        """Test that invalid pipeline raises BadParameter."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_pipeline_name(None, None, "nonexistent_pipeline")

        assert "Unknown pipeline: nonexistent_pipeline" in str(exc_info.value)
        assert "Available:" in str(exc_info.value)

    def test_shows_available_pipelines_in_error(self, mock_registry):
        """Test that error message includes available pipelines."""
        with pytest.raises(click.BadParameter) as exc_info:
            validate_pipeline_name(None, None, "invalid")

        error_msg = str(exc_info.value)
        assert "chembl_activity" in error_msg or "Available:" in error_msg


# =============================================================================
# _handle_destructive_run_confirmation tests
# =============================================================================


@pytest.mark.unit
class TestHandleDestructiveRunConfirmation:
    """Tests for _handle_destructive_run_confirmation helper."""

    def test_incremental_run_returns_true(self):
        """Test that incremental run skips confirmation."""
        result = _handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="incremental",
            dry_run=False,
            yes=False,
        )
        assert result is True

    @patch("bioetl.interfaces.cli.commands.domains.run.support.show_cleanup_preview")
    def test_rebuild_dry_run_shows_preview_returns_false(self, mock_preview):
        """Test that rebuild with dry-run shows preview and returns False."""
        result = _handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="rebuild",
            dry_run=True,
            yes=False,
        )

        assert result is False
        mock_preview.assert_called_once_with("chembl_activity")

    @patch("bioetl.interfaces.cli.commands.domains.run.support.show_cleanup_preview")
    def test_backfill_dry_run_shows_preview_returns_false(self, mock_preview):
        """Test that backfill with dry-run shows preview and returns False."""
        result = _handle_destructive_run_confirmation(
            pipeline="pubchem_compound",
            run_type="backfill",
            dry_run=True,
            yes=False,
        )

        assert result is False
        mock_preview.assert_called_once_with("pubchem_compound")

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.click.confirm",
        return_value=True,
    )
    def test_rebuild_with_confirmation_returns_true(self, mock_confirm):
        """Test that rebuild with user confirmation returns True."""
        result = _handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="rebuild",
            dry_run=False,
            yes=False,
        )

        assert result is True
        mock_confirm.assert_called_once()

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.click.confirm",
        return_value=False,
    )
    @patch("bioetl.interfaces.cli.commands.domains.run.support.sys.exit")
    def test_rebuild_cancelled_exits(self, mock_exit, mock_confirm):
        """Test that cancelled rebuild exits."""
        _handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="rebuild",
            dry_run=False,
            yes=False,
        )

        mock_exit.assert_called_once_with(0)

    def test_rebuild_with_yes_flag_skips_confirmation(self):
        """Test that --yes flag skips confirmation for rebuild."""
        result = _handle_destructive_run_confirmation(
            pipeline="chembl_activity",
            run_type="rebuild",
            dry_run=False,
            yes=True,
        )

        assert result is True

    def test_backfill_with_yes_flag_skips_confirmation(self):
        """Test that --yes flag skips confirmation for backfill."""
        result = _handle_destructive_run_confirmation(
            pipeline="uniprot_protein",
            run_type="backfill",
            dry_run=False,
            yes=True,
        )

        assert result is True


# =============================================================================
# _get_runner_logger tests
# =============================================================================


@pytest.mark.unit
class TestGetRunnerLogger:
    """Tests for _get_runner_logger helper."""

    def test_returns_logger_attribute(self):
        """Test that logger attribute is returned if present."""
        mock_runner = MagicMock()
        mock_logger = MagicMock()
        mock_runner.logger = mock_logger

        result = _get_runner_logger(mock_runner)
        assert result is mock_logger

    def test_returns_private_logger_fallback(self):
        """Test that _logger is returned as fallback."""
        mock_runner = MagicMock(spec=[])  # No attributes by default
        mock_logger = MagicMock()

        # Remove logger, add _logger
        type(mock_runner).logger = property(lambda s: None)
        mock_runner._logger = mock_logger

        result = _get_runner_logger(mock_runner)
        assert result is mock_logger

    def test_returns_none_when_no_logger(self):
        """Test that None is returned when no logger found."""
        mock_runner = MagicMock(spec=[])

        # Make getattr return None for both
        mock_runner.configure_mock(**{"logger": None, "_logger": None})

        # Create object without logger attributes
        class NoLoggerRunner:
            pass

        runner = NoLoggerRunner()
        result = _get_runner_logger(runner)
        assert result is None


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestCliCommands:
    """Tests for Click CLI commands using CliRunner."""

    def test_cli_shows_help(self, cli_runner):
        """Test that CLI --help works."""
        result = cli_runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "BioETL - Bioactivity Data ETL Pipeline" in result.output

    def test_cli_version(self, cli_runner):
        """Test that --version shows version."""
        from bioetl import __version__

        result = cli_runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_run_help(self, cli_runner):
        """Test that run --help works."""
        result = cli_runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-type" in result.output
        assert "--resume" in result.output
        assert "--limit" in result.output

    def test_quarantine_help(self, cli_runner):
        """Test that quarantine --help works."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])
        assert result.exit_code == 0
        assert "Manage quarantine" in result.output

    def test_checkpoint_help(self, cli_runner):
        """Test that checkpoint --help works."""
        result = cli_runner.invoke(cli, ["checkpoint", "--help"])
        assert result.exit_code == 0
        assert "Manage checkpoints" in result.output

    def test_maintenance_help(self, cli_runner):
        """Test that maintenance --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "--help"])
        assert result.exit_code == 0
        assert "Maintenance operations" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_invalid_pipeline_shows_error(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that invalid pipeline shows error."""
        result = cli_runner.invoke(cli, ["run", "--pipeline", "invalid"])
        assert result.exit_code != 0
        assert "Unknown pipeline" in result.output or "Error" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_with_valid_pipeline(
        self, mock_asyncio_run, mock_register, cli_runner, mock_registry
    ):
        """Test that valid pipeline is executed."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
            RunResult,
        )

        # _run_pipeline_async returns RunResult
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
        )

        result = cli_runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        # Should have called asyncio.run
        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run.ensure_metrics_server_started")
    def test_run_with_limit(
        self,
        mock_ensure_metrics,
        mock_get_service,
        mock_register,
        cli_runner,
        mock_registry,
    ):
        """Test that --limit is passed correctly."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )

        mock_service = MagicMock()
        mock_result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
        )
        mock_service.run = AsyncMock(return_value=mock_result)
        mock_get_service.return_value = mock_service

        # Use patch for asyncio.run that actually runs the coroutine
        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run",
            side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "100",
                    "--no-health-server",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify limit was passed via RunOptions
        call_args = mock_service.run.call_args
        assert call_args is not None, "service.run was not called"
        pipeline_name = call_args[0][0]
        options = call_args[1]["options"]  # RunOptions
        assert pipeline_name == "chembl_activity"
        assert isinstance(options, RunOptions)
        assert options.limit == 100

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run.get_pipeline_runner_service")
    @patch("bioetl.interfaces.cli.commands.run.ensure_metrics_server_started")
    def test_run_with_resume_flag(
        self,
        mock_ensure_metrics,
        mock_get_service,
        mock_register,
        cli_runner,
        mock_registry,
    ):
        """Test that --resume flag is passed correctly."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )

        mock_service = MagicMock()
        mock_result = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
        )
        mock_service.run = AsyncMock(return_value=mock_result)
        mock_get_service.return_value = mock_service

        # Use patch for asyncio.run that actually runs the coroutine
        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run",
            side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--resume",
                    "--no-health-server",
                ],
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Verify resume was passed via RunOptions
        call_args = mock_service.run.call_args
        assert call_args is not None, "service.run was not called"
        pipeline_name = call_args[0][0]
        options = call_args[1]["options"]  # RunOptions
        assert pipeline_name == "chembl_activity"
        assert isinstance(options, RunOptions)
        assert options.resume is True

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_exact_replay_without_cached_bronze_warns_boundary(
        self, mock_asyncio_run, mock_register, cli_runner, mock_registry
    ):
        """Exact replay without cached Bronze warns and exits with config error."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
            RunResult,
        )
        from bioetl.interfaces.cli.exit_codes import ExitCode

        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
        )

        result = cli_runner.invoke(
            cli, ["run", "--pipeline", "chembl_activity", "--exact-replay"]
        )

        assert result.exit_code == ExitCode.CONFIG_ERROR, (
            f"Command failed: {result.output}"
        )
        assert "outside the strict exact-replay boundary" in result.output
        assert "without --use-cached-bronze" in result.output
        assert (
            "--exact-replay currently requires --use-cached-bronze "
            "with snapshot-backed Bronze inputs" in result.output
        )

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_exact_replay_with_cached_bronze_omits_boundary_warning(
        self, mock_asyncio_run, mock_register, cli_runner, mock_registry
    ):
        """Snapshot-backed exact-replay intent should not emit the no-cache warning."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
            RunResult,
        )

        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
        )

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--pipeline",
                "chembl_activity",
                "--exact-replay",
                "--use-cached-bronze",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "without --use-cached-bronze" not in result.output


# =============================================================================
# Main entry point test
# =============================================================================


@pytest.mark.unit
class TestMainEntryPoint:
    """Tests for main() entry point."""

    @patch("bioetl.interfaces.cli.main.cli")
    @patch("bioetl.interfaces.cli.main._build_main_registry")
    def test_main_does_not_prebuild_registry(self, mock_build_registry, mock_cli):
        """Test that main() avoids eager registry construction."""
        main()

        mock_build_registry.assert_not_called()
        mock_cli.assert_called_once_with()

    @patch("bioetl.interfaces.cli.main.cli")
    @patch("bioetl.interfaces.cli.main._build_main_registry")
    def test_main_calls_cli(self, mock_build_registry, mock_cli):
        """Test that main() invokes CLI group."""
        main()

        mock_build_registry.assert_not_called()
        mock_cli.assert_called_once_with()
