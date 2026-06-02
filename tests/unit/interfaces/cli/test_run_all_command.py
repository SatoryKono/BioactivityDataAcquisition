"""Unit tests for run-all CLI command.

Tests for the universal run-all command that runs all pipelines for a provider.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services.execution.pipeline_runner_models import (
    RunResult,
    PipelineRunResult,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    BatchRunResult,
    RunAllExecutionPlan,
    create_run_all_options,
    emit_run_all_listing,
    filter_pipelines_by_provider,
    get_available_providers,
    record_pipeline_failure,
    record_pipeline_result,
    resolve_run_all_execution_plan,
    should_prompt_for_destructive_run,
    validate_provider,
)
from bioetl.interfaces.cli.main import cli


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
        "chembl_assay",
        "chembl_molecule",
        "chembl_target",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with (
        patch(
            "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
            return_value=mock,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_all.resolve_context_registry",
            return_value=mock,
        ),
    ):
        yield mock


@pytest.fixture
def mock_registry_main():
    """Mock default registry for main.py imports."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_assay",
        "chembl_molecule",
        "chembl_target",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with (
        patch(
            "bioetl.interfaces.cli.registry_helpers.build_cli_registry",
            return_value=mock,
        ),
        patch(
            "bioetl.interfaces.cli.commands.run_all.resolve_context_registry",
            return_value=mock,
        ),
    ):
        yield mock


# =============================================================================
# BatchRunResult tests
# =============================================================================


@pytest.mark.unit
class TestBatchRunResult:
    """Tests for BatchRunResult dataclass."""

    def test_all_succeeded_true_when_no_failures__test_batch_run_result_interfaces_cli_test_run_all_command_98(
        self,
    ):
        """Test all_succeeded is True when no failures."""
        result = BatchRunResult(total=3, succeeded=3, failed=0)
        assert result.all_succeeded is True

    def test_all_succeeded_false_when_failures__test_batch_run_result_interfaces_cli_test_run_all_command_103(
        self,
    ):
        """Test all_succeeded is False when there are failures."""
        result = BatchRunResult(total=3, succeeded=2, failed=1)
        assert result.all_succeeded is False

    def test_all_succeeded_false_when_zero_total(self):
        """Test all_succeeded is False when no pipelines processed."""
        result = BatchRunResult(total=0, succeeded=0, failed=0)
        assert result.all_succeeded is False

    def test_batch_run_result__default_values__f7340e15(self):
        """Test default values are initialized correctly."""
        result = BatchRunResult()
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.results == []
        assert result.failed_pipelines == []


# =============================================================================
# Helper function tests
# =============================================================================


@pytest.mark.unit
class TestGetAvailableProviders:
    """Tests for get_available_providers function."""

    def test_available_providers__unique_providers__9bc8cfc0(self, mock_registry):
        """Test that unique providers are extracted from pipeline names."""
        providers = get_available_providers(registry=mock_registry)
        assert sorted(providers) == ["chembl", "pubchem", "uniprot"]

    def test_empty_when_no_pipelines(self):
        """Test that empty list returned when no pipelines registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        providers = get_available_providers(registry=mock)
        assert providers == []


@pytest.mark.unit
class TestFilterPipelinesByProvider:
    """Tests for filter_pipelines_by_provider function."""

    def test_filters_chembl_pipelines(self, mock_registry):
        """Test that ChEMBL pipelines are correctly filtered."""
        pipelines = filter_pipelines_by_provider("chembl", registry=mock_registry)
        assert pipelines == [
            "chembl_activity",
            "chembl_assay",
            "chembl_molecule",
            "chembl_target",
        ]

    def test_filters_pubchem_pipelines(self, mock_registry):
        """Test that PubChem pipelines are correctly filtered."""
        pipelines = filter_pipelines_by_provider("pubchem", registry=mock_registry)
        assert pipelines == ["pubchem_compound"]

    def test_pipelines_by_provider__for_unknown_provider__808b8446(self, mock_registry):
        """Test that empty list returned for unknown provider."""
        pipelines = filter_pipelines_by_provider("unknown", registry=mock_registry)
        assert pipelines == []


@pytest.mark.unit
class TestValidateProvider:
    """Tests for validate_provider function."""

    def test_validate_provider__returns_true__b8bcb899(self, mock_registry):
        """Test that valid provider returns (True, None)."""
        is_valid, error = validate_provider("chembl", registry=mock_registry)
        assert is_valid is True
        assert error is None

    def test_validate_provider__returns_false__732c6628(self, mock_registry):
        """Test that invalid provider returns (False, error_message)."""
        is_valid, error = validate_provider("invalid", registry=mock_registry)
        assert is_valid is False
        assert "No pipelines found for provider 'invalid'" in error
        assert "Available providers:" in error

    def test_empty_registry_returns_error(self):
        """Test that empty registry returns appropriate error."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        is_valid, error = validate_provider("chembl", registry=mock)
        assert is_valid is False
        assert "No pipelines are registered" in error


@pytest.mark.unit
class TestRunAllHelpers:
    """Tests for extracted run-all helper functions."""

    def test_create_run_all_options_enables_debug_log_level(self) -> None:
        """Debug flag should map to DEBUG log level in RunOptions."""
        options = create_run_all_options(
            run_type="incremental",
            limit=25,
            dry_run=False,
            debug=True,
        )

        assert options.run_type == "incremental"
        assert options.limit == 25
        assert options.dry_run is False
        assert options.log_level == "DEBUG"

    def test_resolve_run_all_execution_plan_resolves_pipelines_and_options(
        self, mock_registry
    ) -> None:
        """Execution plan helper should validate provider and build RunOptions."""
        plan, error = resolve_run_all_execution_plan(
            source="chembl",
            run_type="incremental",
            limit=25,
            dry_run=True,
            debug=False,
            registry=mock_registry,
        )

        assert error is None
        assert plan == RunAllExecutionPlan(
            pipelines=[
                "chembl_activity",
                "chembl_assay",
                "chembl_molecule",
                "chembl_target",
            ],
            options=create_run_all_options(
                run_type="incremental",
                limit=25,
                dry_run=True,
                debug=False,
            ),
        )

    def test_resolve_run_all_execution_plan_returns_error_for_invalid_provider(
        self, mock_registry
    ) -> None:
        """Execution plan helper should preserve provider validation failures."""
        plan, error = resolve_run_all_execution_plan(
            source="missing",
            run_type="incremental",
            limit=None,
            dry_run=False,
            debug=False,
            registry=mock_registry,
        )

        assert plan is None
        assert error is not None
        assert "No pipelines found for provider 'missing'" in error

    @patch("bioetl.interfaces.cli.commands.domains.run_all.support.echo_warning")
    def test_record_pipeline_result_shutdown_requests_stop(
        self,
        mock_echo_warning,
    ) -> None:
        """Shutdown result should mark the batch as skipped and stop execution."""
        batch_result = BatchRunResult(total=2)
        result = RunResult(
            status=PipelineRunResult.SHUTDOWN,
            pipeline_name="chembl_activity",
            run_id="run-id",
            run_type="incremental",
        )

        should_stop = record_pipeline_result(
            batch_result=batch_result,
            pipeline="chembl_activity",
            result=result,
        )

        assert should_stop is True
        assert batch_result.skipped == 1
        assert batch_result.results == [result]
        mock_echo_warning.assert_called_once()

    @patch("bioetl.interfaces.cli.commands.domains.run_all.support.echo_error")
    def test_record_pipeline_failure_tracks_failed_pipeline(
        self,
        mock_echo_error,
    ) -> None:
        """Failure helper should update counters and preserve pipeline name."""
        batch_result = BatchRunResult(total=1)

        record_pipeline_failure(
            batch_result=batch_result,
            pipeline="chembl_activity",
            title="[FAIL] chembl_activity: failed",
            detail="boom",
        )

        assert batch_result.failed == 1
        assert batch_result.failed_pipelines == ["chembl_activity"]
        mock_echo_error.assert_called_once_with(
            "[FAIL] chembl_activity: failed",
            "boom",
        )

    def test_should_prompt_for_destructive_run_only_when_required(self) -> None:
        """Prompting should be limited to destructive non-dry interactive runs."""
        assert (
            should_prompt_for_destructive_run(
                run_type="rebuild",
                dry_run=False,
                yes=False,
            )
            is True
        )
        assert (
            should_prompt_for_destructive_run(
                run_type="incremental",
                dry_run=False,
                yes=False,
            )
            is False
        )

    @patch("bioetl.interfaces.cli.commands.domains.run_all.support.echo_info")
    def test_emit_run_all_listing_prints_header_and_total(
        self,
        mock_echo_info,
    ) -> None:
        """List-only helper should emit the header, entries, and total."""
        emit_run_all_listing(
            source="chembl",
            pipelines=["chembl_activity", "chembl_assay"],
        )

        calls = [call.args[0] for call in mock_echo_info.call_args_list]
        assert calls[0] == "Pipelines for provider 'chembl':"
        assert "  - chembl_activity" in calls
        assert calls[-1] == "\nTotal: 2 pipeline(s)"


# =============================================================================
# CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllCommand:
    """Tests for run-all Click command."""

    def test_run_all_command__run_all_help__8625aed8(self, cli_runner):
        """Test that run-all --help works."""
        result = cli_runner.invoke(cli, ["run-all", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--run-type" in result.output
        assert "--list-only" in result.output
        assert "--dry-run" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_command__all_requires_source__ec5a5820(
        self, mock_register, cli_runner
    ):
        """Test that --source is required."""
        result = cli_runner.invoke(cli, ["run-all"])
        assert result.exit_code != 0
        assert "Missing option '--source'" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_list_only_shows_pipelines(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that --list-only shows pipelines without executing."""
        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--list-only"]
        )
        assert result.exit_code == 0
        assert "Pipelines for provider 'chembl':" in result.output
        assert "chembl_activity" in result.output
        assert "chembl_assay" in result.output
        assert "Total: 4 pipeline(s)" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_invalid_source_fails(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that invalid source shows error and exits with code 1."""
        result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])
        assert result.exit_code == 1
        assert "No pipelines found for provider 'invalid'" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_executes_all_pipelines(
        self, mock_asyncio, mock_register, cli_runner, mock_registry
    ):
        """Test that all pipelines for source are executed."""
        # Mock asyncio.run to return BatchRunResult directly
        mock_asyncio.return_value = BatchRunResult(
            total=4,
            succeeded=4,
            failed=0,
            results=[
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name=f"chembl_{entity}",
                    run_id="test-run-id",
                    run_type="incremental",
                )
                for entity in ["activity", "assay", "molecule", "target"]
            ],
        )

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])

        # Verify asyncio.run was called
        mock_asyncio.assert_called_once()
        assert "Running 4 pipeline(s)" in result.output
        assert result.exit_code == 0

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_dry_run_mode(
        self, mock_asyncio, mock_register, cli_runner, mock_registry
    ):
        """Test that --dry-run mode shows pipelines without executing."""
        # Mock asyncio.run to return BatchRunResult with skipped pipelines
        mock_asyncio.return_value = BatchRunResult(
            total=4,
            succeeded=0,
            failed=0,
            skipped=4,
            results=[
                RunResult(
                    status=PipelineRunResult.DRY_RUN,
                    pipeline_name=f"chembl_{entity}",
                    run_id="test-run-id",
                    run_type="incremental",
                )
                for entity in ["activity", "assay", "molecule", "target"]
            ],
        )

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_run_all_rebuild_requires_confirmation(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test that rebuild requires confirmation without --yes."""
        result = cli_runner.invoke(
            cli,
            ["run-all", "--source", "chembl", "--run-type", "rebuild"],
            input="n\n",  # Say no to confirmation
        )

        assert "Operation cancelled" in result.output

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_rebuild_with_yes_skips_confirmation(
        self, mock_asyncio, mock_register, cli_runner, mock_registry
    ):
        """Test that --yes skips confirmation for rebuild."""
        # Mock asyncio.run to return BatchRunResult directly
        mock_asyncio.return_value = BatchRunResult(
            total=4,
            succeeded=4,
            failed=0,
            results=[
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name=f"chembl_{entity}",
                    run_id="test-run-id",
                    run_type="rebuild",
                )
                for entity in ["activity", "assay", "molecule", "target"]
            ],
        )

        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--run-type", "rebuild", "--yes"]
        )

        # Should have called asyncio.run (no confirmation prompt)
        mock_asyncio.assert_called_once()
        assert result.exit_code == 0


# =============================================================================
# Exit Code Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllExitCodes:
    """Tests for run-all exit codes."""

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_exit_code_0_for_list_only(self, mock_register, cli_runner, mock_registry):
        """Test exit code 0 for successful --list-only."""
        result = cli_runner.invoke(
            cli, ["run-all", "--source", "chembl", "--list-only"]
        )
        assert result.exit_code == 0

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    def test_exit_code_1_for_invalid_source(
        self, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 1 for invalid source."""
        result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])
        assert result.exit_code == 1

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_exit_code_0_for_all_success(
        self, mock_asyncio, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 0 when all pipelines succeed."""
        # Mock asyncio.run to return BatchRunResult with all success
        mock_asyncio.return_value = BatchRunResult(
            total=4,
            succeeded=4,
            failed=0,
            results=[
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name=f"chembl_{entity}",
                    run_id="test-run-id",
                    run_type="incremental",
                )
                for entity in ["activity", "assay", "molecule", "target"]
            ],
        )

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])
        assert result.exit_code == 0

    @patch("bioetl.interfaces.cli.main.register_all_pipelines")
    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_exit_code_82_for_failures(
        self, mock_asyncio, mock_register, cli_runner, mock_registry
    ):
        """Test exit code 82 (PIPELINE_ERROR) when some pipelines fail."""
        # Mock asyncio.run to return BatchRunResult with one failure
        mock_asyncio.return_value = BatchRunResult(
            total=4,
            succeeded=3,
            failed=1,
            failed_pipelines=["chembl_assay"],
            results=[
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name="chembl_activity",
                    run_id="test-run-id",
                    run_type="incremental",
                ),
                RunResult(
                    status=PipelineRunResult.FAILED,
                    pipeline_name="chembl_assay",
                    run_id="test-run-id",
                    run_type="incremental",
                    error_message="Test error",
                ),
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name="chembl_molecule",
                    run_id="test-run-id",
                    run_type="incremental",
                ),
                RunResult(
                    status=PipelineRunResult.SUCCESS,
                    pipeline_name="chembl_target",
                    run_id="test-run-id",
                    run_type="incremental",
                ),
            ],
        )

        result = cli_runner.invoke(cli, ["run-all", "--source", "chembl"])
        assert result.exit_code == 82  # ExitCode.PIPELINE_ERROR
