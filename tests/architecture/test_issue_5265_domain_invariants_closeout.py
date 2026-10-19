# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Closeout evidence guard for issue #5265 domain invariant coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.architecture._module_coverage_inventory_support import (
    skip_if_artifact_is_not_authoritative,
    skip_if_module_coverage_inventory_is_dirty,
)


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "issue-5265-domain-invariants-closeout.json"
INVENTORY = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_5265_closeout_matches_live_module_coverage_inventory() -> None:
    skip_if_artifact_is_not_authoritative(root=ROOT, artifact_path=CLOSEOUT)
    skip_if_module_coverage_inventory_is_dirty(root=ROOT, inventory_path=INVENTORY)
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(INVENTORY)
    modules = {row["module"]: row for row in inventory["modules"]}
    tracked_rows = {
        module_name: modules[module_name]
        for module_name in closeout["module_expectations"]
    }

    assert (
        sum(1 for row in tracked_rows.values() if row["coverage_status"] == "uncovered")
        == closeout["current_metrics"]["tracked_uncovered_module_count"]
    )
    assert (
        sum(
            1 for row in tracked_rows.values() if row["coverage_status"] == "unmeasured"
        )
        == closeout["current_metrics"]["tracked_unmeasured_module_count"]
    )
    if closeout["status"] == "validated_local_closeable":
        assert closeout["debt_outcome"] == "improved"
        assert closeout["current_metrics"]["tracked_uncovered_module_count"] == 0
        assert closeout["current_metrics"]["tracked_unmeasured_module_count"] == 0
    else:
        assert closeout["debt_outcome"] == "current_inventory_regressed"
        assert (
            closeout["current_metrics"]["tracked_uncovered_module_count"] > 0
            or closeout["current_metrics"]["tracked_unmeasured_module_count"] > 0
        )

    for module_name, expectation in closeout["module_expectations"].items():
        row = modules[module_name]
        assert row["coverage_status"] == expectation, (module_name, row)
