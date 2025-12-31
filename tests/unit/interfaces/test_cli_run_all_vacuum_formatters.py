"""Unit tests for CLI run-all, vacuum-all commands and formatters.

Tests for:
- run-all command: batch execution of all pipelines for a provider
- vacuum-all command: batch vacuum of all Delta tables
- formatters: output formatting utilities
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from bioetl.application.services import (
    TableVacuumResult,
    VacuumAllResult,
)
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.commands.run_all import (
    BatchRunResult,
    _determine_exit_code,
    _echo_batch_summary,
    _filter_pipelines_by_provider,
    _get_available_providers,
    _handle_destructive_confirmation,
    _validate_provider,
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

if TYPE_CHECKING:
    pass


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
    return mock


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

    def test_default_values(self):
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
    """Tests for _get_available_providers helper."""

    def test_returns_unique_providers(self, mock_registry):
        """Test that unique providers are extracted from pipeline names."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            providers = _get_available_providers()

        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert len(providers) == 3  # chembl, pubchem, uniprot

    def test_returns_sorted_providers(self, mock_registry):
        """Test that providers are sorted alphabetically."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            providers = _get_available_providers()

        assert providers == sorted(providers)

    def test_returns_empty_list_when_no_pipelines(self):
        """Test that empty list is returned when no pipelines registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock,
        ):
            providers = _get_available_providers()

        assert providers == []


@pytest.mark.unit
class TestFilterPipelinesByProvider:
    """Tests for _filter_pipelines_by_provider helper."""

    def test_filters_by_provider_prefix(self, mock_registry):
        """Test that pipelines are filtered by provider prefix."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            pipelines = _filter_pipelines_by_provider("chembl")

        assert "chembl_activity" in pipelines
        assert "chembl_molecule" in pipelines
        assert "pubchem_compound" not in pipelines
        assert len(pipelines) == 2

    def test_returns_empty_for_unknown_provider(self, mock_registry):
        """Test that empty list is returned for unknown provider."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            pipelines = _filter_pipelines_by_provider("unknown")

        assert pipelines == []

    def test_returns_sorted_pipelines(self, mock_registry):
        """Test that pipelines are sorted alphabetically."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            pipelines = _filter_pipelines_by_provider("chembl")

        assert pipelines == sorted(pipelines)


@pytest.mark.unit
class TestValidateProvider:
    """Tests for _validate_provider helper."""

    def test_valid_provider_returns_true(self, mock_registry):
        """Test that valid provider returns (True, None)."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            is_valid, error_msg = _validate_provider("chembl")

        assert is_valid is True
        assert error_msg is None

    def test_invalid_provider_returns_false(self, mock_registry):
        """Test that invalid provider returns (False, error_message)."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            is_valid, error_msg = _validate_provider("invalid")

        assert is_valid is False
        assert "No pipelines found for provider 'invalid'" in error_msg
        assert "Available providers:" in error_msg

    def test_no_pipelines_registered(self):
        """Test error when no pipelines are registered."""
        mock = MagicMock()
        mock.list_pipelines.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock,
        ):
            is_valid, error_msg = _validate_provider("chembl")

        assert is_valid is False
        assert "No pipelines are registered" in error_msg


@pytest.mark.unit
class TestDetermineExitCode:
    """Tests for _determine_exit_code helper."""

    def test_ok_when_all_succeeded(self):
        """Test ExitCode.OK when all pipelines succeeded."""
        result = BatchRunResult(total=3, succeeded=3, failed=0, skipped=0)
        assert _determine_exit_code(result) == ExitCode.OK

    def test_pipeline_error_when_failures(self):
        """Test ExitCode.PIPELINE_ERROR when there are failures."""
        result = BatchRunResult(total=3, succeeded=1, failed=2, skipped=0)
        assert _determine_exit_code(result) == ExitCode.PIPELINE_ERROR

    def test_ok_when_all_skipped_no_failures(self):
        """Test ExitCode.OK when all skipped but no failures (considered success)."""
        # Per the logic: all_succeeded = (failed == 0) and (total > 0)
        # Skipped pipelines don't count as failures
        result = BatchRunResult(total=3, succeeded=0, failed=0, skipped=3)
        assert _determine_exit_code(result) == ExitCode.OK

    def test_sigint_when_no_total(self):
        """Test ExitCode.SIGINT when total is 0 (all_succeeded is False)."""
        result = BatchRunResult(total=0, succeeded=0, failed=0, skipped=0)
        assert _determine_exit_code(result) == ExitCode.SIGINT


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

        with patch(
            "bioetl.interfaces.cli.commands.run_all.echo_info"
        ) as mock_info, patch(
            "bioetl.interfaces.cli.commands.run_all.echo_error"
        ) as mock_error:
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
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(cli, ["run-all", "--source", "invalid"])

        assert result.exit_code != 0
        assert "No pipelines found" in result.output or "error" in result.output.lower()

    def test_run_all_list_only(self, cli_runner, mock_registry):
        """Test --list-only shows pipelines without running."""
        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--list-only"]
            )

        assert result.exit_code == 0
        assert "chembl_activity" in result.output
        assert "chembl_molecule" in result.output
        assert "2 pipeline(s)" in result.output

    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_dry_run(self, mock_asyncio_run, cli_runner, mock_registry):
        """Test --dry-run mode shows preview."""
        mock_asyncio_run.return_value = BatchRunResult(
            total=2, succeeded=0, failed=0, skipped=2
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output or "Would run" in result.output

    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_success(self, mock_asyncio_run, cli_runner, mock_registry):
        """Test successful run-all execution."""
        mock_asyncio_run.return_value = BatchRunResult(
            total=2, succeeded=2, failed=0, skipped=0
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--yes"]
            )

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_with_limit(self, mock_asyncio_run, cli_runner, mock_registry):
        """Test run-all with --limit option."""
        mock_asyncio_run.return_value = BatchRunResult(
            total=2, succeeded=2, failed=0, skipped=0
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--limit", "100", "--yes"]
            )

        assert result.exit_code == 0
        mock_asyncio_run.assert_called_once()

    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_with_failures(self, mock_asyncio_run, cli_runner, mock_registry):
        """Test run-all with some failures."""
        mock_asyncio_run.return_value = BatchRunResult(
            total=2,
            succeeded=1,
            failed=1,
            skipped=0,
            failed_pipelines=["chembl_activity"],
        )

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--yes"]
            )

        # Should exit with pipeline error code
        assert result.exit_code == ExitCode.PIPELINE_ERROR

    @patch("bioetl.interfaces.cli.commands.run_all.asyncio.run")
    def test_run_all_keyboard_interrupt(
        self, mock_asyncio_run, cli_runner, mock_registry
    ):
        """Test run-all handles KeyboardInterrupt."""
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        with patch(
            "bioetl.interfaces.cli.commands.run_all.get_default_registry",
            return_value=mock_registry,
        ):
            result = cli_runner.invoke(
                cli, ["run-all", "--source", "chembl", "--yes"]
            )

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

    def test_vacuum_all_success(self, cli_runner, mock_vacuum_service):
        """Test successful vacuum-all execution."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("all")

    def test_vacuum_all_dry_run(self, cli_runner, mock_vacuum_service):
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

    def test_format_bytes_gb(self):
        """Test formatting gigabytes."""
        assert format_bytes(1024**3) == "1.00 GB"
        assert format_bytes(2 * 1024**3) == "2.00 GB"
        assert format_bytes(1536 * 1024**2) == "1.50 GB"

    def test_format_bytes_mb(self):
        """Test formatting megabytes."""
        assert format_bytes(1024**2) == "1.00 MB"
        assert format_bytes(512 * 1024**2) == "512.00 MB"

    def test_format_bytes_kb(self):
        """Test formatting kilobytes."""
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(2048) == "2.00 KB"

    def test_format_bytes_small(self):
        """Test formatting bytes under 1KB."""
        assert format_bytes(0) == "0 bytes"
        assert format_bytes(500) == "500 bytes"
        assert format_bytes(1023) == "1023 bytes"


@pytest.mark.unit
class TestEchoFunctions:
    """Tests for echo_* formatter functions."""

    def test_echo_info(self, cli_runner):
        """Test echo_info outputs to stdout."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_info("Test message")), []
        )
        assert "Test message" in result.output
        assert result.exit_code == 0

    def test_echo_warning(self, cli_runner):
        """Test echo_warning outputs with WARNING prefix."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_warning("Test warning")), []
        )
        assert "WARNING:" in result.output
        assert "Test warning" in result.output

    def test_echo_error_with_detail(self, cli_runner):
        """Test echo_error with detail outputs to stderr."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_error("Error message", "Detail")), []
        )
        assert "Error message: Detail" in result.output

    def test_echo_error_without_detail(self, cli_runner):
        """Test echo_error without detail."""
        result = cli_runner.invoke(
            click.command()(lambda: echo_error("Error only")), []
        )
        assert "Error only" in result.output

    def test_echo_dry_run_prefix(self, cli_runner):
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
        record = {"error_code": "VALIDATION_ERROR", "payload": '{"id": 1}'}
        result = cli_runner.invoke(
            click.command()(lambda: echo_quarantine_record(record)), []
        )
        assert "VALIDATION_ERROR" in result.output
        assert '{"id": 1}' in result.output

    def test_echo_quarantine_record_with_defaults(self, cli_runner):
        """Test echo_quarantine_record with missing fields."""
        record = {}
        result = cli_runner.invoke(
            click.command()(lambda: echo_quarantine_record(record)), []
        )
        assert "UNKNOWN" in result.output
        assert "N/A" in result.output


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
