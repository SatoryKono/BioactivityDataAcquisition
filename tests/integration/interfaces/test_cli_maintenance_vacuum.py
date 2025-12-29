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
