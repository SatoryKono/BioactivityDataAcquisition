from __future__ import annotations

from scripts.engineering.qa.report_hotspot_family_baseline import (
    _budget_warnings_for_family,
    _resolve_snapshot_date,
)


def test_resolve_snapshot_date_prefers_reviewed_scorecard_snapshot() -> None:
    scorecard = {
        "hotspot_family_ratchets": {
            "snapshot_date": "2026-03-24",
        }
    }

    assert _resolve_snapshot_date(scorecard) == "2026-03-24"


def test_resolve_snapshot_date_falls_back_when_reviewed_snapshot_missing() -> None:
    scorecard = {
        "hotspot_family_ratchets": {},
    }

    snapshot_date = _resolve_snapshot_date(scorecard)

    assert isinstance(snapshot_date, str)
    assert len(snapshot_date) == 10


def test_budget_warnings_report_near_and_at_budget_metrics() -> None:
    family = {
        "files_ge_250_loc": 8,
        "max_internal_fan_in": 10,
        "bounded_growth_budgets": {
            "files_ge_250_loc": 10,
            "max_internal_fan_in": 10,
        },
    }

    assert _budget_warnings_for_family(family) == [
        "near_budget:files_ge_250_loc=8/10",
        "at_budget:max_internal_fan_in=10/10",
    ]


def test_budget_warnings_ignore_metrics_below_threshold() -> None:
    family = {
        "files_ge_250_loc": 7,
        "bounded_growth_budgets": {"files_ge_250_loc": 10},
    }

    assert _budget_warnings_for_family(family) == []
