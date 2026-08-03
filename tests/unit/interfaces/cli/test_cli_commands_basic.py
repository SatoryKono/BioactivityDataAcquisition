# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for the CLI module."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview, LayerInfo
from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.interfaces.cli import cli, main
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)
from bioetl.interfaces.cli.exit_codes import ExitCode

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def ensure_registration():
    """Provide a lightweight registry seam for CLI unit tests."""
    registry = PipelineRegistry()
    registry.list_pipelines = MagicMock(return_value=["chembl_activity"])

    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=registry,
        ),
        patch(
            "bioetl.interfaces.cli.commands.domains.run.support.build_cli_registry",
            return_value=registry,
        ),
        patch(
            "bioetl.interfaces.cli.commands.domains.run.support._resolve_populated_default_registry",
            return_value=registry,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run.ensure_observability_backend_started",
            return_value=ObservabilityBackendEnsureResult(
                status="failed",
                health_url="http://127.0.0.1:8081/health",
            ),
        ),
        patch(
            "bioetl.interfaces.cli.commands.run.publish_metrics_safely",
            return_value=True,
        ),
    ):
        yield


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


class TestCheckpointCommands:
    """Tests for checkpoint CLI commands."""

    @patch("bioetl.interfaces.cli.commands.checkpoint.get_checkpoint_runtime_service")
    def test_checkpoint_list_command(self, mock_get_checkpoint_runtime_service, runner):
        """Test that checkpoint list command works."""
        mock_checkpoint_runtime_service = AsyncMock()
        mock_checkpoint_runtime_service.list_all.return_value = ["cp1", "cp2"]
        mock_get_checkpoint_runtime_service.return_value = (
            mock_checkpoint_runtime_service
        )

        result = runner.invoke(cli, ["checkpoint", "list", "--pipeline", "dummy"])

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Listing checkpoints" in result.output
        assert "cp1" in result.output


class TestQuarantineCommands:
    """Tests for quarantine CLI commands."""

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service")
    def test_quarantine_inspect_command(
        self, mock_get_quarantine_runtime_service, runner
    ):
        """Test that quarantine inspect command works."""
        mock_quarantine_runtime_service = AsyncMock()
        mock_quarantine_runtime_service.inspect.return_value = [
            {"error_code": "ERR01", "payload": "{}"}
        ]
        mock_get_quarantine_runtime_service.return_value = (
            mock_quarantine_runtime_service
        )

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        assert "Inspecting quarantine for test_pipeline" in result.output
        assert "ERR01" in result.output

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_runtime_service")
    def test_quarantine_inspect_empty_command(
        self, mock_get_quarantine_runtime_service, runner
    ):
        """Test quarantine inspect command with no records."""
        mock_quarantine_runtime_service = AsyncMock()
        mock_quarantine_runtime_service.inspect.return_value = []
        mock_get_quarantine_runtime_service.return_value = (
            mock_quarantine_runtime_service
        )

        result = runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline"],
        )

        assert result.exit_code == 0
        assert "No records found" in result.output


class TestRunCommand:
    """Tests for the run CLI command."""

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_success(
        self,
        mock_asyncio_run,
        runner,
    ):
        """Test that run command works with valid arguments."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            records_fetched=100,
            records_silver=100,
        )

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_asyncio_run.assert_called_once()

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.runtime_helpers.get_pipeline_runner_service"
    )
    @patch("bioetl.interfaces.cli.commands.run.ensure_metrics_server_started")
    def test_run_command_passes_context_registry_to_service(
        self,
        mock_ensure_metrics,
        mock_get_service,
        runner,
    ):
        """Run command should use the explicit Click registry in runtime wiring."""
        registry = PipelineRegistry()
        registry.list_pipelines = MagicMock(return_value=["chembl_activity"])

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="chembl_activity",
                run_id="test-run-id",
                run_type="incremental",
            )
        )
        mock_get_service.return_value = mock_service

        with patch(
            "bioetl.interfaces.cli.commands.run.asyncio.run",
            side_effect=lambda coro: asyncio.new_event_loop().run_until_complete(coro),
        ):
            result = runner.invoke(
                cli,
                ["run", "--pipeline", "chembl_activity", "--no-health-server"],
                obj=registry,
            )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        mock_get_service.assert_called_once_with(registry=registry)

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_with_options(
        self,
        mock_asyncio_run,
        runner,
    ):
        """Test run command with all options."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="backfill",
            records_fetched=1000,
            records_silver=950,
            records_quarantined=50,
        )

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
        # Verify asyncio.run was called (it receives the coroutine)
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_shutdown_error(
        self,
        mock_asyncio_run,
        runner,
    ):
        """Test run command handles shutdown error."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SHUTDOWN,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            records_fetched=50,
        )

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 130  # Shutdown exit code

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_exception(
        self,
        mock_asyncio_run,
        runner,
    ):
        """Test run command handles general exceptions."""
        mock_asyncio_run.side_effect = RuntimeError("Test error")

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code == 1  # Error exit code


class TestMainFunction:
    """Tests for main entry point."""

    @patch("bioetl.interfaces.cli.main.build_cli_registry")
    def test_build_main_registry_uses_interface_registry_helpers(
        self,
        mock_build_cli_registry,
    ) -> None:
        """Main registry builder should delegate via the canonical CLI helper."""
        import importlib

        cli_main_module = importlib.import_module("bioetl.interfaces.cli.main")

        registry = MagicMock()
        mock_build_cli_registry.return_value = registry

        result = cli_main_module._build_main_registry()

        assert result is registry
        mock_build_cli_registry.assert_called_once_with()

    @patch("bioetl.interfaces.cli.main._build_main_registry")
    @patch("bioetl.interfaces.cli.main.cli")
    def test_main_calls_cli_without_eager_registry(
        self,
        mock_cli,
        mock_build_registry,
    ):
        """Main should defer registry creation until a command truly needs it."""

        main()

        mock_build_registry.assert_not_called()
        mock_cli.assert_called_once_with(obj=None)


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

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_bootstrap_value_error(self, mock_asyncio_run, runner):
        """Test run command handles PipelineNotFoundError during execution."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineNotFoundError,
        )

        # PipelineNotFoundError is caught at the CLI level when asyncio.run raises it
        mock_asyncio_run.side_effect = PipelineNotFoundError(
            "chembl_activity", "Invalid config"
        )

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == ExitCode.CONFIG_ERROR
        assert (
            "Pipeline not found" in result.output
            or "not found" in result.output.lower()
        )

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_bootstrap_file_not_found(self, mock_asyncio_run, runner):
        """Test run command handles FileNotFoundError during service call."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.FAILED,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            error_message="Config not found",
            error_type="FileNotFoundError",
        )

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        # File not found maps to EX_NOINPUT in _map_status_to_exit_code
        assert result.exit_code == ExitCode.EX_NOINPUT

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.runtime_helpers.get_pipeline_runner_service"
    )
    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_bootstrap_generic_error(
        self, mock_asyncio_run, mock_get_service, runner
    ):
        """Test run command handles generic Exception during execution."""
        mock_asyncio_run.side_effect = RuntimeError("Unexpected error")

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        assert result.exit_code == ExitCode.FAIL
        assert "Unexpected error" in result.output or "error" in result.output.lower()

    @patch("bioetl.interfaces.cli.commands.run._run_pipeline_async")
    def test_run_command_with_filter_options(
        self,
        mock_run_async,
        runner,
        tmp_path,
    ):
        """Test run command with CSV filter options."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            PipelineRunResult,
        )

        # Create a temporary CSV file
        csv_file = tmp_path / "filter.csv"
        csv_file.write_text("id\nCHEMBL123\nCHEMBL456")

        # Mock the async function to return success result
        mock_run_async.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            records_fetched=10,
            records_silver=10,
        )

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
                "molecule_id",
            ],
        )

        assert result.exit_code == 0, f"Command failed: {result.output}"
        # Verify _run_pipeline_async was called with correct arguments
        mock_run_async.assert_called_once()
        call_args = mock_run_async.call_args
        pipeline_name = call_args[0][0]  # First positional arg
        options = call_args[0][1]  # Second positional arg
        assert pipeline_name == "chembl_activity"
        assert isinstance(options, RunOptions)
        assert options.input_csv == str(csv_file)
        assert options.filter_column == "id"
        assert options.filter_field == "molecule_id"

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_run_command_missing_logger(self, mock_asyncio_run, runner):
        """Test run command handles service errors gracefully."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.FAILED,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="incremental",
            error_message="Internal error",
            error_type="RuntimeError",
        )

        result = runner.invoke(cli, ["run", "--pipeline", "chembl_activity"])

        # FAILED status with RuntimeError maps to PIPELINE_ERROR
        assert result.exit_code == ExitCode.PIPELINE_ERROR


class TestDryRunMode:
    """Tests for dry-run mode and cleanup preview rendering."""

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
        new_callable=AsyncMock,
    )
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

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
        new_callable=AsyncMock,
    )
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

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
        new_callable=AsyncMock,
    )
    def test_dry_run_preview_runtime_error(
        self,
        mock_preview_cleanup,
        runner,
    ):
        """Test that dry-run handles preview runtime failures gracefully."""
        mock_preview_cleanup.side_effect = RuntimeError("Preview error")

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

    @patch(
        "bioetl.interfaces.cli.commands.domains.run.support.preview_cleanup",
        new_callable=AsyncMock,
    )
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

    @patch("bioetl.interfaces.cli.commands.run.asyncio.run")
    def test_rebuild_with_yes_skips_confirmation(
        self,
        mock_asyncio_run,
        runner,
    ):
        """Test that rebuild with -y skips confirmation."""
        # _run_pipeline_async returns RunResult object
        mock_asyncio_run.return_value = RunResult(
            status=PipelineRunResult.SUCCESS,
            pipeline_name="chembl_activity",
            run_id="test-run-id",
            run_type="rebuild",
            records_fetched=100,
            records_silver=100,
        )

        result = runner.invoke(
            cli,
            ["run", "--pipeline", "chembl_activity", "--run-type", "rebuild", "-y"],
        )

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()


class TestValidatePipelineName:
    """Tests for validate_pipeline_name callback."""

    def test_valid_pipeline_returns_value(self):
        """Test that valid pipeline name is returned unchanged."""
        from bioetl.interfaces.cli.commands.domains.run.support import (
            validate_pipeline_name,
        )

        result = validate_pipeline_name(None, None, "chembl_activity")
        assert result == "chembl_activity"

    def test_invalid_pipeline_raises_bad_parameter(self):
        """Test that invalid pipeline raises BadParameter."""
        import click

        from bioetl.interfaces.cli.commands.domains.run.support import (
            validate_pipeline_name,
        )

        with pytest.raises(click.BadParameter) as exc_info:
            validate_pipeline_name(None, None, "definitely_not_a_real_pipeline")

        assert "Unknown pipeline" in str(exc_info.value)
        assert "Available" in str(exc_info.value)
