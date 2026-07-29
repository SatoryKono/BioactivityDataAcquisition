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
"""Unit tests for run_all CLI command with PipelineRunnerService mocking.

Tests the run-all command with mocked PipelineRunnerService for:
- Positive scenarios (successful pipeline execution)
- Negative scenarios (service errors, failures)
- Dry-run mode
- CLI formatter output verification
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineNotFoundError,
    PipelineRunResult,
    RunOptions,
    RunResult,
)
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.interfaces.cli.commands.run_all import (
    _run_all_pipelines_async,
)
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_registry():
    """Mock default registry with test pipelines."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_assay",
        "pubchem_compound",
    ]
    with patch(
        "bioetl.interfaces.cli.commands.run_all.resolve_context_registry",
        return_value=mock,
    ):
        yield mock


@pytest.fixture
def mock_pipeline_runner_service():
    """Create a mock PipelineRunnerService."""
    service = MagicMock()
    service.run = AsyncMock()
    service.list_pipelines = MagicMock(return_value=["chembl_activity", "chembl_assay"])
    service.validate_pipeline = MagicMock(return_value=True)
    return service


@pytest.fixture(autouse=True)
def mock_run_all_runtime_boundaries():
    """Keep run-all service-mock tests off real runtime startup seams."""
    with (
        patch(
            "bioetl.interfaces.cli.commands.run_all.health_server_context",
            MagicMock(),
        ) as mock_health,
        patch(
            "bioetl.interfaces.cli.commands.run_all.ensure_metrics_server_started",
            return_value=False,
        ),
        patch(
            "bioetl.interfaces.cli.commands.domains.health.metrics_server_integration.ensure_metrics_server_started",
            return_value=False,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_all.ensure_observability_backend_started",
            return_value=ObservabilityBackendEnsureResult(
                status="disabled",
                health_url="http://127.0.0.1:8081/health",
            ),
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_all.should_disable_transient_health_server",
            return_value=False,
        ),
    ):
        mock_health.return_value.__aenter__.return_value = None
        mock_health.return_value.__aexit__.return_value = None
        yield


def _create_run_result(
    pipeline_name: str,
    status: PipelineRunResult = PipelineRunResult.SUCCESS,
    run_type: str = "incremental",
    error_message: str | None = None,
) -> RunResult:
    """Helper to create RunResult objects for tests."""
    return RunResult(
        status=status,
        pipeline_name=pipeline_name,
        run_id="test-run-id",
        run_type=run_type,
        records_fetched=100,
        records_bronze=95,
        records_silver=90,
        records_gold=85,
        records_quarantined=5,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        error_message=error_message,
    )


# =============================================================================
# PipelineRunnerService Mock Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllWithMockedService:
    """Tests for run-all using mocked PipelineRunnerService."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_run_all_calls_service_for_each_pipeline(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that PipelineRunnerService.run is called for each pipeline."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service

        # Setup successful results for each pipeline
        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity"),
            _create_run_result("chembl_assay"),
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert result.exit_code == 0
        assert mock_pipeline_runner_service.run.call_count == 2

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_run_all_passes_correct_options(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that RunOptions are correctly passed to service."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity"
        )

        # Filter registry to single pipeline for easier assertion
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        # Backfill requires confirmation with --yes
        result = cli_runner.invoke(
            cli,
            [
                "run-all",
                "--source",
                "chembl",
                "--run-type",
                "backfill",
                "--limit",
                "50",
                "--yes",  # Skip confirmation prompt
            ],
        )

        assert result.exit_code == 0
        call_args = mock_pipeline_runner_service.run.call_args
        options = call_args[1]["options"]
        assert isinstance(options, RunOptions)
        assert options.run_type == "backfill"
        assert options.limit == 50

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_run_all_handles_service_failure(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test handling when PipelineRunnerService.run fails with exception."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.side_effect = RuntimeError("Service failure")

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert result.exit_code == ExitCode.PIPELINE_ERROR
        assert "unexpected error" in result.output.lower()

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_run_all_handles_pipeline_not_found(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test handling PipelineNotFoundError from service."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.side_effect = PipelineNotFoundError(
            "chembl_activity", ["other_pipeline"]
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert result.exit_code == ExitCode.PIPELINE_ERROR
        assert "not found" in result.output.lower()


# =============================================================================
# Dry-Run Mode Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllDryRunMode:
    """Tests for run-all dry-run mode with PipelineRunnerService."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_dry_run_passes_flag_to_service(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that --dry-run flag is passed to service options."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity", status=PipelineRunResult.DRY_RUN
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--dry-run", "--no-health-server"]
        )

        assert result.exit_code == 0
        call_args = mock_pipeline_runner_service.run.call_args
        options = call_args[1]["options"]
        assert options.dry_run is True

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_dry_run_shows_dry_run_prefix_in_output(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that dry-run output contains [DRY-RUN] prefix."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity", status=PipelineRunResult.DRY_RUN
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--dry-run", "--no-health-server"]
        )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_dry_run_reports_skipped_count(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that dry-run summary shows correct preview count."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
        ]

        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity", status=PipelineRunResult.DRY_RUN),
            _create_run_result("chembl_assay", status=PipelineRunResult.DRY_RUN),
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--dry-run", "--no-health-server"]
        )

        assert result.exit_code == 0
        assert "2 pipelines previewed" in result.output


# =============================================================================
# CLI Formatter Output Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllFormatterOutput:
    """Tests for run-all CLI output formatting."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_success_output_contains_ok_marker(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test successful run shows [OK] marker in output."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity"
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "[OK]" in result.output
        assert "completed successfully" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_failure_output_contains_fail_marker(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test failed run shows [FAIL] marker in output."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity",
            status=PipelineRunResult.FAILED,
            error_message="Connection timeout",
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "[FAIL]" in result.output
        assert "failed" in result.output.lower()

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_summary_shows_succeeded_count(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test summary output shows correct succeeded count."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
        ]

        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity"),
            _create_run_result("chembl_assay"),
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "Succeeded: 2" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_summary_shows_failed_count(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test summary output shows failed count when failures occur."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
        ]

        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity"),
            _create_run_result("chembl_assay", status=PipelineRunResult.FAILED),
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "Failed: 1" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_summary_shows_failed_pipeline_names(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test summary lists names of failed pipelines."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
        ]

        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity"),
            _create_run_result("chembl_assay", status=PipelineRunResult.FAILED),
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "chembl_assay" in result.output


# =============================================================================
# Shutdown Scenario Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllShutdownScenarios:
    """Tests for run-all shutdown handling."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_shutdown_stops_remaining_pipelines(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test that shutdown status stops processing remaining pipelines."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = [
            "chembl_activity",
            "chembl_assay",
            "chembl_molecule",
        ]

        # First succeeds, second gets shutdown, third should not run
        mock_pipeline_runner_service.run.side_effect = [
            _create_run_result("chembl_activity"),
            _create_run_result("chembl_assay", status=PipelineRunResult.SHUTDOWN),
            _create_run_result("chembl_molecule"),  # Should not be called
        ]

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        # Only 2 calls should have been made (third pipeline skipped)
        assert mock_pipeline_runner_service.run.call_count == 2
        assert "gracefully shut down" in result.output.lower()

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_shutdown_shows_stop_marker(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test shutdown status shows [STOP] marker."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity", status=PipelineRunResult.SHUTDOWN
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert "[STOP]" in result.output
        assert "WARNING:" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.build_cli_registry")
    @patch("bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service")
    def test_shutdown_exit_code_with_no_failures(
        self,
        mock_get_service,
        mock_get_registry,
        mock_register,
        cli_runner,
        mock_registry,
        mock_pipeline_runner_service,
    ):
        """Test shutdown without failures returns SIGINT exit code."""
        mock_get_registry.return_value = mock_registry
        mock_get_service.return_value = mock_pipeline_runner_service
        mock_registry.list_pipelines.return_value = ["chembl_activity"]

        mock_pipeline_runner_service.run.return_value = _create_run_result(
            "chembl_activity", status=PipelineRunResult.SHUTDOWN
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--no-health-server"]
        )

        assert result.exit_code == ExitCode.SIGINT


# =============================================================================
# Async Function Direct Tests
# =============================================================================


@pytest.mark.unit
@pytest.mark.asyncio
class TestRunAllAsyncFunction:
    """Direct tests for _run_all_pipelines_async function."""

    async def test_run_all_pipelines_async_success(self):
        """Test _run_all_pipelines_async with all successful runs."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            side_effect=[
                _create_run_result("pipeline1"),
                _create_run_result("pipeline2"),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            result = await _run_all_pipelines_async(
                pipelines=["pipeline1", "pipeline2"],
                options=RunOptions(),
                health_server_enabled=False,  # Disable to avoid port conflicts in parallel tests
            )

        assert result.total == 2
        assert result.succeeded == 2
        assert result.failed == 0
        assert result.all_succeeded is True

    async def test_run_all_pipelines_async_passes_explicit_registry(self):
        """Explicit registry should be passed to the runner service factory."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock(return_value=_create_run_result("pipeline1"))
        registry = PipelineRegistry()

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ) as mock_get_service:
            result = await _run_all_pipelines_async(
                pipelines=["pipeline1"],
                options=RunOptions(),
                health_server_enabled=False,
                registry=registry,
            )

        mock_get_service.assert_called_once_with(registry=registry)
        assert result.succeeded == 1

    async def test_run_all_pipelines_async_partial_failure(self):
        """Test _run_all_pipelines_async with some failures."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            side_effect=[
                _create_run_result("pipeline1"),
                _create_run_result("pipeline2", status=PipelineRunResult.FAILED),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            result = await _run_all_pipelines_async(
                pipelines=["pipeline1", "pipeline2"],
                options=RunOptions(),
                health_server_enabled=False,  # Disable to avoid port conflicts in parallel tests
            )

        assert result.succeeded == 1
        assert result.failed == 1
        assert result.failed_pipelines == ["pipeline2"]
        assert result.all_succeeded is False

    async def test_run_all_pipelines_async_handles_exception(self):
        """Test _run_all_pipelines_async handles runtime exceptions."""
        mock_service = MagicMock()
        mock_service.run = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            result = await _run_all_pipelines_async(
                pipelines=["pipeline1"],
                options=RunOptions(),
                health_server_enabled=False,  # Disable to avoid port conflicts in parallel tests
            )

        assert result.failed == 1
        assert result.failed_pipelines == ["pipeline1"]
