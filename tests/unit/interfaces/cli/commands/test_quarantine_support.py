"""Unit tests for quarantine_support.py CLI helpers.

Tests quarantine inspection, stats display, replay, purge, and record resolution.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.domain.exceptions import BioETLError
from bioetl.interfaces.cli.commands.domains.quarantine.support import (
    _inspect_quarantine,
    _purge_quarantine,
    _replay_quarantine,
    _resolve_quarantine_record,
    _show_quarantine_stats,
)
from bioetl.interfaces.cli.exit_codes import ExitCode


def _make_runtime_service(
    records: list | None = None,
    stats: dict | None = None,
) -> MagicMock:
    """Create a mock quarantine runtime service."""
    runtime_service = MagicMock()
    runtime_service.inspect = AsyncMock(return_value=records or [])
    runtime_service.get_stats = AsyncMock(return_value=stats or {"total_count": 0})
    return runtime_service


def _make_service(
    replay_records: list | None = None,
    purge_count: int = 0,
    stats: dict | None = None,
    update_result: bool = True,
    mark_count: int = 0,
) -> MagicMock:
    """Create a mock quarantine service."""
    service = MagicMock()
    service.replay = MagicMock(return_value=replay_records or [])
    service.purge = MagicMock(return_value=purge_count)
    service.get_stats = AsyncMock(return_value=stats or {"total_count": 0})
    service.update_status = MagicMock(return_value=update_result)
    service.mark_as_reprocessed = MagicMock(return_value=mark_count)
    return service


@pytest.mark.unit
class TestInspectQuarantine:
    """Tests for _inspect_quarantine helper."""

    def test_empty_records_prints_no_records(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Test that empty inspection prints a 'no records' message."""
        runtime_service = _make_runtime_service(records=[])

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.echo_info"
        ) as mock_echo:
            _inspect_quarantine(
                runtime_service,
                pipeline="chembl_activity",
                limit=10,
                error_code=None,
            )

        calls = [str(c) for c in mock_echo.call_args_list]
        assert any("No records" in c for c in calls)

    def test_records_are_echoed(self) -> None:
        """Test that found records are echoed via echo_quarantine_record."""
        record = {"payload_hash": "abc123", "error_code": "VALIDATION_FAILED"}
        runtime_service = _make_runtime_service(records=[record])

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.echo_quarantine_record"
        ) as mock_echo:
            _inspect_quarantine(
                runtime_service,
                pipeline="chembl_activity",
                limit=10,
                error_code=None,
            )

        mock_echo.assert_called_once_with(record)
        runtime_service.inspect.assert_awaited_once_with(
            limit=10,
            error_code=None,
        )

    def test_inspect_quarantine__exits_with_fail__7998d39a(self) -> None:
        """Test that BioETLError during inspect exits with FAIL code."""
        runtime_service = MagicMock()
        runtime_service.inspect = AsyncMock(side_effect=BioETLError("inspect error"))

        with pytest.raises(SystemExit) as exc_info:
            _inspect_quarantine(
                runtime_service,
                pipeline="chembl_activity",
                limit=10,
                error_code=None,
            )

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestShowQuarantineStats:
    """Tests for _show_quarantine_stats helper."""

    def test_json_output_mode(self) -> None:
        """Test that output_json=True emits JSON to stdout."""
        stats = {"total_count": 5, "by_error_code": {"VALIDATION_FAILED": 5}}
        runtime_service = _make_runtime_service(stats=stats)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ) as mock_echo:
            _show_quarantine_stats(
                runtime_service,
                pipeline="chembl_activity",
                output_json=True,
                error_code=None,
            )

        output_calls = [str(c) for c in mock_echo.call_args_list]
        # Combined output should contain JSON-parseable content
        combined = " ".join(output_calls)
        assert "total_count" in combined or "VALIDATION_FAILED" in combined

    def test_dashboard_output_mode(self) -> None:
        """Test that output_json=False renders dashboard format."""
        stats = {
            "total_count": 10,
            "by_error_code": {"SCHEMA_ERROR": 10},
            "by_status": {"PENDING": 10},
        }
        runtime_service = _make_runtime_service(stats=stats)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ) as mock_echo:
            _show_quarantine_stats(
                runtime_service,
                pipeline="chembl_activity",
                output_json=False,
                error_code=None,
            )

        output = " ".join(str(c) for c in mock_echo.call_args_list)
        assert "chembl_activity" in output or "SCHEMA_ERROR" in output
        runtime_service.get_stats.assert_awaited_once_with(error_code=None, run_id=None)

    def test_run_scoped_stats_enrich_bronze_ratio(self) -> None:
        """Run-scoped stats should surface Bronze denominator when available."""
        stats = {
            "total_count": 4,
            "by_error_code": {"FILTERED_OUT_SILVER": 4},
            "by_status": {"NEW": 4},
            "silver_filter_rejects": {
                "total_count": 4,
                "by_reason_code": {"missing_required_field": 4},
                "by_field": {},
                "by_rule_type": {},
                "by_operator": {},
                "by_reason_code_field": {},
                "by_reason_signature": {},
            },
        }
        runtime_service = _make_runtime_service(stats=stats)
        run_manifest_service = MagicMock()
        run_manifest_service.show.return_value = MagicMock(
            ledger_entries=(MagicMock(metrics_snapshot={"records_bronze": 20}),)
        )

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ) as mock_echo:
            _show_quarantine_stats(
                runtime_service,
                pipeline="chembl_activity",
                output_json=False,
                error_code="FILTERED_OUT_SILVER",
                run_id="00000000-0000-0000-0000-000000000123",
                run_manifest_service=run_manifest_service,
            )

        output = " ".join(str(c) for c in mock_echo.call_args_list)
        assert "Run ID Scope: 00000000-0000-0000-0000-000000000123" in output
        assert "Silver Rejects vs Bronze: 4/20 (20.0%)" in output
        runtime_service.get_stats.assert_awaited_once_with(
            error_code="FILTERED_OUT_SILVER",
            run_id="00000000-0000-0000-0000-000000000123",
        )

    def test_show_quarantine_stats__exits_with_fail__57982ce2(self) -> None:
        """Test that BioETLError during stats fetch exits with FAIL code."""
        runtime_service = MagicMock()
        runtime_service.get_stats = AsyncMock(side_effect=BioETLError("stats error"))

        with pytest.raises(SystemExit) as exc_info:
            _show_quarantine_stats(
                runtime_service,
                pipeline="chembl_activity",
                output_json=False,
                error_code=None,
            )

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestReplayQuarantine:
    """Tests for _replay_quarantine helper."""

    def test_no_records_found_prints_message(self) -> None:
        """Test that no replay records prints informational message."""
        service = _make_service(replay_records=[])

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.echo_info"
        ) as mock_echo:
            _replay_quarantine(
                service,
                pipeline="chembl_activity",
                error_code=None,
                max_age_days=30,
                dry_run=False,
            )

        calls = [str(c) for c in mock_echo.call_args_list]
        assert any("No records" in c for c in calls)

    def test_dry_run_shows_preview_without_marking(self) -> None:
        """Test that dry_run=True shows preview and does NOT mark records."""
        records = [
            {"payload_hash": "abc123abc123abc1", "error_code": "VALIDATION_FAILED"},
            {"payload_hash": "def456def456def4", "error_code": "SCHEMA_ERROR"},
        ]
        service = _make_service(replay_records=records)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ):
            _replay_quarantine(
                service,
                pipeline="chembl_activity",
                error_code=None,
                max_age_days=30,
                dry_run=True,
            )

        service.mark_as_reprocessed.assert_not_called()

    def test_non_dry_run_marks_records(self) -> None:
        """Test that dry_run=False marks records as reprocessed."""
        records = [
            {"payload_hash": "abc123abc123abc1", "error_code": "VALIDATION_FAILED"}
        ]
        service = _make_service(replay_records=records, mark_count=1)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ):
            _replay_quarantine(
                service,
                pipeline="chembl_activity",
                error_code=None,
                max_age_days=30,
                dry_run=False,
            )

        service.mark_as_reprocessed.assert_called_once_with(records)


@pytest.mark.unit
class TestPurgeQuarantine:
    """Tests for _purge_quarantine helper."""

    def test_dry_run_shows_preview_without_purging(self) -> None:
        """Test that dry_run=True shows preview and does NOT call purge."""
        stats = {"total_count": 20}
        service = _make_service(stats=stats)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ):
            _purge_quarantine(
                service,
                pipeline="chembl_activity",
                older_than_days=30,
                dry_run=True,
                force=True,
            )

        service.purge.assert_not_called()

    def test_force_purge_skips_confirmation(self) -> None:
        """Test that force=True bypasses click.confirm prompt."""
        service = _make_service(purge_count=5)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.confirm"
        ) as mock_confirm:
            with patch(
                "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
            ):
                _purge_quarantine(
                    service,
                    pipeline="chembl_activity",
                    older_than_days=30,
                    dry_run=False,
                    force=True,
                )

        mock_confirm.assert_not_called()
        service.purge.assert_called_once_with(
            pipeline="chembl_activity", older_than_days=30
        )

    def test_purge_quarantine__exits_with_fail__2533ae55(self) -> None:
        """Test that BioETLError during purge exits with FAIL code."""
        service = MagicMock()
        service.get_stats = AsyncMock(return_value={"total_count": 0})
        service.purge = MagicMock(side_effect=BioETLError("purge error"))

        with pytest.raises(SystemExit) as exc_info:
            _purge_quarantine(
                service,
                pipeline="chembl_activity",
                older_than_days=30,
                dry_run=False,
                force=True,
            )

        assert exc_info.value.code == ExitCode.FAIL


@pytest.mark.unit
class TestResolveQuarantineRecord:
    """Tests for _resolve_quarantine_record helper."""

    def test_success_prints_confirmation(self) -> None:
        """Test that successful update prints confirmation message."""
        service = _make_service(update_result=True)

        with patch(
            "bioetl.interfaces.cli.commands.domains.quarantine.support.click.echo"
        ) as mock_echo:
            _resolve_quarantine_record(
                service,
                pipeline="chembl_activity",
                payload_hash="abc123",
                status="IGNORED",
            )

        calls = [str(c) for c in mock_echo.call_args_list]
        assert any("abc123" in c for c in calls)

    def test_record_not_found_exits_with_fail(self) -> None:
        """Test that not-found record exits with FAIL code."""
        service = _make_service(update_result=False)

        with pytest.raises(SystemExit) as exc_info:
            _resolve_quarantine_record(
                service,
                pipeline="chembl_activity",
                payload_hash="nonexistent",
                status="IGNORED",
            )

        assert exc_info.value.code == ExitCode.FAIL

    def test_quarantine_record__exits_with_fail__7414e68f(self) -> None:
        """Test that BioETLError during resolve exits with FAIL code."""
        service = MagicMock()
        service.update_status = MagicMock(side_effect=BioETLError("update error"))

        with pytest.raises(SystemExit) as exc_info:
            _resolve_quarantine_record(
                service,
                pipeline="chembl_activity",
                payload_hash="abc123",
                status="IGNORED",
            )

        assert exc_info.value.code == ExitCode.FAIL
