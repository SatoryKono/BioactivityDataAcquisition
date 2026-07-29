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
"""Unit tests for cleanup.py CLI commands.

Tests bronze-cleanup and cleanup-preview commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.application.core.lifecycle.cleanup_service import CleanupPreview, LayerInfo
from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli import cli
from tests.unit.interfaces.cli.commands.conftest import mock_asyncio_run

TEST_SILVER_PATH = "test-output/silver/chembl/activity"
TEST_GOLD_PATH = "test-output/gold/chembl/activity"


@dataclass
class _MockCleanupResult:
    files_removed: int
    bytes_freed: int
    directories_removed: int


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_bronze_cleanup_service() -> MagicMock:
    """Create a mock BronzeCleanupService."""
    service = MagicMock()
    service.cleanup = AsyncMock(
        return_value=_MockCleanupResult(
            files_removed=10,
            bytes_freed=1024 * 1024,
            directories_removed=2,
        )
    )
    return service


@pytest.mark.unit
class TestBronzeCleanupCommand:
    """Tests for the bronze-cleanup subcommand."""

    def test_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test bronze-cleanup --help shows retention-days and dry-run options."""
        result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup", "--help"])

        assert result.exit_code == 0
        assert "--retention-days" in result.output
        assert "--dry-run" in result.output

    def test_success_default_retention(
        self,
        cli_runner: CliRunner,
        mock_bronze_cleanup_service: MagicMock,
    ) -> None:
        """Test successful bronze cleanup with default 90-day retention."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup"])

        assert result.exit_code == 0
        assert "10 files" in result.output
        assert "2 empty directories" in result.output
        mock_bronze_cleanup_service.cleanup.assert_awaited_once_with(
            retention_days=90, dry_run=False
        )

    def test_success_custom_retention(
        self,
        cli_runner: CliRunner,
        mock_bronze_cleanup_service: MagicMock,
    ) -> None:
        """Test bronze cleanup with custom -r flag passes correct retention days."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "bronze-cleanup", "-r", "30"]
            )

        assert result.exit_code == 0
        mock_bronze_cleanup_service.cleanup.assert_awaited_once_with(
            retention_days=30, dry_run=False
        )

    def test_dry_run_shows_prefix_and_would_remove(
        self,
        cli_runner: CliRunner,
        mock_bronze_cleanup_service: MagicMock,
    ) -> None:
        """Test dry-run mode outputs [DRY-RUN] prefix and 'Would remove'."""
        with patch(
            "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
            return_value=mock_bronze_cleanup_service,
        ):
            result = cli_runner.invoke(
                cli, ["maintenance", "bronze-cleanup", "--dry-run"]
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Would remove" in result.output
        mock_bronze_cleanup_service.cleanup.assert_awaited_once_with(
            retention_days=90, dry_run=True
        )

    def test_domain_error_exits_nonzero(self, cli_runner: CliRunner) -> None:
        """Test that BioETLError causes non-zero exit code."""
        with mock_asyncio_run(side_effect=BioETLError("disk error")):
            with patch(
                "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
                return_value=MagicMock(),
            ):
                result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup"])

        assert result.exit_code != 0

    def test_keyboard_interrupt_exits_nonzero(self, cli_runner: CliRunner) -> None:
        """Test that KeyboardInterrupt exits with non-zero code."""
        with mock_asyncio_run(side_effect=KeyboardInterrupt()):
            with patch(
                "bioetl.interfaces.cli.commands.cleanup.get_bronze_cleanup_service",
                return_value=MagicMock(),
            ):
                result = cli_runner.invoke(cli, ["maintenance", "bronze-cleanup"])

        assert result.exit_code != 0


@pytest.mark.unit
class TestCleanupPreviewCommand:
    """Tests for the cleanup-preview subcommand."""

    def test_help_displays_pipeline_option(self, cli_runner: CliRunner) -> None:
        """Test cleanup-preview --help shows --pipeline option."""
        result = cli_runner.invoke(cli, ["maintenance", "cleanup-preview", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output

    def test_missing_pipeline_exits_nonzero(self, cli_runner: CliRunner) -> None:
        """Test that missing --pipeline option causes non-zero exit."""
        result = cli_runner.invoke(cli, ["maintenance", "cleanup-preview"])

        assert result.exit_code != 0

    def test_success_renders_silver_and_gold_preview(
        self, cli_runner: CliRunner
    ) -> None:
        """Test cleanup-preview renders Silver and Gold layer info."""
        preview = CleanupPreview(
            silver=LayerInfo(
                path=TEST_SILVER_PATH,
                file_count=3,
                exists=True,
            ),
            gold=LayerInfo(
                path=TEST_GOLD_PATH,
                file_count=1,
                exists=True,
            ),
            total_files=4,
        )

        with patch(
            "bioetl.interfaces.cli.commands.cleanup.preview_pipeline_cleanup",
            new=AsyncMock(return_value=preview),
        ):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "cleanup-preview", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "[DRY-RUN]" in result.output
        assert "Silver:" in result.output
        assert "Gold:" in result.output

    def test_preview_command__error_exits_nonzero__9337cc50(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that BioETLError on preview exits non-zero."""
        with mock_asyncio_run(side_effect=BioETLError("preview error")):
            result = cli_runner.invoke(
                cli,
                ["maintenance", "cleanup-preview", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code != 0
