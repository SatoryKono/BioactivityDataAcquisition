"""Deterministic retention enforcement tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from memory.retention import RetentionRecord, check_retention

pytestmark = pytest.mark.unit
_NOW = datetime(2026, 7, 29, tzinfo=UTC)


def test_report_exposes_nonzero_equivalent_for_expired_records() -> None:
    report = check_retention(
        [
            RetentionRecord(
                record_id="expired",
                created_at="2026-07-01T00:00:00Z",
                ttl_days=14,
            )
        ],
        now=_NOW,
    )

    assert report.ok is False
    assert report.exit_code == 1
    assert report.to_dict()["violation_count"] == 1
    assert report.violations[0].code == "retention_expired"


def test_report_is_green_before_explicit_retention_boundary() -> None:
    report = check_retention(
        [
            RetentionRecord(
                record_id="active",
                created_at="2026-07-20T00:00:00+00:00",
                ttl_days=14,
                retain_until="2026-08-15T00:00:00Z",
            )
        ],
        now=_NOW,
    )

    assert report.ok is True
    assert report.exit_code == 0


def test_governed_record_requires_explicit_ttl_or_retain_until() -> None:
    report = check_retention(
        [RetentionRecord(record_id="unbounded", created_at="2026-07-20T00:00:00Z")],
        now=_NOW,
    )

    assert report.violations[0].code == "missing_retention_policy"


@pytest.mark.parametrize(
    ("record", "code"),
    [
        (
            RetentionRecord(
                record_id="bad-created",
                created_at="2026-07-20T00:00:00",
                ttl_days=14,
            ),
            "invalid_created_at",
        ),
        (
            RetentionRecord(
                record_id="bad-ttl",
                created_at="2026-07-20T00:00:00Z",
                ttl_days=0,
            ),
            "invalid_ttl",
        ),
        (
            RetentionRecord(
                record_id="bad-retain",
                created_at="2026-07-20T00:00:00Z",
                retain_until="not-a-date",
            ),
            "invalid_retain_until",
        ),
    ],
)
def test_invalid_explicit_metadata_fails_closed(
    record: RetentionRecord,
    code: str,
) -> None:
    assert check_retention([record], now=_NOW).violations[0].code == code


def test_legal_hold_overrides_expiry_only_with_explicit_reason() -> None:
    held = RetentionRecord(
        record_id="held",
        created_at="2020-01-01T00:00:00Z",
        ttl_days=1,
        legal_hold=True,
        legal_hold_reason="Active investigation CASE-1",
    )
    missing_reason = RetentionRecord(
        record_id="invalid-hold",
        created_at="2020-01-01T00:00:00Z",
        ttl_days=1,
        legal_hold=True,
    )

    report = check_retention([held, missing_reason], now=_NOW)

    assert report.held_count == 1
    assert report.violations[0].code == "missing_legal_hold_reason"


def test_api_has_no_filesystem_mtime_fallback(tmp_path) -> None:
    unrelated = tmp_path / "old-record.json"
    unrelated.write_text("{}", encoding="utf-8")

    report = check_retention(
        [RetentionRecord(record_id="explicit", created_at="", ttl_days=14)],
        now=_NOW,
    )

    assert report.violations[0].code == "invalid_created_at"
