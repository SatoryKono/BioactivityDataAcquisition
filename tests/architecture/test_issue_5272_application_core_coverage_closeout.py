"""Closeout evidence guard for issue #5272 application core coverage debt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = (
    ROOT
    / "reports"
    / "quality"
    / "issue-5272-application-core-coverage-closeout.json"
)
INVENTORY = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _below_default_floor_count(inventory: dict[str, Any]) -> int:
    return sum(
        1
        for row in inventory["modules"]
        if isinstance(row.get("coverage_percent"), (int, float))
        and float(row["coverage_percent"]) < 85.0
    )


def test_issue_5272_closeout_artifact_has_expected_shape() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["issue"] == "#5272"
    assert closeout["parent_epic"] == "#5244"
    assert closeout["status"] == "validated_local_closeable"
    assert closeout["debt_outcome"] == "improved"
    assert (
        closeout["current_metrics"]["repo_uncovered_module_count"]
        < closeout["baseline_metrics"]["repo_uncovered_module_count"]
    )
    assert (
        closeout["current_metrics"]["application_core_covered_line_percent"]
        > closeout["baseline_metrics"]["application_core_covered_line_percent"]
    )
    assert closeout["module_expectations"]
    for evidence_path in closeout["evidence"]:
        assert (ROOT / str(evidence_path)).exists(), evidence_path


def test_issue_5272_closeout_matches_live_module_coverage_inventory() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    summary = inventory["summary"]
    application_core = summary["hotspot_family_coverage"]["application_core"]

    assert (
        summary["status_counts"]["uncovered"]
        == closeout["current_metrics"]["repo_uncovered_module_count"]
        == 0
    )
    assert (
        summary["unmeasured_module_count"]
        == closeout["current_metrics"]["repo_unmeasured_module_count"]
        == 0
    )
    assert (
        application_core["covered_line_percent"]
        == closeout["current_metrics"]["application_core_covered_line_percent"]
    )
    assert (
        application_core["covered_line_percent"]
        > closeout["baseline_metrics"]["application_core_covered_line_percent"]
    )
    assert (
        application_core["status_counts"]["uncovered"]
        == closeout["current_metrics"]["application_core_uncovered_module_count"]
        == 0
    )
    assert (
        application_core["unmeasured_module_count"]
        == closeout["current_metrics"]["application_core_unmeasured_module_count"]
        == 0
    )


def test_issue_5244_parent_epic_stays_open_until_default_floor_is_zero() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    below_default_floor = _below_default_floor_count(inventory)

    assert below_default_floor == closeout["parent_epic_status"][
        "remaining_below_85_module_count"
    ]
    assert below_default_floor > 0
    assert (
        closeout["parent_epic_status"]["status"]
        == "not_closeable_under_current_definition_of_done"
    )
