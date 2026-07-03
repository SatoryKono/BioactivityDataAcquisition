"""Integration tests for CLI run command (incremental mode).

Tests the `bioetl run --pipeline <name>` command using mocks
to verify end-to-end CLI behavior without external dependencies.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from bioetl.interfaces.cli.exit_codes import ExitCode

pytestmark = pytest.mark.integration


def _get_cli():
    from bioetl.interfaces.cli import cli

    return cli


def _register_all_pipelines() -> None:
    from bioetl.composition.factories.pipeline.registry import register_all_pipelines

    register_all_pipelines()


class TestCliRunIncremental:
    """Test CLI run command for incremental pipeline runs."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        _register_all_pipelines()

    def test_run_help_displays_options(self, cli_runner: CliRunner):
        """Test that run --help displays available options."""
        result = cli_runner.invoke(_get_cli(), ["run", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-type" in result.output
        assert "--limit" in result.output
        assert "--resume" in result.output
        assert "--dry-run" in result.output

    def test_run_requires_pipeline_option(self, cli_runner: CliRunner):
        """Test that run command requires --pipeline option."""
        result = cli_runner.invoke(_get_cli(), ["run"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_run_rejects_unknown_pipeline(self, cli_runner: CliRunner):
        """Test that run command rejects unknown pipeline names."""
        result = cli_runner.invoke(
            _get_cli(), ["run", "--pipeline", "nonexistent_pipeline"]
        )

        assert result.exit_code != 0
        assert "Unknown pipeline" in result.output or "Invalid value" in result.output

    def test_run_validates_run_type(self, cli_runner: CliRunner):
        """Test that run command validates run-type values."""
        result = cli_runner.invoke(
            _get_cli(),
            ["run", "--pipeline", "chembl_activity", "--run-type", "invalid_type"],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output or "invalid_type" in result.output

    def test_run_accepts_limit_option(self, cli_runner: CliRunner):
        """Test that run command accepts --limit option."""
        # Just verify the option is accepted (not the actual run)
        result = cli_runner.invoke(_get_cli(), ["run", "--help"])

        assert "--limit" in result.output
        assert "Maximum number of records" in result.output
        assert "--exact-replay" in result.output

    def test_run_incremental_success(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test successful incremental pipeline run.

        Uses mocked service to verify CLI bootstrapping and execution flow.
        """
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
            RunResult,
        )

        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run"
        ) as mock_asyncio_run:
            # mock asyncio.run(coro) where coro is _run_pipeline_async
            # _run_pipeline_async returns RunResult
            mock_asyncio_run.return_value = RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )

            result = cli_runner.invoke(
                _get_cli(),
                ["run", "--pipeline", "chembl_activity", "--limit", "5"],
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        mock_asyncio_run.assert_called_once()

    def test_run_incremental_with_resume_flag(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test incremental run with --resume flag."""
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
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "5",
                    "--resume",
                ],
            )

        assert result.exit_code == 0, f"CLI failed: {result.output}"
        mock_asyncio_run.assert_called_once()

    def test_run_shows_version(self, cli_runner: CliRunner):
        """Test that --version displays version info."""
        result = cli_runner.invoke(_get_cli(), ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output or "version" in result.output.lower()

    def test_run_exact_replay_requires_cached_bronze(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ) -> None:
        result = cli_runner.invoke(
            _get_cli(),
            ["run", "--pipeline", "chembl_activity", "--exact-replay"],
        )

        assert result.exit_code == ExitCode.CONFIG_ERROR
        assert "--exact-replay currently requires --use-cached-bronze" in result.output


class TestCliRunTypes:
    """Test different run types via CLI."""

    @pytest.fixture(autouse=True)
    def setup_pipelines(self):
        """Register all pipelines before each test."""
        _register_all_pipelines()

    def test_run_type_incremental_is_default(self, cli_runner: CliRunner):
        """Test that incremental is the default run type."""
        result = cli_runner.invoke(_get_cli(), ["run", "--help"])

        assert "incremental" in result.output
        assert "default" in result.output.lower()

    def test_run_type_backfill_prompts_confirmation(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that backfill run type prompts for confirmation."""
        result = cli_runner.invoke(
            _get_cli(),
            ["run", "--pipeline", "chembl_activity", "--run-type", "backfill"],
            input="n\n",  # Answer 'no' to confirmation
        )

        # Should exit cleanly after user cancels
        assert result.exit_code == 0
        assert (
            "cancelled" in result.output.lower() or "confirm" in result.output.lower()
        )

    def test_run_type_rebuild_prompts_confirmation(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that rebuild run type prompts for confirmation."""
        result = cli_runner.invoke(
            _get_cli(),
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild"],
            input="n\n",  # Answer 'no' to confirmation
        )

        # Should exit cleanly after user cancels
        assert result.exit_code == 0
        assert (
            "cancelled" in result.output.lower() or "confirm" in result.output.lower()
        )

    def test_run_type_backfill_skip_confirmation_with_yes(
        self,
        cli_runner: CliRunner,
        temp_env: dict[str, str],
    ):
        """Test that -y skips confirmation for backfill."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineRunResult,
        )

        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run"
        ) as mock_asyncio_run:
            # _run_pipeline_async returns (status, error_message, error_type, run_id) tuple
            mock_asyncio_run.return_value = (
                PipelineRunResult.SUCCESS,
                None,
                None,
                "test-run-id",
            )

            result = cli_runner.invoke(
                _get_cli(),
                [
                    "run",
                    "--pipeline",
                    "chembl_activity",
                    "--run-type",
                    "backfill",
                    "-y",
                    "--limit",
                    "1",
                ],
            )

        # Check that it didn't ask for confirmation
        assert "cancelled" not in result.output.lower()
        # Should have called asyncio.run
        mock_asyncio_run.assert_called_once()


class TestCliMain:
    """Test main entry point."""

    def test_main_registers_pipelines(self):
        """Test that main() registers all pipelines."""
        runner = CliRunner()

        # Invoke main through the CLI
        result = runner.invoke(_get_cli(), ["--help"])

        assert result.exit_code == 0
        assert "run" in result.output
        assert "quarantine" in result.output
        assert "checkpoint" in result.output
