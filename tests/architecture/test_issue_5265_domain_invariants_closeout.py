"""Closeout evidence guard for issue #5265 domain invariant coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "issue-5265-domain-invariants-closeout.json"
INVENTORY = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5265_closeout_artifact_has_expected_shape() -> None:
    closeout = _load_json(CLOSEOUT)

    assert closeout["issue"] == "#5265"
    assert closeout["status"] == "validated_local_closeable"
    assert closeout["debt_outcome"] == "improved"
    assert (
        closeout["current_metrics"]["uncovered_module_count"]
        < closeout["baseline_metrics"]["uncovered_module_count"]
    )
    assert closeout["module_expectations"]
    for evidence_path in closeout["evidence"]:
        assert (ROOT / str(evidence_path)).exists(), evidence_path


def test_issue_5265_closeout_matches_live_module_coverage_inventory() -> None:
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    modules = {row["module"]: row for row in inventory["modules"]}

    assert (
        inventory["summary"]["status_counts"]["uncovered"]
        == closeout["current_metrics"]["uncovered_module_count"]
    )
    assert (
        inventory["summary"]["unmeasured_module_count"]
        == closeout["current_metrics"]["unmeasured_module_count"]
    )

    for module_name, expectation in closeout["module_expectations"].items():
        row = modules[module_name]
        status = row["coverage_status"]
        if expectation == "fully_covered":
            assert status == "fully_covered", (module_name, row)
        elif expectation == "not_uncovered":
            assert status != "uncovered", (module_name, row)
        else:
            raise AssertionError(f"Unknown expectation {expectation!r}")
