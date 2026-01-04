"""Unit tests for quarantine.py CLI commands.

Tests quarantine management CLI commands including inspect, stats, replay, purge, and resolve.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from bioetl.domain.types import QuarantineRecordStatus
from bioetl.interfaces.cli import cli
from bioetl.interfaces.cli.exit_codes import ExitCode


@pytest.fixture
def cli_runner() -> CliRunner:
    """Create a Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_quarantine_manager() -> MagicMock:
    """Create a mock quarantine manager."""
    manager = MagicMock()
    manager.inspect = AsyncMock(return_value=[])
    manager.get_stats = AsyncMock(return_value={"total_count": 0})
    return manager


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.quarantine_path = "/tmp/quarantine"
    return settings


@pytest.fixture
def mock_unified_quarantine() -> MagicMock:
    """Create mock unified quarantine."""
    quarantine = MagicMock()
    quarantine.replay.return_value = iter([])
    quarantine.purge.return_value = 0
    quarantine.get_stats = AsyncMock(return_value={"total_count": 0})
    quarantine.update_status.return_value = True
    return quarantine


class TestQuarantineGroup:
    """Test the quarantine command group."""

    def test_quarantine_help_displays_subcommands(self, cli_runner: CliRunner) -> None:
        """Test that quarantine --help displays available subcommands."""
        result = cli_runner.invoke(cli, ["quarantine", "--help"])

        assert result.exit_code == 0
        assert "inspect" in result.output
        assert "stats" in result.output
        assert "replay" in result.output
        assert "purge" in result.output
        assert "resolve" in result.output
        assert "Manage quarantine" in result.output


class TestQuarantineInspect:
    """Test the quarantine inspect subcommand."""

    def test_inspect_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine inspect --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--limit" in result.output
        assert "--error-code" in result.output

    def test_inspect_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine inspect requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "inspect"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_inspect_empty_quarantine(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine inspect with no records."""
        mock_quarantine_manager.inspect = AsyncMock(return_value=[])

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "No records found" in result.output

    def test_inspect_with_records(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine inspect with existing records."""
        sample_records = [
            {
                "error_code": "VALIDATION_ERROR",
                "payload": {"molecule_id": "CHEMBL123"},
            },
            {
                "error_code": "SCHEMA_MISMATCH",
                "payload": {"molecule_id": "CHEMBL456"},
            },
        ]
        mock_quarantine_manager.inspect = AsyncMock(return_value=sample_records)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "inspect", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "VALIDATION_ERROR" in result.output
        assert "SCHEMA_MISMATCH" in result.output

    def test_inspect_with_error_code_filter(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine inspect with --error-code filter."""
        mock_quarantine_manager.inspect = AsyncMock(return_value=[])

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
                    "DQ_MISSING_FIELD",
                ],
            )

        # Verify inspect was called with correct error_code
        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=100, error_code="DQ_MISSING_FIELD"
        )
        assert result.exit_code == 0

    def test_inspect_with_custom_limit(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine inspect with custom --limit."""
        mock_quarantine_manager.inspect = AsyncMock(return_value=[])

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

        mock_quarantine_manager.inspect.assert_called_once_with(
            limit=50, error_code=None
        )
        assert result.exit_code == 0


class TestQuarantineStats:
    """Test the quarantine stats subcommand."""

    def test_stats_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine stats --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "stats", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--json" in result.output

    def test_stats_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine stats requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "stats"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_stats_empty_quarantine(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine stats with no records."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={"total_count": 0, "by_error_code": {}, "by_status": {}}
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Total Records: 0" in result.output

    def test_stats_with_records(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine stats with records."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={
                "total_count": 100,
                "by_error_code": {"VALIDATION_ERROR": 60, "SCHEMA_ERROR": 40},
                "by_status": {"NEW": 80, "REVIEWED": 20},
            }
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Total Records: 100" in result.output
        assert "VALIDATION_ERROR" in result.output
        assert "60.0%" in result.output
        assert "By Error Code:" in result.output
        assert "By Status:" in result.output

    def test_stats_json_output(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine stats with JSON output."""
        stats_data = {
            "total_count": 50,
            "by_error_code": {"DQ_MISSING": 30, "DQ_INVALID": 20},
            "by_status": {"NEW": 40, "RESOLVED": 10},
        }
        mock_quarantine_manager.get_stats = AsyncMock(return_value=stats_data)

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity", "--json"],
            )

        assert result.exit_code == 0
        # Parse JSON output
        output_json = json.loads(result.output)
        assert output_json["total_count"] == 50
        assert output_json["by_error_code"]["DQ_MISSING"] == 30

    def test_stats_exception_handling(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine stats handles exceptions."""
        mock_quarantine_manager.get_stats = AsyncMock(
            side_effect=Exception("Database error")
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == ExitCode.FAIL.value
        assert "Failed to get stats" in result.output

    def test_stats_dashboard_header(
        self,
        cli_runner: CliRunner,
        mock_quarantine_manager: MagicMock,
    ) -> None:
        """Test quarantine stats displays dashboard header."""
        mock_quarantine_manager.get_stats = AsyncMock(
            return_value={"total_count": 0, "by_error_code": {}, "by_status": {}}
        )

        with patch(
            "bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager",
            return_value=mock_quarantine_manager,
        ):
            result = cli_runner.invoke(
                cli,
                ["quarantine", "stats", "--pipeline", "chembl_activity"],
            )

        assert "Quarantine Dashboard: chembl_activity" in result.output
        assert "=" * 50 in result.output


class TestQuarantineReplay:
    """Test the quarantine replay subcommand."""

    def test_replay_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine replay --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "replay", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--error-code" in result.output
        assert "--max-age-days" in result.output
        assert "--dry-run" in result.output

    def test_replay_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine replay requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "replay"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_replay_no_records(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay with no records."""
        mock_unified_quarantine.replay.return_value = iter([])

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
        assert "No records found for replay" in result.output

    def test_replay_dry_run(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay in dry-run mode."""
        mock_records = [
            {"error_code": "DQ_ERROR", "payload_hash": "abc123def456"},
            {"error_code": "DQ_ERROR", "payload_hash": "xyz789uvw012"},
        ]
        mock_unified_quarantine.replay.return_value = iter(mock_records)

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
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would replay 2 record(s)" in result.output
        assert "abc123def456" in result.output

    def test_replay_dry_run_many_records(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay dry-run with many records shows truncation."""
        # Create 15 records to test truncation (shows first 10 + "... and N more")
        mock_records = [
            {"error_code": f"DQ_ERROR_{i}", "payload_hash": f"hash{i:03d}"}
            for i in range(15)
        ]
        mock_unified_quarantine.replay.return_value = iter(mock_records)

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
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would replay 15 record(s)" in result.output
        assert "... and 5 more" in result.output

    def test_replay_actual_replay(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay actually marks records as reprocessed."""
        mock_records = [
            {"error_code": "DQ_ERROR", "payload_hash": "abc123"},
            {"error_code": "DQ_ERROR", "payload_hash": "def456"},
        ]
        mock_unified_quarantine.replay.return_value = iter(mock_records)
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
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        assert result.exit_code == 0
        assert "Replaying 2 record(s)" in result.output
        assert "Marked 2 record(s) as REPROCESSED" in result.output
        # Verify update_status was called for each record
        assert mock_unified_quarantine.update_status.call_count == 2

    def test_replay_with_error_code_filter(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay with error code filter."""
        mock_unified_quarantine.replay.return_value = iter([])

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
                    "DQ_NETWORK_ERROR",
                ],
            )

        # Command should execute without error
        assert result.exit_code == 0

    def test_replay_with_max_age_days(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine replay with custom max-age-days."""
        mock_unified_quarantine.replay.return_value = iter([])

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
                ],
            )

        # Command should execute without error
        assert result.exit_code == 0
        # Verify replay was called
        mock_unified_quarantine.replay.assert_called_once()


class TestQuarantinePurge:
    """Test the quarantine purge subcommand."""

    def test_purge_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine purge --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "purge", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--older-than-days" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output

    def test_purge_requires_pipeline(self, cli_runner: CliRunner) -> None:
        """Test that quarantine purge requires --pipeline option."""
        result = cli_runner.invoke(cli, ["quarantine", "purge"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_purge_dry_run(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine purge in dry-run mode."""
        mock_unified_quarantine.get_stats = AsyncMock(return_value={"total_count": 50})

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
                ["quarantine", "purge", "--pipeline", "chembl_activity", "--dry-run"],
            )

        assert result.exit_code == 0
        assert "Would purge records older than 30 days" in result.output
        assert "Current total in quarantine: 50" in result.output
        assert "Use without --dry-run" in result.output

    def test_purge_with_confirmation(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine purge with confirmation prompt."""
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
            # Simulate user confirming with 'y'
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="y\n",
            )

        assert result.exit_code == 0
        assert "Purged 25 record(s)" in result.output

    def test_purge_confirmation_abort(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine purge aborts on negative confirmation."""
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
            # Simulate user aborting with 'n'
            result = cli_runner.invoke(
                cli,
                ["quarantine", "purge", "--pipeline", "chembl_activity"],
                input="n\n",
            )

        # Should abort
        assert result.exit_code == 1
        assert "Aborted" in result.output

    def test_purge_with_force(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine purge with --force skips confirmation."""
        mock_unified_quarantine.purge.return_value = 30

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
                ["quarantine", "purge", "--pipeline", "chembl_activity", "--force"],
            )

        assert result.exit_code == 0
        assert "Purged 30 record(s)" in result.output
        # Verify purge was called
        mock_unified_quarantine.purge.assert_called_once()

    def test_purge_custom_older_than_days(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine purge with custom --older-than-days."""
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
        # Verify purge was called with older_than_days=60
        mock_unified_quarantine.purge.assert_called_once()
        call_kwargs = mock_unified_quarantine.purge.call_args.kwargs
        assert call_kwargs.get("older_than_days") == 60


class TestQuarantineResolve:
    """Test the quarantine resolve subcommand."""

    def test_resolve_help_displays_options(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve --help displays options."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve", "--help"])

        assert result.exit_code == 0
        assert "--pipeline" in result.output
        assert "--payload-hash" in result.output
        assert "--status" in result.output
        assert "IGNORED" in result.output
        assert "REPROCESSED" in result.output

    def test_resolve_requires_pipeline_and_hash(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve requires --pipeline and --payload-hash."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_resolve_requires_payload_hash(self, cli_runner: CliRunner) -> None:
        """Test that quarantine resolve requires --payload-hash."""
        result = cli_runner.invoke(cli, ["quarantine", "resolve", "--pipeline", "test"])

        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_resolve_success_default_status(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test quarantine resolve with default IGNORED status."""
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
        assert "Record abc123def456 marked as IGNORED" in result.output
        mock_unified_quarantine.update_status.assert_called_once_with(
            "abc123def456", QuarantineRecordStatus.IGNORED
        )

    def test_resolve_with_reprocessed_status(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
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
                    "xyz789",
                    "--status",
                    "REPROCESSED",
                ],
            )

        assert result.exit_code == 0
        assert "Record xyz789 marked as REPROCESSED" in result.output
        mock_unified_quarantine.update_status.assert_called_once_with(
            "xyz789", QuarantineRecordStatus.REPROCESSED
        )

    def test_resolve_record_not_found(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
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

        assert result.exit_code == ExitCode.FAIL.value
        assert "Record not found: nonexistent" in result.output

    def test_resolve_invalid_status(self, cli_runner: CliRunner) -> None:
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
        # Click should reject invalid choice
        assert (
            "Invalid value" in result.output
            or "invalid choice" in result.output.lower()
        )


class TestQuarantineEdgeCases:
    """Test edge cases and error handling for quarantine commands."""

    @patch("bioetl.interfaces.cli.commands.quarantine.get_quarantine_manager")
    def test_inspect_displays_info_message(
        self,
        mock_get_manager: MagicMock,
        cli_runner: CliRunner,
    ) -> None:
        """Test that inspect displays informational message."""
        mock_manager = MagicMock()
        mock_manager.inspect = AsyncMock(return_value=[])
        mock_get_manager.return_value = mock_manager

        result = cli_runner.invoke(
            cli,
            ["quarantine", "inspect", "--pipeline", "test_pipeline", "--limit", "50"],
        )

        assert "Inspecting quarantine for test_pipeline (limit 50)" in result.output

    def test_replay_record_without_payload_hash(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test replay handles records without payload_hash."""
        # Record without payload_hash
        mock_records = [{"error_code": "DQ_ERROR"}]
        mock_unified_quarantine.replay.return_value = iter(mock_records)
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
                ["quarantine", "replay", "--pipeline", "chembl_activity"],
            )

        # Should not crash, but update_status won't be called for records without hash
        assert result.exit_code == 0

    def test_replay_dry_run_shows_hash_truncated(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test replay dry-run truncates long payload hashes."""
        long_hash = "a" * 64  # SHA256 hash length
        mock_records = [{"error_code": "DQ_ERROR", "payload_hash": long_hash}]
        mock_unified_quarantine.replay.return_value = iter(mock_records)

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
                ["quarantine", "replay", "--pipeline", "chembl_activity", "--dry-run"],
            )

        # Hash should be truncated to first 16 chars + "..."
        assert "aaaaaaaaaaaaaaaa..." in result.output

    def test_purge_dry_run_custom_days(
        self,
        cli_runner: CliRunner,
        mock_settings: MagicMock,
        mock_unified_quarantine: MagicMock,
    ) -> None:
        """Test purge dry-run shows custom older-than-days."""
        mock_unified_quarantine.get_stats = AsyncMock(return_value={"total_count": 100})

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

        assert "Would purge records older than 90 days" in result.output
