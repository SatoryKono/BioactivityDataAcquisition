from __future__ import annotations

import pytest

from scripts.engineering.qa.report_hotspot_family_baseline import (
    _budget_review_notes_for_family,
    _budget_warnings_for_family,
    _merge_reviewed_baseline_metrics,
    _resolve_snapshot_date,
)

pytestmark = pytest.mark.unit


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


def test_budget_warnings_report_only_exceeded_budget_metrics() -> None:
    family = {
        "files_ge_250_loc": 11,
        "max_internal_fan_in": 10,
        "bounded_growth_budgets": {
            "files_ge_250_loc": 10,
            "max_internal_fan_in": 10,
        },
    }

    assert _budget_warnings_for_family(family) == ["over_budget:files_ge_250_loc=11/10"]


def test_budget_warnings_ignore_metrics_at_or_below_budget() -> None:
    family = {
        "files_ge_250_loc": 10,
        "bounded_growth_budgets": {"files_ge_250_loc": 10},
    }

    assert _budget_warnings_for_family(family) == []


def test_budget_review_notes_report_near_and_at_budget_metrics() -> None:
    family = {
        "files_ge_250_loc": 8,
        "max_internal_fan_in": 10,
        "bounded_growth_budgets": {
            "files_ge_250_loc": 10,
            "max_internal_fan_in": 10,
        },
    }

    assert _budget_review_notes_for_family(family) == [
        "near_budget:files_ge_250_loc=8/10",
        "at_budget:max_internal_fan_in=10/10",
    ]


def test_merge_reviewed_baseline_metrics_preserves_live_measured_census() -> None:
    family = {
        "name": "application_services_control_plane",
        "ratchet_stage": "reviewed-baseline",
        "metrics": {
            "duplication_clusters": 17,
            "files": 66,
            "total_loc": 12998,
            "files_ge_250_loc": 22,
            "helper_function_ratio": 0.496,
            "max_internal_fan_in": 6,
            "max_internal_fan_in_module": "bioetl.application.services.control_plane.helpers",
        },
    }
    measured = {
        "name": "application_services_control_plane",
        "duplication_clusters": 17,
        "files": 71,
        "total_loc": 13453,
        "files_ge_250_loc": 21,
        "helper_function_ratio": 0.499,
        "max_internal_fan_in": 6,
        "max_internal_fan_in_module": "bioetl.application.services.control_plane.helpers",
    }

    merged = _merge_reviewed_baseline_metrics(family=family, measured=measured)

    assert merged["files"] == 71
    assert merged["total_loc"] == 13453
    assert merged["files_ge_250_loc"] == 21
    assert merged["helper_function_ratio"] == 0.499


def test_merge_reviewed_baseline_metrics_preserves_live_metrics_for_active_family() -> (
    None
):
    family = {
        "name": "composition_bootstrap_runtime",
        "ratchet_stage": "active",
        "metrics": {"files_ge_250_loc": 99},
    }
    measured = {
        "name": "composition_bootstrap_runtime",
        "files_ge_250_loc": 5,
    }

    merged = _merge_reviewed_baseline_metrics(family=family, measured=measured)

    assert merged["files_ge_250_loc"] == 5
