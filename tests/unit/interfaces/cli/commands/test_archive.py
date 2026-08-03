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
"""Unit tests for archive.py CLI command.

Tests the archive command for Delta table cold storage archival.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli import cli
from tests.unit.interfaces.cli.commands.conftest import mock_asyncio_run


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_lifecycle_service() -> MagicMock:
    """Create a mock lifecycle service."""
    service = MagicMock()
    service.archive = AsyncMock(return_value=5)
    return service


@pytest.mark.unit
class TestArchiveHelp:
    """Test archive command help output."""

    def test_archive_help_displays_arguments(self, cli_runner: CliRunner) -> None:
        """Test that archive --help shows required arguments."""
        result = cli_runner.invoke(cli, ["maintenance", "archive", "--help"])

        assert result.exit_code == 0
        assert "TABLE" in result.output
        assert "TARGET_PATH" in result.output

    def test_archive_help_displays_remove_source_flag(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that archive --help shows --remove-source flag."""
        result = cli_runner.invoke(cli, ["maintenance", "archive", "--help"])

        assert result.exit_code == 0
        assert "--remove-source" in result.output


@pytest.mark.unit
class TestArchiveCommand:
    """Tests for archive command happy and error paths."""

    def test_archive_command__archive_success__aa880529(
        self, cli_runner: CliRunner, mock_lifecycle_service: MagicMock
    ) -> None:
        """Test successful archive operation echoes file count and path."""
        with patch(
            "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
            return_value=mock_lifecycle_service,
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "archive", "chembl.activity", "/archive/chembl"],
            )

        assert result.exit_code == 0
        assert "5" in result.output
        assert "/archive/chembl" in result.output
        mock_lifecycle_service.archive.assert_awaited_once_with(
            table="chembl.activity",
            target_path="/archive/chembl",
            remove_source=False,
        )

    def test_archive_with_remove_source_flag(
        self, cli_runner: CliRunner, mock_lifecycle_service: MagicMock
    ) -> None:
        """Test archive --remove-source passes flag to service."""
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
                    "/archive/chembl",
                    "--remove-source",
                ],
            )

        assert result.exit_code == 0
        mock_lifecycle_service.archive.assert_awaited_once_with(
            table="chembl.activity",
            target_path="/archive/chembl",
            remove_source=True,
        )

    def test_archive_domain_error_exits_nonzero(self, cli_runner: CliRunner) -> None:
        """Test that BioETLError causes non-zero exit code."""
        with mock_asyncio_run(side_effect=BioETLError("archive failed")):
            with patch(
                "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
                return_value=MagicMock(),
            ):
                result = cli_runner.invoke(
                    cli,
                    ["maintenance", "archive", "chembl.activity", "/archive/chembl"],
                )

        assert result.exit_code != 0

    def test_archive_missing_arguments_exits_nonzero(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that missing required arguments causes non-zero exit code."""
        result = cli_runner.invoke(cli, ["maintenance", "archive"])

        assert result.exit_code != 0

    def test_archive_keyboard_interrupt_exits_nonzero(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that KeyboardInterrupt is handled gracefully."""
        with mock_asyncio_run(side_effect=KeyboardInterrupt()):
            with patch(
                "bioetl.interfaces.cli.commands.archive.get_lifecycle_service",
                return_value=MagicMock(),
            ):
                result = cli_runner.invoke(
                    cli,
                    ["maintenance", "archive", "chembl.activity", "/archive/chembl"],
                )

        assert result.exit_code != 0
