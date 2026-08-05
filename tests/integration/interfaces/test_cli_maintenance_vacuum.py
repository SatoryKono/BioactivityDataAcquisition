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
"""Integration tests for CLI maintenance vacuum command.

Tests the vacuum command for Delta table maintenance operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.interfaces.cli import cli

if TYPE_CHECKING:
    from click.testing import CliRunner

pytestmark = pytest.mark.integration


class TestCliMaintenanceVacuumHelp:
    """Test vacuum command help and argument handling."""

    def test_maintenance_vacuum_help(self, cli_runner: CliRunner):
        """Test that maintenance vacuum --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum", "--help"])

        assert result.exit_code == 0
        assert "vacuum" in result.output.lower()
        assert "TABLE" in result.output
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output

    def test_maintenance_vacuum_requires_table(self, cli_runner: CliRunner):
        """Test that vacuum requires TABLE argument."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "TABLE" in result.output


class TestCliMaintenanceVacuumExecution:
    """Test vacuum command execution scenarios."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.vacuum = AsyncMock(return_value=42)
        return service

    def test_vacuum_success(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test successful vacuum operation."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity"],
            )

        assert result.exit_code == 0
        assert "42" in result.output or "Removed" in result.output

        # Verify service was called correctly
        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=7,  # Default value
            dry_run=False,
        )

    def test_vacuum_with_custom_retention(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test vacuum with custom retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "--retention-days", "30"],
            )

        assert result.exit_code == 0

        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=30,
            dry_run=False,
        )

    def test_vacuum_with_short_retention_flag(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test vacuum with short -r flag for retention."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "-r", "14"],
            )

        assert result.exit_code == 0

        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=14,
            dry_run=False,
        )


class TestCliMaintenanceVacuumDryRun:
    """Test vacuum command dry-run mode."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.vacuum = AsyncMock(return_value=10)
        return service

    def test_vacuum_dry_run_shows_preview(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that --dry-run shows what would be removed."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output or "Would" in result.output

        # Verify dry_run flag was passed
        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=7,
            dry_run=True,
        )

    def test_vacuum_dry_run_shows_file_count(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that dry-run shows the number of files that would be removed."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "10" in result.output  # File count from mock

    def test_vacuum_dry_run_combined_with_retention(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test dry-run with custom retention days."""
        mock_lifecycle_service.vacuum.return_value = 25

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "--dry-run", "-r", "30"],
            )

        assert result.exit_code == 0
        assert "25" in result.output

        mock_lifecycle_service.vacuum.assert_called_once_with(
            table="chembl.activity",
            retention_days=30,
            dry_run=True,
        )


class TestCliMaintenanceVacuumErrors:
    """Test vacuum command error handling."""

    @pytest.fixture
    def mock_lifecycle_service_error(self):
        """Create a mock lifecycle service that raises an error."""
        service = MagicMock()
        service.vacuum = AsyncMock(
            side_effect=RuntimeError("Vacuum failed: table not found")
        )
        return service

    def test_vacuum_handles_service_error(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service_error: MagicMock,
    ):
        """Test that vacuum propagates service errors."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service_error,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "nonexistent.table"],
            )

        # Should fail with non-zero exit code
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_vacuum_with_zero_retention_succeeds(
        self,
        cli_runner: CliRunner,
    ):
        """Test that vacuum with zero retention is allowed (uses default)."""
        mock_service = MagicMock()
        mock_service.vacuum = AsyncMock(return_value=0)

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "-r", "0"],
            )

        # Should succeed (0 retention is valid)
        assert result.exit_code == 0


class TestCliMaintenanceVacuumOutput:
    """Test vacuum command output formatting."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.vacuum = AsyncMock(return_value=100)
        return service

    def test_vacuum_shows_removed_count(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that vacuum shows the number of removed files."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity"],
            )

        assert result.exit_code == 0
        assert "100" in result.output
        assert "Removed" in result.output or "files" in result.output.lower()

    def test_vacuum_dry_run_shows_would_remove(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that dry-run output says 'would remove'."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "vacuum", "chembl.activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would" in result.output or "would" in result.output


# =============================================================================
# vacuum-all Command Tests
# =============================================================================


class TestCliMaintenanceVacuumAllHelp:
    """Test vacuum-all command help and argument handling."""

    def test_maintenance_vacuum_all_help(self, cli_runner: CliRunner):
        """Test that maintenance vacuum-all --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--help"])

        assert result.exit_code == 0
        assert "vacuum" in result.output.lower()
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output
        assert "--layer" in result.output


class TestCliMaintenanceVacuumAllExecution:
    """Test vacuum-all command execution scenarios."""

    @pytest.fixture
    def mock_vacuum_service(self):
        """Create a mock vacuum service."""
        from bioetl.application.services.ops.vacuum_service import (
            TableVacuumResult,
            VacuumAllResult,
        )

        service = MagicMock()
        service.collect_tables = MagicMock(
            return_value=[
                ("chembl_activity", "silver"),
                ("chembl_activity", "gold"),
            ]
        )
        service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult("chembl_activity", "silver", 20, None),
                    TableVacuumResult("chembl_activity", "gold", 10, None),
                ),
                dry_run=False,
            )
        )
        return service

    def test_vacuum_all_success(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service: MagicMock,
    ):
        """Test successful vacuum-all operation."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "30" in result.output  # Total files removed (20 + 10)
        mock_vacuum_service.collect_tables.assert_called_once_with("all")

    def test_vacuum_all_with_layer_silver(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service: MagicMock,
    ):
        """Test vacuum-all filtering by silver layer."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "silver"),
        ]

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--layer", "silver"]
            )

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("silver")

    def test_vacuum_all_with_layer_gold(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service: MagicMock,
    ):
        """Test vacuum-all filtering by gold layer."""
        mock_vacuum_service.collect_tables.return_value = [
            ("chembl_activity", "gold"),
        ]

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--layer", "gold"]
            )

        assert result.exit_code == 0
        mock_vacuum_service.collect_tables.assert_called_once_with("gold")

    def test_vacuum_all_with_custom_retention(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service: MagicMock,
    ):
        """Test vacuum-all with custom retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "vacuum-all", "--retention-days", "30"]
            )

        assert result.exit_code == 0
        call_args = mock_vacuum_service.vacuum_all.call_args
        assert call_args[1]["retention_days"] == 30


class TestCliMaintenanceVacuumAllDryRun:
    """Test vacuum-all command dry-run mode."""

    @pytest.fixture
    def mock_vacuum_service_dry_run(self):
        """Create a mock vacuum service for dry-run."""
        from bioetl.application.services.ops.vacuum_service import (
            TableVacuumResult,
            VacuumAllResult,
        )

        service = MagicMock()
        service.collect_tables = MagicMock(
            return_value=[
                ("chembl_activity", "silver"),
            ]
        )
        service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(TableVacuumResult("chembl_activity", "silver", 15, None),),
                dry_run=True,
            )
        )
        return service

    def test_vacuum_all_dry_run_shows_preview(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_dry_run: MagicMock,
    ):
        """Test that --dry-run shows what would be removed."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_dry_run,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output or "Would" in result.output

    def test_vacuum_all_dry_run_passes_flag_to_service(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_dry_run: MagicMock,
    ):
        """Test that dry_run flag is passed to vacuum service."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_dry_run,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert result.exit_code == 0
        call_args = mock_vacuum_service_dry_run.vacuum_all.call_args
        assert call_args[1]["dry_run"] is True


class TestCliMaintenanceVacuumAllNoTables:
    """Test vacuum-all when no tables are found."""

    @pytest.fixture
    def mock_vacuum_service_empty(self):
        """Create a mock vacuum service with no tables."""
        service = MagicMock()
        service.collect_tables = MagicMock(return_value=[])
        return service

    def test_vacuum_all_no_tables_found(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_empty: MagicMock,
    ):
        """Test vacuum-all when no tables to vacuum."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_empty,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0
        assert "No tables found" in result.output


class TestCliMaintenanceVacuumAllErrors:
    """Test vacuum-all command error handling."""

    @pytest.fixture
    def mock_vacuum_service_partial_failure(self):
        """Create a mock vacuum service with partial failures."""
        from bioetl.application.services.ops.vacuum_service import (
            TableVacuumResult,
            VacuumAllResult,
        )

        service = MagicMock()
        service.collect_tables = MagicMock(
            return_value=[
                ("table1", "silver"),
                ("table2", "gold"),
            ]
        )
        service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult("table1", "silver", 10, None),
                    TableVacuumResult("table2", "gold", 0, "Delta table corrupted"),
                ),
                dry_run=False,
            )
        )
        return service

    def test_vacuum_all_partial_failure_shows_errors(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_partial_failure: MagicMock,
    ):
        """Test that partial failures show error messages."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_partial_failure,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert result.exit_code == 0  # Partial failure still exits 0
        assert "Error:" in result.output
        assert "Delta table corrupted" in result.output

    def test_vacuum_all_partial_failure_shows_failed_tables(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_partial_failure: MagicMock,
    ):
        """Test that partial failures list failed table names."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_partial_failure,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "Failed tables:" in result.output
        assert "gold/table2" in result.output


class TestCliMaintenanceVacuumAllOutput:
    """Test vacuum-all command output formatting."""

    @pytest.fixture
    def mock_vacuum_service_multi(self):
        """Create a mock vacuum service with multiple tables."""
        from bioetl.application.services.ops.vacuum_service import (
            TableVacuumResult,
            VacuumAllResult,
        )

        service = MagicMock()
        service.collect_tables = MagicMock(
            return_value=[
                ("chembl_activity", "silver"),
                ("chembl_activity", "gold"),
                ("chembl_assay", "silver"),
            ]
        )
        service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(
                    TableVacuumResult("chembl_activity", "silver", 10, None),
                    TableVacuumResult("chembl_activity", "gold", 5, None),
                    TableVacuumResult("chembl_assay", "silver", 8, None),
                ),
                dry_run=False,
            )
        )
        return service

    def test_vacuum_all_shows_each_table_result(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_multi: MagicMock,
    ):
        """Test that output shows result for each table."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_multi,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "silver/chembl_activity" in result.output
        assert "gold/chembl_activity" in result.output
        assert "silver/chembl_assay" in result.output

    def test_vacuum_all_shows_total_files(
        self,
        cli_runner: CliRunner,
        mock_vacuum_service_multi: MagicMock,
    ):
        """Test that output shows total files removed."""
        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_vacuum_service_multi,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all"])

        assert "Total:" in result.output
        assert "23" in result.output  # 10 + 5 + 8

    def test_vacuum_all_dry_run_shows_would_remove(
        self,
        cli_runner: CliRunner,
    ):
        """Test that dry-run output says 'would remove'."""
        from bioetl.application.services.ops.vacuum_service import (
            TableVacuumResult,
            VacuumAllResult,
        )

        mock_service = MagicMock()
        mock_service.collect_tables = MagicMock(
            return_value=[("chembl_activity", "silver")]
        )
        mock_service.vacuum_all = AsyncMock(
            return_value=VacuumAllResult(
                results=(TableVacuumResult("chembl_activity", "silver", 10, None),),
                dry_run=True,
            )
        )

        with patch(
            "bioetl.interfaces.cli.commands.vacuum.get_vacuum_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "vacuum-all", "--dry-run"])

        assert result.exit_code == 0
        assert "would remove" in result.output.lower()
