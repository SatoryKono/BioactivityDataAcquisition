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
"""Unit tests for vacuum CLI commands with VacuumService mocking.

Tests the vacuum and vacuum-all commands with mocked VacuumService for:
- Positive scenarios (successful vacuum operations)
- Negative scenarios (service errors, failures)
- Dry-run mode
- CLI formatter output verification (echo_vacuum_result, echo_vacuum_all_summary)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.services.vacuum_service import (
    TableVacuumResult,
    VacuumAllResult,
)
from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_vacuum_service():
    """Create a mock VacuumService."""
    service = MagicMock()
    service.collect_tables = MagicMock()
    service.vacuum_all = AsyncMock()
    service.vacuum_table = AsyncMock()
    return service


@pytest.fixture
def mock_lifecycle_service():
    """Create a mock MedallionLifecycleService."""
    service = MagicMock()
    service.vacuum = AsyncMock(return_value=10)
    return service


def _create_table_result(
    table_name: str,
    layer: str = "silver",
    files_removed: int = 5,
    error: str | None = None,
) -> TableVacuumResult:
    """Helper to create TableVacuumResult objects."""
    return TableVacuumResult(
        table_name=table_name,
        layer=layer,
        files_removed=files_removed,
        error=error,
    )


def _create_vacuum_all_result(
    results: list[TableVacuumResult],
    dry_run: bool = False,
) -> VacuumAllResult:
    """Helper to create VacuumAllResult objects."""
    return VacuumAllResult(
        results=tuple(results),
        dry_run=dry_run,
    )


# =============================================================================
# vacuum Command Tests
# =============================================================================


@pytest.mark.unit
class TestVacuumCommand:
    """Tests for the vacuum command."""

    def test_vacuum_command__vacuum_help__73b0181b(self, cli_runner):
        """Test vacuum --help shows correct options."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum", "--help"])

        assert result.exit_code == 0
        assert "TABLE" in result.output
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output

    def test_vacuum_command__vacuum_success__47371b34(
        self, cli_runner, mock_lifecycle_service
    ):
        """Test successful vacuum operation."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity"]
            )

        assert result.exit_code == 0
        assert "10" in result.output  # files_removed
        assert "Removed" in result.output
        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=7,
            dry_run=False,
        )

    def test_vacuum_command__custom_retention__02c904ce(
        self, cli_runner, mock_lifecycle_service
    ):
        """Test vacuum with custom retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity", "-r", "30"]
            )

        assert result.exit_code == 0
        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=30,
            dry_run=False,
        )

    def test_vacuum_command__vacuum_dry_run__2913ed86(
        self, cli_runner, mock_lifecycle_service
    ):
        """Test vacuum dry-run mode."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "chembl.activity", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would" in result.output
        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=7,
            dry_run=True,
        )

    def test_vacuum_error_handling(self, cli_runner, mock_lifecycle_service):
        """Test vacuum handles service errors."""
        mock_lifecycle_service.vacuum.side_effect = RuntimeError("Table not found")

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum", "nonexistent.table"]
            )

        assert result.exit_code != 0


# =============================================================================
# vacuum-all Command Tests
# =============================================================================


@pytest.mark.unit
class TestVacuumAllCommand:
    """Tests for the vacuum-all command."""

    def test_vacuum_all_command__vacuum_all_help__4c45cb7d(self, cli_runner):
        """Test vacuum-all --help shows correct options."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--help"])

        assert result.exit_code == 0
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output
        assert "--layer" in result.output

    def test_vacuum_all_command__vacuum_all_success__e32d986c(
        self, cli_runner, mock_vacuum_service
    ):
        """Test successful vacuum-all operation."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
            ("chembl_activity", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("chembl_activity", "silver", 10),
                _create_table_result("chembl_activity", "gold", 5),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "15" in result.output  # total files removed
        mock_vacuum_service.collect_tables.assert_called_once_with("all")

    def test_vacuum_all_with_layer_filter(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all with layer filter."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[_create_table_result("chembl_activity", "silver", 10)]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--layer", "silver"]
            )

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("silver")

    def test_vacuum_all_command__vacuum_all_dry_run__8e4ee80b(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all dry-run mode."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[_create_table_result("chembl_activity", "silver", 10)],
            dry_run=True,
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would" in result.output

    def test_vacuum_all_command__vacuum_all_no_tables__3e63f89e(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all with no tables to vacuum."""
        mock_vacuum_service.collect_tables.return_value = []

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "No tables found" in result.output
        mock_vacuum_service.vacuum_all.assert_not_called()

    def test_vacuum_all_command__custom_retention__10e1b7a0(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all with custom retention days."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[_create_table_result("chembl_activity", "silver", 10)]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "-r", "14"])

        assert result.exit_code == 0
        mock_vacuum_service.vacuum_all.assert_called_once()
        call_args = mock_vacuum_service.vacuum_all.call_args
        assert call_args[1]["retention_days"] == 14


# =============================================================================
# Formatter Output Tests
# =============================================================================


@pytest.mark.unit
class TestVacuumFormatterOutput:
    """Tests for vacuum CLI formatter output verification."""

    def test_vacuum_all_shows_table_results(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all shows individual table results."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 10),
                _create_table_result("table2", "gold", 5),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "silver/table1" in result.output
        assert "gold/table2" in result.output

    def test_vacuum_all_shows_error_for_failed_tables(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all shows errors for failed tables."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 10),
                _create_table_result(
                    "table2", "gold", 0, error="Delta table corrupted"
                ),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "Error:" in result.output
        assert "Delta table corrupted" in result.output

    def test_vacuum_all_summary_shows_total(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all summary shows total files removed."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 10),
                _create_table_result("table2", "gold", 5),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "Total:" in result.output
        assert "15" in result.output

    def test_vacuum_all_summary_shows_failed_tables(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all summary lists failed tables."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 10),
                _create_table_result("table2", "gold", 0, error="Failed"),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "Failed tables:" in result.output
        assert "gold/table2" in result.output

    def test_formatter_output__shows_would_remove__687a48c2(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all dry-run shows 'would remove' in output."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[_create_table_result("table1", "silver", 10)],
            dry_run=True,
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert "Would" in result.output or "would" in result.output


# =============================================================================
# Negative Scenarios
# =============================================================================


@pytest.mark.unit
class TestVacuumNegativeScenarios:
    """Tests for vacuum command error handling."""

    def test_vacuum_all_partial_failure_continues(
        self, cli_runner, mock_vacuum_service
    ):
        """Test vacuum-all continues even if some tables fail."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "silver"),
            ("table3", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 10),
                _create_table_result("table2", "silver", 0, error="Failed"),
                _create_table_result("table3", "gold", 5),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        # Should complete successfully (exit 0) even with partial failures
        assert result.exit_code == 0
        # Should show summary with both successes and failures
        assert "15" in result.output  # 10 + 5 files removed
        assert "Failed tables:" in result.output

    def test_vacuum_all_handles_service_error(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all handles VacuumService exceptions."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
        ]
        mock_vacuum_service.vacuum_all.side_effect = RuntimeError("Service error")

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        # Should fail with non-zero exit code
        assert result.exit_code != 0

    def test_vacuum_all_with_all_failures(self, cli_runner, mock_vacuum_service):
        """Test vacuum-all when all tables fail."""
        mock_vacuum_service.collect_tables.return_value = [
            ("table1", "silver"),
            ("table2", "gold"),
        ]
        mock_vacuum_service.vacuum_all.return_value = _create_vacuum_all_result(
            results=[
                _create_table_result("table1", "silver", 0, error="Error 1"),
                _create_table_result("table2", "gold", 0, error="Error 2"),
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        # Still exits 0 (operation completed, just with failures)
        assert result.exit_code == 0
        assert "Failed tables:" in result.output


# =============================================================================
# Integration with formatters.py Functions
# =============================================================================


@pytest.mark.unit
class TestFormatterFunctions:
    """Direct tests for CLI formatter functions used by vacuum commands."""

    def test_formatter_functions__result_success__cbfc8b31(self, capsys):
        """Test echo_vacuum_result formats successful result correctly."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_result

        result = _create_table_result("test_table", "silver", 42)
        echo_vacuum_result(result, dry_run=False)

        captured = capsys.readouterr()
        assert "Vacuuming silver/test_table" in captured.out
        assert "Removed 42 files" in captured.out

    def test_formatter_functions__result_dry_run__e50f68cb(self, capsys):
        """Test echo_vacuum_result formats dry-run result correctly."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_result

        result = _create_table_result("test_table", "gold", 10)
        echo_vacuum_result(result, dry_run=True)

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "Would vacuum" in captured.out
        assert "Would remove 10 files" in captured.out

    def test_echo_vacuum_result_error(self, capsys):
        """Test echo_vacuum_result formats error result correctly."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_result

        result = _create_table_result(
            "test_table", "silver", 0, error="Delta table not found"
        )
        echo_vacuum_result(result, dry_run=False)

        captured = capsys.readouterr()
        # Error messages go to stderr
        assert "Error:" in captured.err
        assert "Delta table not found" in captured.err

    def test_echo_vacuum_all_summary_success(self, capsys):
        """Test echo_vacuum_all_summary formats summary correctly."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_all_summary

        result = _create_vacuum_all_result(
            results=[
                _create_table_result("t1", "silver", 10),
                _create_table_result("t2", "gold", 5),
            ]
        )
        echo_vacuum_all_summary(result)

        captured = capsys.readouterr()
        assert "Total:" in captured.out
        assert "15" in captured.out

    def test_formatter_functions__with_failures__7b7bfe68(self, capsys):
        """Test echo_vacuum_all_summary shows failed tables."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_all_summary

        result = _create_vacuum_all_result(
            results=[
                _create_table_result("t1", "silver", 10),
                _create_table_result("t2", "gold", 0, error="Failed"),
            ]
        )
        echo_vacuum_all_summary(result)

        captured = capsys.readouterr()
        # Failed tables list goes to stderr
        assert "Failed tables:" in captured.err
        assert "gold/t2" in captured.err

    def test_formatter_functions__all_summary_dry_run__70fef12c(self, capsys):
        """Test echo_vacuum_all_summary formats dry-run summary correctly."""
        from bioetl.interfaces.cli.formatters import echo_vacuum_all_summary

        result = _create_vacuum_all_result(
            results=[_create_table_result("t1", "silver", 10)],
            dry_run=True,
        )
        echo_vacuum_all_summary(result)

        captured = capsys.readouterr()
        assert "would remove" in captured.out
