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
"""Integration tests for CLI maintenance archive command.

Tests the archive command for Delta table archival operations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.interfaces.cli import cli

if TYPE_CHECKING:
    from pathlib import Path

    from click.testing import CliRunner

pytestmark = pytest.mark.integration


class TestCliMaintenanceArchiveHelp:
    """Test archive command help and argument handling."""

    def test_maintenance_archive_help(self, cli_runner: CliRunner):
        """Test that maintenance archive --help works."""
        result = cli_runner.invoke(cli, ["maintenance", "archive", "--help"])

        assert result.exit_code == 0
        assert "archive" in result.output.lower()
        assert "TABLE" in result.output
        assert "TARGET_PATH" in result.output
        assert "--remove-source" in result.output

    def test_maintenance_archive_requires_table(self, cli_runner: CliRunner):
        """Test that archive requires TABLE argument."""
        result = cli_runner.invoke(cli, ["maintenance", "archive"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "TABLE" in result.output

    def test_maintenance_archive_requires_target_path(self, cli_runner: CliRunner):
        """Test that archive requires TARGET_PATH argument."""
        result = cli_runner.invoke(cli, ["maintenance", "archive", "chembl.activity"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "TARGET_PATH" in result.output


class TestCliMaintenanceArchiveExecution:
    """Test archive command execution scenarios."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.archive = AsyncMock(return_value=100)
        return service

    def test_archive_success(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test successful archive operation."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/2025"],
            )

        assert result.exit_code == 0
        assert "100" in result.output or "Archived" in result.output

        # Verify service was called correctly
        mock_lifecycle_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="/archive/2025",
            remove_source=False,
        )

    def test_archive_with_remove_source(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test archive with --remove-source flag."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "archive",
                    "chembl.activity",
                    "/archive/2025",
                    "--remove-source",
                ],
            )

        assert result.exit_code == 0

        mock_lifecycle_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="/archive/2025",
            remove_source=True,
        )

    def test_archive_with_different_tables(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test archive with different table names."""
        mock_lifecycle_service.archive.return_value = 50

        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "pubchem.compound", "/cold/storage"],
            )

        assert result.exit_code == 0
        assert "50" in result.output

        mock_lifecycle_service.archive.assert_called_once_with(
            table="pubchem.compound",
            target_path="/cold/storage",
            remove_source=False,
        )


class TestCliMaintenanceArchivePathValidation:
    """Test archive command path handling."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.archive = AsyncMock(return_value=25)
        return service

    def test_archive_with_absolute_path(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
        tmp_path: Path,
    ):
        """Test archive with absolute target path."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "archive",
                    "chembl.activity",
                    str(tmp_path / "archive" / "delta"),
                ],
            )

        assert result.exit_code == 0
        mock_lifecycle_service.archive.assert_called_once()

    def test_archive_with_relative_path(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test archive with relative target path."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "./archive/backup"],
            )

        assert result.exit_code == 0
        mock_lifecycle_service.archive.assert_called_once_with(
            table="chembl.activity",
            target_path="./archive/backup",
            remove_source=False,
        )

    def test_archive_with_complex_path(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test archive with path containing special characters."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "archive",
                    "chembl.activity",
                    "/archive/2025-01-01/chembl_backup",
                ],
            )

        assert result.exit_code == 0


class TestCliMaintenanceArchiveErrors:
    """Test archive command error handling."""

    @pytest.fixture
    def mock_lifecycle_service_error(self):
        """Create a mock lifecycle service that raises an error."""
        service = MagicMock()
        service.archive = AsyncMock(
            side_effect=RuntimeError("Archive failed: permission denied")
        )
        return service

    def test_archive_handles_service_error(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service_error: MagicMock,
    ):
        """Test that archive propagates service errors."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service_error,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/path"],
            )

        # Should fail with non-zero exit code or show error
        assert result.exit_code != 0 or "error" in result.output.lower()

    def test_archive_handles_table_not_found(
        self,
        cli_runner: CliRunner,
    ):
        """Test that archive handles missing table."""
        mock_service = MagicMock()
        mock_service.archive = AsyncMock(
            side_effect=FileNotFoundError("Table 'nonexistent.table' not found")
        )

        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "nonexistent.table", "/archive/path"],
            )

        # Should fail
        assert result.exit_code != 0 or "not found" in result.output.lower()


class TestCliMaintenanceArchiveRemoveSource:
    """Test archive command with remove-source behavior."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.archive = AsyncMock(return_value=75)
        return service

    def test_archive_without_remove_source_keeps_source(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that archive without --remove-source keeps the source."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/path"],
            )

        assert result.exit_code == 0

        # Verify remove_source=False was passed
        call_args = mock_lifecycle_service.archive.call_args
        assert call_args.kwargs.get("remove_source") is False

    def test_archive_with_remove_source_removes_source(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that archive with --remove-source removes the source."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "maintenance",
                    "archive",
                    "chembl.activity",
                    "/archive/path",
                    "--remove-source",
                ],
            )

        assert result.exit_code == 0

        # Verify remove_source=True was passed
        call_args = mock_lifecycle_service.archive.call_args
        assert call_args.kwargs.get("remove_source") is True


class TestCliMaintenanceArchiveOutput:
    """Test archive command output formatting."""

    @pytest.fixture
    def mock_lifecycle_service(self):
        """Create a mock lifecycle service."""
        service = MagicMock()
        service.archive = AsyncMock(return_value=200)
        return service

    def test_archive_shows_archived_count(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that archive shows the number of archived files."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/path"],
            )

        assert result.exit_code == 0
        assert "200" in result.output
        assert "Archived" in result.output or "files" in result.output.lower()

    def test_archive_shows_target_path(
        self,
        cli_runner: CliRunner,
        mock_lifecycle_service: MagicMock,
    ):
        """Test that archive output includes target path."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/cold/storage/2025"],
            )

        assert result.exit_code == 0
        assert "/cold/storage/2025" in result.output

    def test_archive_zero_files(
        self,
        cli_runner: CliRunner,
    ):
        """Test archive when table is empty."""
        mock_service = MagicMock()
        mock_service.archive = AsyncMock(return_value=0)

        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "empty.table", "/archive/path"],
            )

        assert result.exit_code == 0
        assert "0" in result.output
