from __future__ import annotations

from scripts.engineering.qa.report_hotspot_family_baseline import _resolve_snapshot_date


def test_resolve_snapshot_date_prefers_reviewed_scorecard_snapshot() -> None:
    scorecard = {
        "report_only_hotspot_families": {
            "snapshot_date": "2026-03-24",
        }
    }

    assert _resolve_snapshot_date(scorecard) == "2026-03-24"


def test_resolve_snapshot_date_falls_back_when_reviewed_snapshot_missing() -> None:
    scorecard = {
        "report_only_hotspot_families": {},
    }

    snapshot_date = _resolve_snapshot_date(scorecard)

    assert isinstance(snapshot_date, str)
    assert len(snapshot_date) == 10
