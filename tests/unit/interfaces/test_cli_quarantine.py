"""Unit tests for CLI quarantine commands.

Tests for CLI quarantine commands (inspect, stats, replay, purge, resolve)
with mocked services. Uses Click's CliRunner for command testing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.types import QuarantineRecordStatus
from bioetl.interfaces.cli.main import cli


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create Click's CliRunner for testing CLI commands."""
    return CliRunner()


@pytest.fixture
def mock_quarantine_manager() -> MagicMock:
    """Create a mock quarantine manager."""
    manager = MagicMock()
    manager.inspect = AsyncMock(return_value=[])
    manager.get_stats = AsyncMock(
        return_value={
            "total_count": 0,
            "by_error_code": {},
            "by_status": {},
        }
    )
    return manager


@pytest.fixture
def mock_unified_quarantine() -> MagicMock:
    """Create a mock UnifiedQuarantine."""
    quarantine = MagicMock()
    quarantine.replay.return_value = []
    quarantine.purge.return_value = 0
    quarantine.update_status.return_value = True
    quarantine.get_stats = AsyncMock(
        return_value={
            "total_count": 0,
            "by_error_code": {},
            "by_status": {},
        }
    )
    return quarantine


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.quarantine_path = "/tmp/quarantine"
    return settings


# =============================================================================
# quarantine group Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineGroup:
    """Tests for the quarantine command group."""

    def test_quarantine_help(self, cli_runner: CliRunner):
        """Test quarantine --help shows subcommands."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])

        assert result.exit_code == 0
        assert "inspect" in result.output
        assert "stats" in result.output
        assert "replay" in result.output
        assert "purge" in result.output
        assert "resolve" in result.output

    def test_quarantine_without_subcommand(self, cli_runner: CliRunner):
        """Test quarantine without subcommand shows help."""
        result = cli_runner.invoke(cli, ["quarantine"])

        # Click groups may exit with 0 or 2 when invoked without subcommand
        # The important thing is that subcommands are shown
        assert "inspect" in result.output or "stats" in result.output


# =============================================================================
# quarantine inspect Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineInspectCommand:
    """Tests for quarantine inspect command."""

    def test_quarantine_inspect_help(self, cli_runner: CliRunner):
        """Test quarantine inspect --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--limit" in result.output
        assert "--error-code" in result.output

    def test_quarantine_inspect_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine inspect requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_quarantine_inspect_empty(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine inspect with no records."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "inspect", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "No records found" in result.output

    def test_quarantine_inspect_with_records(self, cli_runner: CliRunner):
        """Test quarantine inspect displays records."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(
            return_value=[
                {
                    "error_code": "VALIDATION_ERROR",
                    "payload": {"molecule_id": "CHEMBL123"},
                },
                {
                    "error_code": "SCHEMA_ERROR",
                    "payload": {"molecule_id": "CHEMBL456"},
                },
            ]
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "inspect", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "VALIDATION_ERROR" in result.output
        assert "SCHEMA_ERROR" in result.output

    def test_quarantine_inspect_with_error_code_filter(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine inspect with --error-code filter."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--error-code",
                    "VALIDATION_ERROR",
                ],
            )

        assert result.exit_code == 0
        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=100, error_code="VALIDATION_ERROR"
        )

    def test_quarantine_inspect_with_custom_limit(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine inspect with --limit option."""
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "inspect",
                    "--pipeline",
                    "chembl_activity",
                    "--limit",
                    "50",
                ],
            )

        assert result.exit_code == 0
        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=50, error_code=None
        )


# =============================================================================
# quarantine stats Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineStatsCommand:
    """Tests for quarantine stats command."""

    def test_quarantine_stats_help(self, cli_runner: CliRunner):
        """Test quarantine stats --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "stats", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--json" in result.output

    def test_quarantine_stats_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine stats requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "stats"])

        assert result.exit_code != 0

    def test_quarantine_stats_dashboard_output(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine stats dashboard output format."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 100,
                "by_error_code": {
                    "VALIDATION_ERROR": 60,
                    "SCHEMA_ERROR": 30,
                    "NETWORK_ERROR": 10,
                },
                "by_status": {
                    "NEW": 70,
                    "REVIEWED": 20,
                    "RESOLVED": 10,
                },
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "Quarantine Dashboard" in result.output
        assert "chembl_activity" in result.output
        assert "Total Records: 100" in result.output
        assert "By Error Code" in result.output
        assert "VALIDATION_ERROR" in result.output
        assert "60.0%" in result.output
        assert "By Status" in result.output
        assert "NEW" in result.output

    def test_quarantine_stats_json_output(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine stats JSON output."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 50,
                "by_error_code": {"VALIDATION_ERROR": 50},
                "by_status": {"NEW": 50},
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity", "--json"]
            )

        assert result.exit_code == 0
        assert '"total_count": 50' in result.output
        assert '"by_error_code"' in result.output
        assert '"VALIDATION_ERROR": 50' in result.output

    def test_quarantine_stats_empty(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine stats with empty quarantine."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 0,
                "by_error_code": {},
                "by_status": {},
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "Total Records: 0" in result.output

    def test_quarantine_stats_error_handling(self, cli_runner: CliRunner):
        """Test quarantine stats error handling."""
        mock_manager = MagicMock()
        mock_manager.get_stats = AsyncMock(
            side_effect=RuntimeError("Database connection failed")
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code != 0
        assert "Failed to get stats" in result.output

    def test_quarantine_stats_percentage_calculation(
        self, cli_runner: CliRunner, mock_quarantine_manager: MagicMock
    ):
        """Test quarantine stats correctly calculates percentages."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 200,
                "by_error_code": {"ERROR_A": 100, "ERROR_B": 50, "ERROR_C": 50},
                "by_status": {"NEW": 150, "RESOLVED": 50},
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "50.0%" in result.output  # ERROR_A: 100/200
        assert "25.0%" in result.output  # ERROR_B, ERROR_C, RESOLVED: 50/200
        assert "75.0%" in result.output  # NEW: 150/200


# =============================================================================
# quarantine replay Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineReplayCommand:
    """Tests for quarantine replay command."""

    def test_quarantine_replay_help(self, cli_runner: CliRunner):
        """Test quarantine replay --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "replay", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--error-code" in result.output
        assert "--max-age-days" in result.output
        assert "--dry-run" in result.output

    def test_quarantine_replay_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine replay requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "replay"])

        assert result.exit_code != 0

    def test_quarantine_replay_dry_run_with_records(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay dry-run mode with records."""
        mock_unified_quarantine.replay.return_value = [
            {"error_code": "VALIDATION_ERROR", "payload_hash": "abc123def456"},
            {"error_code": "NETWORK_ERROR", "payload_hash": "xyz789abc012"},
        ]

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "Would replay 2 record(s)" in result.output
        assert "VALIDATION_ERROR" in result.output
        assert "abc123def456" in result.output

    def test_quarantine_replay_dry_run_empty(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay dry-run with no records."""
        mock_unified_quarantine.replay.return_value = []

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "No records found for replay" in result.output

    def test_quarantine_replay_actual(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay actual execution."""
        mock_unified_quarantine.replay.return_value = [
            {"error_code": "VALIDATION_ERROR", "payload_hash": "abc123"},
            {"error_code": "NETWORK_ERROR", "payload_hash": "def456"},
        ]

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Replaying 2 record(s)" in result.output
        assert "Marked 2 record(s) as REPROCESSED" in result.output
        assert mock_unified_quarantine.update_status.call_count == 2

    def test_quarantine_replay_with_error_code_filter(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay with --error-code filter."""
        mock_unified_quarantine.replay.return_value = []

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--error-code",
                    "NETWORK_ERROR",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        # Verify error_code was passed to replay
        call_kwargs = mock_unified_quarantine.replay.call_args[1]
        assert call_kwargs["error_code"] == "NETWORK_ERROR"

    def test_quarantine_replay_with_max_age(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay with --max-age-days option."""
        mock_unified_quarantine.replay.return_value = []

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--max-age-days",
                    "14",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        call_kwargs = mock_unified_quarantine.replay.call_args[1]
        assert call_kwargs["max_age_days"] == 14

    def test_quarantine_replay_truncates_long_list(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay dry-run truncates list > 10 records."""
        # Create 15 records
        records = [
            {"error_code": f"ERROR_{i}", "payload_hash": f"hash_{i:03d}"}
            for i in range(15)
        ]
        mock_unified_quarantine.replay.return_value = records

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "replay",
                    "--pipeline",
                    "chembl_activity",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "Would replay 15 record(s)" in result.output
        assert "... and 5 more" in result.output

    def test_quarantine_replay_handles_missing_payload_hash(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine replay handles records without payload_hash."""
        mock_unified_quarantine.replay.return_value = [
            {"error_code": "ERROR", "payload_hash": None},
        ]

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        # update_status should not be called for records without payload_hash
        mock_unified_quarantine.update_status.assert_not_called()


# =============================================================================
# quarantine purge Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantinePurgeCommand:
    """Tests for quarantine purge command."""

    def test_quarantine_purge_help(self, cli_runner: CliRunner):
        """Test quarantine purge --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "purge", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--older-than-days" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_quarantine_purge_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine purge requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "purge"])

        assert result.exit_code != 0

    def test_quarantine_purge_dry_run(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge dry-run mode."""
        mock_unified_quarantine.get_stats = AsyncMock(
            return_value={"total_count": 50}
        )

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "Would purge records older than 30 days" in result.output
        assert "Current total in quarantine: 50" in result.output
        mock_unified_quarantine.purge.assert_not_called()

    def test_quarantine_purge_with_force(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge with --force flag."""
        mock_unified_quarantine.purge.return_value = 25

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "Purged 25 record(s)" in result.output
        mock_unified_quarantine.purge.assert_called_once()

    def test_quarantine_purge_confirmation_abort(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge confirmation abort."""
        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="n\n",  # Answer "no" to confirmation
            )

        assert result.exit_code == 1  # Aborted
        mock_unified_quarantine.purge.assert_not_called()

    def test_quarantine_purge_confirmation_yes(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge confirmation with yes answer."""
        mock_unified_quarantine.purge.return_value = 10

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="y\n",  # Answer "yes" to confirmation
            )

        assert result.exit_code == 0
        assert "Purged 10 record(s)" in result.output
        mock_unified_quarantine.purge.assert_called_once()

    def test_quarantine_purge_custom_older_than_days(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge with custom --older-than-days."""
        mock_unified_quarantine.purge.return_value = 5

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--older-than-days",
                    "60",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        call_kwargs = mock_unified_quarantine.purge.call_args[1]
        assert call_kwargs["older_than_days"] == 60

    def test_quarantine_purge_dry_run_custom_days(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine purge dry-run shows custom days."""
        mock_unified_quarantine.get_stats = AsyncMock(
            return_value={"total_count": 100}
        )

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--older-than-days",
                    "90",
                    "--dry-run",
                ],
            )

        assert result.exit_code == 0
        assert "Would purge records older than 90 days" in result.output


# =============================================================================
# quarantine resolve Tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineResolveCommand:
    """Tests for quarantine resolve command."""

    def test_quarantine_resolve_help(self, cli_runner: CliRunner):
        """Test quarantine resolve --help shows options."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--payload-hash" in result.output
        assert "--status" in result.output
        assert "IGNORED" in result.output
        assert "REPROCESSED" in result.output

    def test_quarantine_resolve_requires_pipeline(self, cli_runner: CliRunner):
        """Test that quarantine resolve requires --pipeline option."""
        result = cli_runner.invoke(
            cli,
            ["quarantine", "resolve", "--payload-hash", "abc123"],
        )

        assert result.exit_code != 0

    def test_quarantine_resolve_requires_payload_hash(self, cli_runner: CliRunner):
        """Test that quarantine resolve requires --payload-hash option."""
        result = cli_runner.invoke(
            cli,
            ["quarantine", "resolve", "--pipeline", "chembl_activity"],
        )

        assert result.exit_code != 0

    def test_quarantine_resolve_success_ignored(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine resolve with IGNORED status."""
        mock_unified_quarantine.update_status.return_value = True

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "abc123def456",
                ],
            )

        assert result.exit_code == 0
        assert "abc123def456 marked as IGNORED" in result.output
        mock_unified_quarantine.update_status.assert_called_once_with(
            "abc123def456", QuarantineRecordStatus.IGNORED
        )

    def test_quarantine_resolve_success_reprocessed(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine resolve with REPROCESSED status."""
        mock_unified_quarantine.update_status.return_value = True

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "xyz789abc012",
                    "--status",
                    "REPROCESSED",
                ],
            )

        assert result.exit_code == 0
        assert "xyz789abc012 marked as REPROCESSED" in result.output
        mock_unified_quarantine.update_status.assert_called_once_with(
            "xyz789abc012", QuarantineRecordStatus.REPROCESSED
        )

    def test_quarantine_resolve_not_found(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test quarantine resolve when record not found."""
        mock_unified_quarantine.update_status.return_value = False

        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "nonexistent",
                ],
            )

        assert result.exit_code != 0
        assert "Record not found: nonexistent" in result.output

    def test_quarantine_resolve_invalid_status(self, cli_runner: CliRunner):
        """Test quarantine resolve with invalid status."""
        result = cli_runner.invoke(
            cli,
            [
                "quarantine",
                "resolve",
                "--pipeline",
                "chembl_activity",
                "--payload-hash",
                "abc123",
                "--status",
                "INVALID_STATUS",
            ],
        )

        assert result.exit_code != 0
        # Click should show an error about invalid choice


# =============================================================================
# Integration-style tests
# =============================================================================


@pytest.mark.unit
class TestQuarantineCommandIntegration:
    """Integration-style tests for quarantine command workflows."""

    def test_inspect_then_resolve_workflow(
        self,
        cli_runner: CliRunner,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test inspect → resolve workflow."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(
            return_value=[
                {
                    "error_code": "VALIDATION_ERROR",
                    "payload": {"id": "123"},
                    "payload_hash": "hash_to_resolve",
                },
            ]
        )
        mock_unified_quarantine.update_status.return_value = True

        # Step 1: Inspect
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "inspect", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "VALIDATION_ERROR" in result.output

        # Step 2: Resolve the found record
        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "resolve",
                    "--pipeline",
                    "chembl_activity",
                    "--payload-hash",
                    "hash_to_resolve",
                    "--status",
                    "IGNORED",
                ],
            )

        assert result.exit_code == 0
        assert "marked as IGNORED" in result.output

    def test_stats_then_purge_workflow(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
        mock_unified_quarantine: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test stats → purge workflow."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 100,
                "by_error_code": {"OLD_ERROR": 80, "NEW_ERROR": 20},
                "by_status": {"NEW": 100},
            }
        )
        mock_unified_quarantine.purge.return_value = 80

        # Step 1: Check stats
        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli, ["quarantine", "stats", "--pipeline", "chembl_activity"]
            )

        assert result.exit_code == 0
        assert "Total Records: 100" in result.output

        # Step 2: Purge old records
        with (
            patch(
                "bioetl.infrastructure.config.Settings",
                return_value=mock_settings,
            ),
            patch(
                "bioetl.infrastructure.quarantine.unified.UnifiedQuarantine",
                return_value=mock_unified_quarantine,
            ),
        ):
            result = cli_runner.invoke(
                cli,
                [
                    "quarantine",
                    "purge",
                    "--pipeline",
                    "chembl_activity",
                    "--older-than-days",
                    "30",
                    "--force",
                ],
            )

        assert result.exit_code == 0
        assert "Purged 80 record(s)" in result.output


__all__ = [
    "TestQuarantineGroup",
    "TestQuarantineInspectCommand",
    "TestQuarantineStatsCommand",
    "TestQuarantineReplayCommand",
    "TestQuarantinePurgeCommand",
    "TestQuarantineResolveCommand",
    "TestQuarantineCommandIntegration",
]
