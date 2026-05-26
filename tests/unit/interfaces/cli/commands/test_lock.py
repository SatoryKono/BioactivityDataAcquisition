"""Unit tests for lock.py CLI commands.

Tests lock release and check subcommands.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from click.testing import CliRunner

from bioetl.interfaces.cli import cli

_VALID_UUID = str(uuid4())
_INVALID_UUID = "not-a-uuid"


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_lock_service() -> MagicMock:
    """Create a mock lock service."""
    service = MagicMock()
    service.release_lock = AsyncMock(return_value=True)
    service.check_lock = AsyncMock(return_value=True)
    return service


@pytest.mark.unit
class TestLockGroupHelp:
    """Test the lock command group."""

    def test_lock_help_displays_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that lock --help displays release and check subcommands."""
        result = cli_runner.invoke(cli, ["lock", "--help"])

        assert result.exit_code == 0
        assert "release" in result.output
        assert "check" in result.output


@pytest.mark.unit
class TestLockReleaseCommand:
    """Tests for lock release subcommand."""

    def test_release_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test lock release --help shows required options."""
        result = cli_runner.invoke(cli, ["lock", "release", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-id" in result.output
        assert "--exclusive" in result.output

    def test_release_success_prints_confirmation(
        self, cli_runner: CliRunner, mock_lock_service: MagicMock
    ) -> None:
        """Test successful lock release prints confirmation message."""
        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    _VALID_UUID,
                ],
            )

        assert result.exit_code == 0
        assert "released" in result.output
        assert "chembl_activity" in result.output

    def test_release_with_exclusive_flag(
        self, cli_runner: CliRunner, mock_lock_service: MagicMock
    ) -> None:
        """Test lock release with --exclusive flag passes it to service."""
        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    _VALID_UUID,
                    "--exclusive",
                ],
            )

        assert result.exit_code == 0
        mock_lock_service.release_lock.assert_awaited_once()
        call_kwargs = mock_lock_service.release_lock.call_args.kwargs
        assert call_kwargs["exclusive"] is True

    def test_release_not_held_prints_warning(
        self, cli_runner: CliRunner, mock_lock_service: MagicMock
    ) -> None:
        """Test that lock-not-released prints a warning."""
        mock_lock_service.release_lock = AsyncMock(return_value=False)

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "release",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    _VALID_UUID,
                ],
            )

        assert result.exit_code == 0
        # Should print a warning about lock not released
        assert "not released" in result.output or "not held" in result.output

    def test_release_invalid_uuid_prints_error(self, cli_runner: CliRunner) -> None:
        """Test that an invalid UUID prints an error message."""
        result = cli_runner.invoke(
            cli,
            [
                "lock",
                "release",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                _INVALID_UUID,
            ],
        )

        assert result.exit_code == 0  # returns 0 but prints error
        assert "Invalid run-id" in result.output or "UUID" in result.output

    def test_release_missing_pipeline_exits_nonzero(
        self, cli_runner: CliRunner
    ) -> None:
        """Test that missing --pipeline option causes non-zero exit."""
        result = cli_runner.invoke(
            cli,
            ["lock", "release", "--run-id", _VALID_UUID],
        )

        assert result.exit_code != 0


@pytest.mark.unit
class TestLockCheckCommand:
    """Tests for lock check subcommand."""

    def test_check_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test lock check --help shows required options."""
        result = cli_runner.invoke(cli, ["lock", "check", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--run-id" in result.output

    def test_check_lock_held__test_lock_check_command_cli_commands_test_lock_178(
        self, cli_runner: CliRunner, mock_lock_service: MagicMock
    ) -> None:
        """Test check reports lock IS held."""
        mock_lock_service.check_lock = AsyncMock(return_value=True)

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "check",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    _VALID_UUID,
                ],
            )

        assert result.exit_code == 0
        assert "IS held" in result.output or "held" in result.output

    def test_check_lock_not_held__test_lock_check_command_cli_commands_test_lock_203(
        self, cli_runner: CliRunner, mock_lock_service: MagicMock
    ) -> None:
        """Test check reports lock is NOT held."""
        mock_lock_service.check_lock = AsyncMock(return_value=False)

        with patch(
            "bioetl.interfaces.cli.commands.lock.get_lock_service",
            return_value=mock_lock_service,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "lock",
                    "check",
                    "--pipeline",
                    "chembl_activity",
                    "--run-id",
                    _VALID_UUID,
                ],
            )

        assert result.exit_code == 0
        assert "NOT held" in result.output or "not" in result.output.lower()

    def test_check_invalid_uuid_prints_error(self, cli_runner: CliRunner) -> None:
        """Test that an invalid UUID for check command prints error."""
        result = cli_runner.invoke(
            cli,
            [
                "lock",
                "check",
                "--pipeline",
                "chembl_activity",
                "--run-id",
                _INVALID_UUID,
            ],
        )

        assert result.exit_code == 0
        assert "Invalid run-id" in result.output or "UUID" in result.output

    def test_check_missing_run_id_exits_nonzero(self, cli_runner: CliRunner) -> None:
        """Test that missing --run-id option causes non-zero exit."""
        result = cli_runner.invoke(
            cli,
            ["lock", "check", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code != 0
