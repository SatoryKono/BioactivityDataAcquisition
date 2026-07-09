"""Closeout evidence guard for issue #5272 application core coverage debt."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.architecture._module_coverage_inventory_support import (
    skip_if_module_coverage_inventory_is_dirty,
)


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = (
    ROOT / "reports" / "quality" / "issue-5272-application-core-coverage-closeout.json"
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
    assert closeout["status"] in {
        "validated_local_closeable",
        "not_closeable_under_current_inventory",
    }
    assert closeout["debt_outcome"] in {"improved", "current_inventory_regressed"}
    if closeout["status"] == "validated_local_closeable":
        assert closeout["debt_outcome"] == "improved"
        assert (
            closeout["current_metrics"]["repo_uncovered_module_count"]
            < closeout["baseline_metrics"]["repo_uncovered_module_count"]
        )
        assert (
            closeout["current_metrics"]["application_core_covered_line_percent"]
            > closeout["baseline_metrics"]["application_core_covered_line_percent"]
        )
        # Application core must be zero for local closeout
        assert closeout["current_metrics"]["application_core_uncovered_module_count"] == 0
        assert closeout["current_metrics"]["application_core_unmeasured_module_count"] == 0
    else:
        assert closeout["debt_outcome"] == "current_inventory_regressed"
        assert (
            closeout["current_metrics"]["repo_uncovered_module_count"]
            >= closeout["baseline_metrics"]["repo_uncovered_module_count"]
            or closeout["current_metrics"]["application_core_covered_line_percent"]
            <= closeout["baseline_metrics"]["application_core_covered_line_percent"]
        )
    assert closeout["module_expectations"]
    evidence = set(closeout["evidence"])
    assert "reports/coverage/coverage.xml" not in evidence
    assert "reports/quality/module-coverage-inventory.json" in evidence
    assert "reports/quality/architecture-quality-scorecard.json" in evidence
    assert "configs/quality/module_coverage_gates.yaml" in evidence
    for evidence_path in closeout["evidence"]:
        assert (ROOT / str(evidence_path)).exists(), evidence_path

    inventory = _load_json(INVENTORY)
    assert inventory["coverage_xml_path"] == "reports/coverage/coverage.xml"
    assert (
        isinstance(inventory["coverage_xml_sha256"], str)
        and inventory["coverage_xml_sha256"]
    )


def test_issue_5272_closeout_matches_live_module_coverage_inventory() -> None:
    skip_if_module_coverage_inventory_is_dirty(root=ROOT, inventory_path=INVENTORY)
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    summary = inventory["summary"]
    application_core = summary["hotspot_family_coverage"]["application_core"]

    assert (
        summary["status_counts"]["uncovered"]
        == closeout["current_metrics"]["repo_uncovered_module_count"]
    )
    assert (
        summary["unmeasured_module_count"]
        == closeout["current_metrics"]["repo_unmeasured_module_count"]
    )
    assert (
        application_core["covered_line_percent"]
        == closeout["current_metrics"]["application_core_covered_line_percent"]
    )
    assert (
        application_core["status_counts"]["uncovered"]
        == closeout["current_metrics"]["application_core_uncovered_module_count"]
    )
    assert (
        application_core["unmeasured_module_count"]
        == closeout["current_metrics"]["application_core_unmeasured_module_count"]
    )
    if closeout["status"] == "validated_local_closeable":
        assert closeout["debt_outcome"] == "improved"
        # Application core metrics must be zero
        assert application_core["status_counts"]["uncovered"] == 0
        assert application_core["unmeasured_module_count"] == 0
        assert (
            application_core["covered_line_percent"]
            > closeout["baseline_metrics"]["application_core_covered_line_percent"]
        )
        # Repo-level metrics may have unmeasured modules outside application_core
        # This is acceptable for local closeout
    else:
        assert closeout["debt_outcome"] == "current_inventory_regressed"
        assert (
            summary["status_counts"]["uncovered"] > 0
            or summary["unmeasured_module_count"] > 0
            or application_core["status_counts"]["uncovered"] > 0
        )


def test_issue_5244_parent_epic_stays_open_until_default_floor_is_zero() -> None:
    skip_if_module_coverage_inventory_is_dirty(root=ROOT, inventory_path=INVENTORY)
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    below_default_floor = _below_default_floor_count(inventory)

    assert (
        below_default_floor
        == closeout["parent_epic_status"]["remaining_below_85_module_count"]
    )
    assert below_default_floor > 0
    assert (
        closeout["parent_epic_status"]["status"]
        == "not_closeable_under_current_definition_of_done"
    )
