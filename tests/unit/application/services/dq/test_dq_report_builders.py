"""Focused unit tests for dq_report_builders helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pytest

from bioetl.application.services.dq.dq_report_builders import (
    build_summary,
    convert_value,
    run_serialized_checks,
    update_counts,
)
from bioetl.domain.value_objects.dq_report import (
    DQCheckStatus,
    DQReportStatus,
    RecordCountResult,
)


@dataclass(frozen=True)
class _SamplePayload:
    created_at: datetime
    status: DQCheckStatus
    items: tuple[int, ...]


@pytest.mark.unit
class TestDqReportBuilders:
    """Direct tests for generic DQ report helper functions."""

    def test_convert_value_serializes_dataclass_enum_datetime_and_collections(
        self,
    ) -> None:
        payload = _SamplePayload(
            created_at=datetime(2026, 3, 19, 10, 0, 0, tzinfo=UTC),
            status=DQCheckStatus.WARN,
            items=(1, 2, 3),
        )

        result = convert_value(
            {
                "payload": payload,
                "tags": {"levels": {DQCheckStatus.PASS, DQCheckStatus.FAIL}},
            }
        )

        assert result["payload"]["created_at"] == "2026-03-19T10:00:00+00:00"
        assert result["payload"]["status"] == DQCheckStatus.WARN.value
        assert result["payload"]["items"] == [1, 2, 3]
        assert sorted(result["tags"]["levels"]) == ["fail", "pass"]

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (DQCheckStatus.PASS, (2, 0, 0)),
            (DQCheckStatus.FAIL, (1, 1, 0)),
            (DQCheckStatus.WARN, (1, 0, 1)),
        ],
    )
    def test_update_counts_routes_status_to_expected_bucket(
        self,
        status: DQCheckStatus,
        expected: tuple[int, int, int],
    ) -> None:
        assert update_counts(status, 1, 0, 0) == expected

    def test_build_summary_prefers_failed_checks(self) -> None:
        result = build_summary(
            passed=3,
            failed=1,
            warnings=2,
            threshold_status=DQCheckStatus.WARN,
        )

        assert result.total_checks == 6
        assert result.overall_status == DQReportStatus.FAIL

    def test_build_summary_uses_threshold_warning_when_no_failed_checks(self) -> None:
        result = build_summary(
            passed=3,
            failed=0,
            warnings=0,
            threshold_status=DQCheckStatus.WARN,
        )

        assert result.overall_status == DQReportStatus.WARNING

    def test_build_summary_returns_pass_when_all_checks_pass(self) -> None:
        result = build_summary(
            passed=4,
            failed=0,
            warnings=0,
        )

        assert result.total_checks == 4
        assert result.overall_status == DQReportStatus.PASS

    def test_run_serialized_checks_updates_counts_and_payloads(self) -> None:
        checks: dict[str, object] = {}

        passed, failed, warnings = run_serialized_checks(
            enabled_checks={"record_count", "warn_count"},
            dispatch=[
                (
                    "record_count",
                    "record_count",
                    lambda: RecordCountResult(value=3, status=DQCheckStatus.PASS),
                ),
                (
                    "warn_count",
                    "warn_count",
                    lambda: RecordCountResult(value=2, status=DQCheckStatus.WARN),
                ),
                (
                    "skipped",
                    "skipped",
                    lambda: RecordCountResult(value=1, status=DQCheckStatus.FAIL),
                ),
            ],
            checks=checks,
            serialize_result=convert_value,
            passed=0,
            failed=0,
            warnings=0,
        )

        assert set(checks) == {"record_count", "warn_count"}
        assert checks["record_count"]["status"] == DQCheckStatus.PASS.value
        assert checks["warn_count"]["status"] == DQCheckStatus.WARN.value
        assert (passed, failed, warnings) == (1, 0, 1)
