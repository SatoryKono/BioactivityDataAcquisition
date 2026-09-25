"""UTC age for active non-canonical evidence summaries (#11199)."""

from __future__ import annotations

from datetime import UTC, date, datetime

from scripts.docs.checks.check_drift import _utc_evidence_age_days


def test_evidence_age_uses_pinned_day() -> None:
    assert _utc_evidence_age_days(date(2026, 9, 25), today=date(2026, 9, 26)) == 1


def test_evidence_age_defaults_to_utc_date(monkeypatch) -> None:
    class _FrozenDateTime:
        @staticmethod
        def now(tz):
            assert tz is UTC
            return datetime(2026, 9, 26, 0, 30, tzinfo=UTC)

    monkeypatch.setattr(
        "scripts.docs.checks.check_drift.datetime",
        _FrozenDateTime,
    )
    assert _utc_evidence_age_days(date(2026, 9, 25)) == 1
