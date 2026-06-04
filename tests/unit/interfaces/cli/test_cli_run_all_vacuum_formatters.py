"""Unit tests for CLI run-all, vacuum-all commands and formatters.

Tests for:
- run-all command: batch execution of all pipelines for a provider
- vacuum-all command: batch vacuum of all Delta tables
- formatters: output formatting utilities
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from bioetl.application.services.execution.pipeline_runner_models import (
    PipelineRunResult,
    RunResult,
)
from bioetl.application.services.vacuum_service import (
    TableVacuumResult,
    VacuumAllResult,
)
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.commands.domains.health.observability_backend_runtime import (
    ObservabilityBackendEnsureResult,
)
from bioetl.interfaces.cli.commands.run_all import (
    BatchRunResult,
    _echo_batch_summary,
    _handle_destructive_confirmation,
)
from bioetl.interfaces.cli.commands.domains.run_all.support import (
    determine_batch_exit_code,
    filter_pipelines_by_provider,
    get_available_providers,
    validate_provider,
)
from bioetl.interfaces.cli.exit_codes import ExitCode
from bioetl.interfaces.cli.formatters import (
    echo_checkpoint,
    echo_dry_run_prefix,
    echo_error,
    echo_info,
    echo_quarantine_record,
    echo_vacuum_all_summary,
    echo_vacuum_result,
    echo_warning,
    format_bytes,
)


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_registry():
    """Mock registry with chembl and pubchem pipelines."""
    mock = MagicMock()
    mock.list_pipelines.return_value = [
        "chembl_activity",
        "chembl_molecule",
        "pubchem_compound",
        "uniprot_protein",
    ]
    with patch(
        "bioetl.interfaces.cli.commands.run_all.resolve_context_registry",
        return_value=mock,
    ):
        yield mock


@pytest.fixture(autouse=True)
def mock_run_all_observability_backend():
    """Prevent run-all unit tests from probing a real detached backend."""
    with (
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
        yield


# =============================================================================
# BatchRunResult Dataclass Tests
# =============================================================================


@pytest.mark.unit
class TestBatchRunResult:
    """Tests for BatchRunResult dataclass."""

    def test_all_succeeded_true_when_no_failures(self):
        """Test that all_succeeded is True when no pipelines failed."""
        result = BatchRunResult(total=3, succeeded=3, failed=0, skipped=0)
        assert result.all_succeeded is True

    def test_all_succeeded_false_when_failures(self):
        """Test that all_succeeded is False when there are failures."""
        result = BatchRunResult(total=3, succeeded=1, failed=2, skipped=0)
        assert result.all_succeeded is False

    def test_all_succeeded_false_when_no_pipelines(self):
        """Test that all_succeeded is False when total is 0."""
        result = BatchRunResult(total=0, succeeded=0, failed=0, skipped=0)
        assert result.all_succeeded is False

    def test_batch_run_result__default_values__8e271d6c(self):
        """Test default values for BatchRunResult."""
        result = BatchRunResult()
        assert result.total == 0
        assert result.succeeded == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.results == []
        assert result.failed_pipelines == []


# =============================================================================
# run_all Helper Function Tests
# =============================================================================


@pytest.mark.unit
class TestGetAvailableProviders:
    """Tests for get_available_providers helper."""

    def test_returns_unique_providers(self, mock_registry):
        """Test that unique providers are extracted from pipeline names."""
        providers = get_available_providers(registry=mock_registry)

        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert len(providers) == 3  # chembl, pubchem, uniprot

    def test_returns_sorted_providers(self, mock_registry):
        """Test that providers are sorted alphabetically."""
        providers = get_available_providers(registry=mock_registry)

        assert providers == sorted(providers)

    def test_returns_empty_list_when_no_pipelines(self):
        """Test that empty list is returned when no pipelines registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        providers = get_available_providers(registry=mock)

        assert providers == []


@pytest.mark.unit
class TestFilterPipelinesByProvider:
    """Tests for filter_pipelines_by_provider helper."""

    def test_filters_by_provider_prefix(self, mock_registry):
        """Test that pipelines are filtered by provider prefix."""
        pipelines = filter_pipelines_by_provider("chembl", registry=mock_registry)

        assert "chembl_activity" in pipelines
        assert "chembl_molecule" in pipelines
        assert "pubchem_compound" not in pipelines
        assert len(pipelines) == 2

    def test_returns_empty_for_unknown_provider(self, mock_registry):
        """Test that empty list is returned for unknown provider."""
        pipelines = filter_pipelines_by_provider("unknown", registry=mock_registry)

        assert pipelines == []

    def test_returns_sorted_pipelines(self, mock_registry):
        """Test that pipelines are sorted alphabetically."""
        pipelines = filter_pipelines_by_provider("chembl", registry=mock_registry)

        assert pipelines == sorted(pipelines)


@pytest.mark.unit
class TestValidateProvider:
    """Tests for validate_provider helper."""

    def test_valid_provider_returns_true(self, mock_registry):
        """Test that valid provider returns (True, None)."""
        is_valid, error_msg = validate_provider("chembl", registry=mock_registry)

        assert is_valid is True
        assert error_msg is None

    def test_invalid_provider_returns_false(self, mock_registry):
        """Test that invalid provider returns (False, error_message)."""
        is_valid, error_msg = validate_provider("invalid", registry=mock_registry)

        assert is_valid is False
        assert "No pipelines found for provider 'invalid'" in error_msg
        assert "Available providers:" in error_msg

    def test_no_pipelines_registered(self):
        """Test error when no pipelines are registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []
        is_valid, error_msg = validate_provider("chembl", registry=mock)

        assert is_valid is False
        assert "No pipelines are registered" in error_msg


@pytest.mark.unit
class TestDetermineExitCode:
    """Tests for determine_batch_exit_code helper."""

    def test_ok_when_all_succeeded(self):
        """Test ExitCode.OK when all pipelines succeeded."""
        result = BatchRunResult(total=3, succeeded=3, failed=0, skipped=0)
        assert determine_batch_exit_code(result) == ExitCode.OK

    def test_pipeline_error_when_failures(self):
        """Test ExitCode.PIPELINE_ERROR when there are failures."""
        result = BatchRunResult(total=3, succeeded=1, failed=2, skipped=0)
        assert determine_batch_exit_code(result) == ExitCode.PIPELINE_ERROR

    def test_sigint_when_shutdown_present(self):
        """Test ExitCode.SIGINT when batch contains a shutdown status."""
        result = BatchRunResult(
            total=1,
            succeeded=0,
            failed=0,
            skipped=1,
            results=[
                RunResult(
                    status=PipelineRunResult.SHUTDOWN,
                    pipeline_name="chembl_activity",
                    run_id="test-run-id",
                    run_type="incremental",
                )
            ],
        )
        assert determine_batch_exit_code(result) == ExitCode.SIGINT

    def test_sigint_when_no_total(self):
        """Test ExitCode.SIGINT when total is 0 (all_succeeded is False)."""
        result = BatchRunResult(total=0, succeeded=0, failed=0, skipped=0)
        assert determine_batch_exit_code(result) == ExitCode.SIGINT


@pytest.mark.unit
class TestHandleDestructiveConfirmation:
    """Tests for _handle_destructive_confirmation helper."""

    def test_returns_true_for_incremental(self):
        """Test that incremental run skips confirmation."""
        result = _handle_destructive_confirmation(
            run_type="incremental",
            pipelines=["test"],
            dry_run=False,
            yes=False,
        )
        assert result is True

    def test_returns_true_for_dry_run(self):
        """Test that dry-run skips confirmation."""
        result = _handle_destructive_confirmation(
            run_type="rebuild",
            pipelines=["test"],
            dry_run=True,
            yes=False,
        )
        assert result is True

    def test_returns_true_with_yes_flag(self):
        """Test that --yes flag skips confirmation."""
        result = _handle_destructive_confirmation(
            run_type="rebuild",
            pipelines=["test"],
            dry_run=False,
            yes=True,
        )
        assert result is True

    @patch("bioetl.interfaces.cli.commands.run_all.click.confirm", return_value=True)
    def test_prompts_for_rebuild(self, mock_confirm):
        """Test that rebuild prompts for confirmation."""
        result = _handle_destructive_confirmation(
            run_type="rebuild",
            pipelines=["test_pipeline"],
            dry_run=False,
            yes=False,
        )
        assert result is True
        mock_confirm.assert_called_once()


@pytest.mark.unit
class TestEchoBatchSummary:
    """Tests for _echo_batch_summary helper."""

    def test_dry_run_summary(self, cli_runner):
        """Test batch summary output in dry-run mode."""
        result = BatchRunResult(total=3, succeeded=0, failed=0, skipped=0)

        with patch("bioetl.interfaces.cli.commands.run_all.echo_info") as mock_echo:
            _echo_batch_summary(result, dry_run=True)

        # Check that dry-run message was included
        calls = [str(call) for call in mock_echo.call_args_list]
        assert any("Dry-run" in str(c) for c in calls)

    def test_execution_summary_with_failures(self):
        """Test batch summary output with failures."""
        result = BatchRunResult(
            total=3,
            succeeded=1,
            failed=2,
            skipped=0,
            failed_pipelines=["pipeline_a", "pipeline_b"],
        )

        with (
            patch("bioetl.interfaces.cli.commands.run_all.echo_info") as mock_info,
            patch("bioetl.interfaces.cli.commands.run_all.echo_error") as mock_error,
        ):
            _echo_batch_summary(result, dry_run=False)

        # Check that failure count was output
        info_calls = [str(call) for call in mock_info.call_args_list]
        assert any("Failed" in str(c) for c in info_calls)

        # Check that failed pipelines were listed
        mock_error.assert_called_once()


# =============================================================================
# run-all CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestRunAllCommand:
    """Tests for run-all CLI command."""

    def test_run_all_help(self, cli_runner):
        """Test that run-all --help works."""
        result = cli_runner.invoke(cli, ["run-all", "--help"])

        assert result.exit_code == 0
        assert "--source" in result.output
        assert "--run-type" in result.output
        assert "--dry-run" in result.output
        assert "--yes" in result.output
        assert "--list-only" in result.output

    def test_run_all_requires_source(self, cli_runner):
        """Test that --source is required."""
        result = cli_runner.invoke(cli, ["run-all"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "--source" in result.output

    def test_run_all_invalid_provider(self, cli_runner, mock_registry):
        """Test error for invalid provider."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])

        assert result.exit_code != 0
        assert "No pipelines found" in result.output or "error" in result.output.lower()

    def test_run_all_list_only(self, cli_runner, mock_registry):
        """Test --list-only shows pipelines without running."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--list-only"]
            )

        assert result.exit_code == 0
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output
        assert "2 pipeline(s)" in result.output

    def test_run_all_dry_run(self, cli_runner, mock_registry):
        """Test --dry-run mode shows preview."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                return_value=BatchRunResult(total=2, succeeded=0, failed=0, skipped=2),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output or "Would run" in result.output

    def test_run_all_success(self, cli_runner, mock_registry):
        """Test successful run-all execution."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                return_value=BatchRunResult(total=2, succeeded=2, failed=0, skipped=0),
            ) as mock_asyncio_run,
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "chembl", "--yes"])

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    def test_run_all_with_limit(self, cli_runner, mock_registry):
        """Test run-all with --limit option."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                return_value=BatchRunResult(total=2, succeeded=2, failed=0, skipped=0),
            ) as mock_asyncio_run,
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--limit", "100", "--yes"]
            )

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    def test_run_all_with_failures(self, cli_runner, mock_registry):
        """Test run-all with some failures."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                return_value=BatchRunResult(
                    total=2,
                    succeeded=1,
                    failed=1,
                    skipped=0,
                    failed_pipelines=["chembl_activity"],
                ),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "chembl", "--yes"])

        # Should exit with pipeline error code
        assert result.exit_code == ExitCode.PIPELINE_ERROR

    def test_run_all_keyboard_interrupt(self, cli_runner, mock_registry):
        """Test run-all handles KeyboardInterrupt."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                side_effect=KeyboardInterrupt(),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "chembl", "--yes"])

        assert result.exit_code == ExitCode.SIGINT
        assert "interrupted" in result.output.lower()


# =============================================================================
# vacuum-all CLI Command Tests
# =============================================================================


@pytest.mark.unit
class TestVacuumAllCommand:
    """Tests for vacuum-all CLI command."""

    def test_vacuum_all_help(self, cli_runner):
        """Test that vacuum-all --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--help"])

        assert result.exit_code == 0
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output
        assert "--layer" in result.output

    @pytest.fixture
    def mock_vacuum_service(self):
        """Create a mock vacuum service."""
        service = MagicMock()
        service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
            ("chembl_activity", "gold"),
        ]
        service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult(
                        table_name="chembl_activity",
                        layer="silver",
                        files_removed=10,
                        error=None,
                    ),
                    TableVacuumResult(
                        table_name="chembl_activity",
                        layer="gold",
                        files_removed=5,
                        error=None,
                    ),
                ),
                dry_run=False,
            )
        )
        return service

    def test_vacuum_all_command__vacuum_all_success__339b42b3(
        self, cli_runner, mock_vacuum_service
    ):
        """Test successful vacuum-all execution."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("all")

    def test_vacuum_all_command__vacuum_all_dry_run__02dc303f(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all with --dry-run."""
        mock_vacuum_service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult(
                        table_name="chembl_activity",
                        layer="silver",
                        files_removed=10,
                        error=None,
                    ),
                ),
                dry_run=True,
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output or "Would" in result.output

    def test_vacuum_all_with_retention(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all with custom retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--retention-days", "30"]
            )

        assert result.exit_code == 0
        # Verify retention was passed
        call_args = mock_vacuum_service.vacuum_all.call_args
        assert call_args[1]["retention_days"] == 30

    def test_vacuum_all_silver_only(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all with --layer silver."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--layer", "silver"]
            )

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("silver")

    def test_vacuum_all_gold_only(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all with --layer gold."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--layer", "gold"]
            )

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("gold")

    def test_vacuum_all_no_tables(self, cli_runner):
        """Test vacuum-all when no tables found."""
        mock_service = MagicMock()
        mock_service.collect_tables.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "No tables found" in result.output

    def test_vacuum_all_with_errors(self, cli_runner):
        """Test vacuum-all with table errors."""
        mock_service = MagicMock()
        mock_service.collect_tables.return_value = [("bad_table", "silver")]
        mock_service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult(
                        table_name="bad_table",
                        layer="silver",
                        files_removed=0,
                        error="Table not found",
                    ),
                ),
                dry_run=False,
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "Error" in result.output or "error" in result.output.lower()


# =============================================================================
# Formatters Tests
# =============================================================================


@pytest.mark.unit
class TestFormatBytes:
    """Tests for format_bytes formatter."""

    def test_format_bytes__format_bytes_gb__1f38e53b(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024**3) == "1.00 GB"
        assert format_bytes(2 * 1024**3) == "2.00 GB"
        assert format_bytes(1536 * 1024**2) == "1.50 GB"

    def test_format_bytes__format_bytes_mb__8fefedc9(self):
        """Test formatting megabytes."""
        assert format_bytes(1024**2) == "1.00 MB"
        assert format_bytes(512 * 1024**2) == "512.00 MB"

    def test_format_bytes__format_bytes_kb__75acd4ef(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(2048) == "2.00 KB"

    def test_format_bytes__format_bytes_small__fa76e3e8(self):
        """Test formatting bytes under 1KB."""
        assert format_bytes(0) == "0 bytes"
        assert format_bytes(500) == "500 bytes"
        assert format_bytes(1023) == "1023 bytes"


@pytest.mark.unit
class TestEchoFunctions:
    """Tests for echo_* formatter functions."""

    def test_echo_functions__echo_info__7d8435dc(self, cli_runner):
        """Test echo_info outputs to stdout."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_info("Test message")), []
        )
        assert "Test message" in result.output
        assert result.exit_code == 0

    def test_echo_functions__echo_warning__3dc6a7f8(self, cli_runner):
        """Test echo_warning outputs with WARNING prefix."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_warning("Test warning")), []
        )
        assert "WARNING:" in result.output
        assert "Test warning" in result.output

    def test_echo_functions__error_with_detail__2bc46930(self, cli_runner):
        """Test echo_error with detail outputs to stderr."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_error("Error message", "Detail")), []
        )
        assert "Error message: Detail" in result.output

    def test_echo_functions__error_without_detail__ae867a7d(self, cli_runner):
        """Test echo_error without detail."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_error("Error only")), []
        )
        assert "Error only" in result.output

    def test_echo_functions__echo_dry_run_prefix__5b07499e(self, cli_runner):
        """Test echo_dry_run_prefix adds [DRY-RUN] prefix."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_dry_run_prefix("Would do something")), []
        )
        assert "[DRY-RUN]" in result.output
        assert "Would do something" in result.output

    def test_echo_checkpoint(self, cli_runner):
        """Test echo_checkpoint formats checkpoint entry."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_checkpoint("checkpoint-123")), []
        )
        assert "- checkpoint-123" in result.output

    def test_echo_quarantine_record(self, cli_runner):
        """Test echo_quarantine_record formats record."""
        record = {
            "error_code": "FILTERED_OUT_SILVER",
            "payload_hash": "abc123def4567890abc123def4567890",
            "dq_status": "NEW",
            "payload": '{"id": 1}',
            "error_details": {
                "message": "Missing required field",
                "reason_code": "missing_required_field",
                "field": "publication_year",
                "rule_type": "required_fields",
            },
        }
        result = cli_runner.invoke(
            click.command()(lambda: echo_quarantine_record(record)), []
        )
        assert "FILTERED_OUT_SILVER" in result.output
        assert "Reason: Missing required field" in result.output
        assert "Reason Code: missing_required_field" in result.output
        assert "Field: publication_year" in result.output
        assert '{"id": 1}' in result.output

    def test_echo_quarantine_record_with_defaults(self, cli_runner):
        """Test echo_quarantine_record with missing fields uses proper None handling."""
        record = {}
        result = cli_runner.invoke(
            click.command()(lambda: echo_quarantine_record(record)), []
        )
        assert "UNKNOWN" in result.output
        assert "Status: UNKNOWN" in result.output
        assert "—" in result.output


@pytest.mark.unit
class TestVacuumFormatters:
    """Tests for vacuum-related formatters."""

    def test_echo_vacuum_result_success(self, cli_runner):
        """Test echo_vacuum_result for successful vacuum."""
        result_data = TableVacuumResult(
            table_name="chembl_activity",
            layer="silver",
            files_removed=42,
            error=None,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_result(result_data, dry_run=False)), []
        )

        assert "silver/chembl_activity" in result.output
        assert "42" in result.output
        assert "Removed" in result.output or "Vacuuming" in result.output

    def test_echo_vacuum_result_dry_run(self, cli_runner):
        """Test echo_vacuum_result in dry-run mode."""
        result_data = TableVacuumResult(
            table_name="chembl_activity",
            layer="gold",
            files_removed=10,
            error=None,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_result(result_data, dry_run=True)), []
        )

        assert "[DRY-RUN]" in result.output
        assert "Would" in result.output

    def test_echo_vacuum_result_with_error(self, cli_runner):
        """Test echo_vacuum_result with error."""
        result_data = TableVacuumResult(
            table_name="bad_table",
            layer="silver",
            files_removed=0,
            error="Table not found",
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_result(result_data, dry_run=False)), []
        )

        assert "Error" in result.output
        assert "Table not found" in result.output

    def test_echo_vacuum_all_summary(self, cli_runner):
        """Test echo_vacuum_all_summary output."""
        vacuum_result = VacuumAllResult(
            results=(
                TableVacuumResult(
                    table_name="table1",
                    layer="silver",
                    files_removed=10,
                    error=None,
                ),
                TableVacuumResult(
                    table_name="table2",
                    layer="gold",
                    files_removed=5,
                    error=None,
                ),
            ),
            dry_run=False,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_all_summary(vacuum_result)), []
        )

        assert "15" in result.output  # Total files
        assert "removed" in result.output.lower()

    def test_echo_vacuum_all_summary_dry_run(self, cli_runner):
        """Test echo_vacuum_all_summary in dry-run mode."""
        vacuum_result = VacuumAllResult(
            results=(
                TableVacuumResult(
                    table_name="table1",
                    layer="silver",
                    files_removed=20,
                    error=None,
                ),
            ),
            dry_run=True,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_all_summary(vacuum_result)), []
        )

        assert "would remove" in result.output.lower()

    def test_echo_vacuum_all_summary_with_failures(self, cli_runner):
        """Test echo_vacuum_all_summary with failed tables."""
        vacuum_result = VacuumAllResult(
            results=(
                TableVacuumResult(
                    table_name="good_table",
                    layer="silver",
                    files_removed=10,
                    error=None,
                ),
                TableVacuumResult(
                    table_name="bad_table",
                    layer="gold",
                    files_removed=0,
                    error="Failed",
                ),
            ),
            dry_run=False,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_vacuum_all_summary(vacuum_result)), []
        )

        assert "Failed tables" in result.output
        assert "gold/bad_table" in result.output


# =============================================================================
# echo_cleanup_preview Tests
# =============================================================================


@pytest.mark.unit
class TestEchoCleanupPreview:
    """Tests for echo_cleanup_preview formatter."""

    def test_echo_cleanup_preview_with_existing_layers(self, cli_runner):
        """Test echo_cleanup_preview when both layers exist."""
        from bioetl.application.core.lifecycle.cleanup_service import (
            CleanupPreview,
            LayerInfo,
        )
        from bioetl.interfaces.cli.formatters import echo_cleanup_preview

        preview = CleanupPreview(
            silver=LayerInfo(path="/data/silver/test", file_count=10, exists=True),
            gold=LayerInfo(path="/data/gold/test", file_count=5, exists=True),
            total_files=15,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_cleanup_preview(preview)), []
        )

        assert "/data/silver/test" in result.output
        assert "10 files" in result.output
        assert "/data/gold/test" in result.output
        assert "5 files" in result.output
        assert "15" in result.output
        assert "dry-run" in result.output.lower()

    def test_echo_cleanup_preview_with_non_existing_silver(self, cli_runner):
        """Test echo_cleanup_preview when silver doesn't exist."""
        from bioetl.application.core.lifecycle.cleanup_service import (
            CleanupPreview,
            LayerInfo,
        )
        from bioetl.interfaces.cli.formatters import echo_cleanup_preview

        preview = CleanupPreview(
            silver=LayerInfo(path="/data/silver/missing", file_count=0, exists=False),
            gold=None,
            total_files=0,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_cleanup_preview(preview)), []
        )

        assert "/data/silver/missing" in result.output
        assert "does not exist" in result.output

    def test_echo_cleanup_preview_with_non_existing_gold(self, cli_runner):
        """Test echo_cleanup_preview when gold doesn't exist."""
        from bioetl.application.core.lifecycle.cleanup_service import (
            CleanupPreview,
            LayerInfo,
        )
        from bioetl.interfaces.cli.formatters import echo_cleanup_preview

        preview = CleanupPreview(
            silver=LayerInfo(path="/data/silver/test", file_count=5, exists=True),
            gold=LayerInfo(path="/data/gold/missing", file_count=0, exists=False),
            total_files=5,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_cleanup_preview(preview)), []
        )

        assert "/data/silver/test" in result.output
        assert "5 files" in result.output
        assert "/data/gold/missing" in result.output
        assert "does not exist" in result.output

    def test_echo_cleanup_preview_without_gold(self, cli_runner):
        """Test echo_cleanup_preview when gold is None."""
        from bioetl.application.core.lifecycle.cleanup_service import (
            CleanupPreview,
            LayerInfo,
        )
        from bioetl.interfaces.cli.formatters import echo_cleanup_preview

        preview = CleanupPreview(
            silver=LayerInfo(path="/data/silver/only", file_count=8, exists=True),
            gold=None,
            total_files=8,
        )

        result = cli_runner.invoke(
            click.command()(lambda: echo_cleanup_preview(preview)), []
        )

        assert "/data/silver/only" in result.output
        assert "8 files" in result.output
        # Gold should not be mentioned when None
        assert "Gold:" not in result.output


# =============================================================================
# vacuum command Tests (single table)
# =============================================================================


@pytest.mark.unit
class TestVacuumCommand:
    """Tests for vacuum command (single table operation)."""

    def test_vacuum_help(self, cli_runner):
        """Test that vacuum --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum", "--help"])

        assert result.exit_code == 0
        assert "TABLE" in result.output
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output

    def test_vacuum_requires_table(self, cli_runner):
        """Test that TABLE argument is required."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "TABLE" in result.output

    def test_vacuum_command__vacuum_success__483931ec(self, cli_runner):
        """Test successful vacuum of single table."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.vacuum = AsyncMock(return_value=42)

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity"]
            )

        assert result.exit_code == 0
        assert "Removed 42 files" in result.output

    def test_vacuum_command__vacuum_dry_run__e00332a7(self, cli_runner):
        """Test vacuum with --dry-run."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.vacuum = AsyncMock(return_value=25)

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would remove 25 files" in result.output

    def test_vacuum_with_retention_days(self, cli_runner):
        """Test vacuum with custom retention days."""
        mock_lifecycle = MagicMock()
        mock_lifecycle.vacuum = AsyncMock(return_value=10)

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity", "-r", "30"]
            )

        assert result.exit_code == 0
        # Verify retention_days was passed
        call_kwargs = mock_lifecycle.vacuum.call_args[1]
        assert call_kwargs["retention_days"] == 30


# =============================================================================
# Additional run_all Tests for Coverage
# =============================================================================


@pytest.mark.unit
class TestRunAllPipelinesAsync:
    """Tests for _run_all_pipelines_async function."""

    @pytest.fixture(autouse=True)
    def mock_servers(self):
        """Mock health and metrics servers to prevent port binding."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.run_all.health_server_context",
                MagicMock(),
            ) as mock_health,
            patch(
                "bioetl.interfaces.cli.commands.run_all.ensure_metrics_server_started"
            ),
        ):
            # Setup async context manager mock
            mock_health.return_value.__aenter__.return_value = None
            mock_health.return_value.__aexit__.return_value = None
            yield

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_success(self):
        """Test _run_all_pipelines_async with successful run."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=PipelineRunResult.SUCCESS,
                pipeline_name="test_pipeline",
                run_id="test-run-123",
                run_type="incremental",
                records_fetched=100,
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=False)
            result = await _run_all_pipelines_async(["test_pipeline"], options)

        assert result.total == 1
        assert result.succeeded == 1
        assert result.failed == 0

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_dry_run_status(self):
        """Test _run_all_pipelines_async with DRY_RUN status."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=PipelineRunResult.DRY_RUN,
                pipeline_name="test_pipeline",
                run_id="test-run-123",
                run_type="incremental",
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=True)
            result = await _run_all_pipelines_async(["test_pipeline"], options)

        assert result.total == 1
        assert result.skipped == 1
        assert result.succeeded == 0

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_shutdown_status(self):
        """Test _run_all_pipelines_async stops on SHUTDOWN status."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=PipelineRunResult.SHUTDOWN,
                pipeline_name="pipeline1",
                run_id="test-run-123",
                run_type="incremental",
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=False)
            result = await _run_all_pipelines_async(
                ["pipeline1", "pipeline2", "pipeline3"], options
            )

        assert result.total == 3
        assert result.skipped == 1
        # Should break after shutdown, so only 1 call
        assert mock_service.run.call_count == 1

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_failed_status(self):
        """Test _run_all_pipelines_async with FAILED status."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
            RunResult,
            PipelineRunResult,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            return_value=RunResult(
                status=PipelineRunResult.FAILED,
                pipeline_name="failing_pipeline",
                run_id="test-run-123",
                run_type="incremental",
                error_message="Something went wrong",
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=False)
            result = await _run_all_pipelines_async(["failing_pipeline"], options)

        assert result.total == 1
        assert result.failed == 1
        assert "failing_pipeline" in result.failed_pipelines

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_not_found_error(self):
        """Test _run_all_pipelines_async with PipelineNotFoundError."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            PipelineNotFoundError,
            RunOptions,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(
            side_effect=PipelineNotFoundError("missing_pipeline", available=["other"])
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=False)
            result = await _run_all_pipelines_async(["missing_pipeline"], options)

        assert result.total == 1
        assert result.failed == 1
        assert "missing_pipeline" in result.failed_pipelines

    @pytest.mark.asyncio
    async def test_run_all_pipelines_handles_unexpected_exception(self):
        """Test _run_all_pipelines_async with unexpected exception."""
        from bioetl.application.services.execution.pipeline_runner_models import (
            RunOptions,
        )
        from bioetl.interfaces.cli.commands.run_all import _run_all_pipelines_async

        mock_service = MagicMock()
        mock_service.run = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_pipeline_runner_service",
            return_value=mock_service,
        ):
            options = RunOptions(run_type="incremental", dry_run=False)
            result = await _run_all_pipelines_async(["error_pipeline"], options)

        assert result.total == 1
        assert result.failed == 1
        assert "error_pipeline" in result.failed_pipelines


@pytest.mark.unit
class TestHandleDestructiveConfirmationCancel:
    """Tests for _handle_destructive_confirmation with user cancellation."""

    @patch("bioetl.interfaces.cli.commands.run_all.click.confirm", return_value=False)
    def test_confirmation_cancelled_by_user(self, mock_confirm):
        """Test that cancellation exits the program."""
        with pytest.raises(SystemExit) as exc_info:
            _handle_destructive_confirmation(
                run_type="rebuild",
                pipelines=["test_pipeline"],
                dry_run=False,
                yes=False,
            )

        assert exc_info.value.code == ExitCode.OK
        mock_confirm.assert_called_once()


@pytest.mark.unit
class TestRunAllCommandExceptions:
    """Tests for run_all command exception handling."""

    def test_run_all_unexpected_exception(self, cli_runner, mock_registry):
        """Test run-all handles unexpected exceptions during batch execution."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                side_effect=RuntimeError("Unexpected batch error"),
            ),
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "chembl", "--yes"])

        assert result.exit_code == ExitCode.FAIL
        assert "Unexpected error" in result.output or "error" in result.output.lower()

    def test_run_all_with_debug_flag(self, cli_runner, mock_registry):
        """Test run-all with --debug flag."""
        with (
            patch(
                "bioetl.interfaces.cli.commands.domains.run_all.public_runtime.asyncio.run",
                return_value=BatchRunResult(total=2, succeeded=2, failed=0, skipped=0),
            ) as mock_asyncio_run,
            patch(
                "bioetl.interfaces.cli.commands.run_all.build_cli_registry",
                return_value=mock_registry,
            ),
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--yes", "--debug"]
            )

        assert result.exit_code == 0
        # The async function is called, check that it was called
        mock_asyncio_run.assert_called_once()


@pytest.mark.unit
class TestEchoBatchSummarySkipped:
    """Tests for _echo_batch_summary with skipped pipelines."""

    def test_summary_with_skipped(self):
        """Test batch summary shows skipped count."""
        result = BatchRunResult(
            total=5,
            succeeded=3,
            failed=0,
            skipped=2,
        )

        with patch("bioetl.interfaces.cli.commands.run_all.echo_info") as mock_info:
            _echo_batch_summary(result, dry_run=False)

        calls = [str(call) for call in mock_info.call_args_list]
        assert any("Skipped" in str(c) for c in calls)
