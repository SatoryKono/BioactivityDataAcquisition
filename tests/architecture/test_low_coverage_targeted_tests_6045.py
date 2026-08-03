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
"""Closeout guard for targeted low-coverage tests added for issue #6045."""

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
CLOSEOUT = ROOT / "reports" / "quality" / "low-coverage-targeted-tests-6045.json"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_issue_6045_targeted_low_coverage_closeout_is_coherent() -> None:
    skip_if_module_coverage_inventory_is_dirty(
        root=ROOT,
        inventory_path=MODULE_COVERAGE,
    )
    closeout = _load_json(CLOSEOUT)
    inventory = _load_json(MODULE_COVERAGE)

    assert closeout["schema_version"] == "low-coverage-targeted-tests-6045-v1"
    assert closeout["issue"] == 6045
    assert closeout["debt_budget_policy"] == "flat_or_decreasing_only"
    assert closeout["closeout_decision"]["status"] == "closed-ready"
    assert (
        closeout["module_coverage_inventory_source_tree_sha256"]
        == inventory["source_tree_sha256"]
    )

    modules_by_name = {row["module"]: row for row in inventory["modules"]}
    targeted_modules = closeout["targeted_modules"]
    assert len(targeted_modules) >= 5

    for target in targeted_modules:
        inventory_row = modules_by_name[target["module"]]
        assert inventory_row["path"] == target["path"]
        assert isinstance(target["baseline_coverage_percent"], float | int)
        assert target["baseline_coverage_percent"] < 50
        assert target["covered_behaviors"], target["module"]
        assert (ROOT / target["path"]).exists(), target["path"]
        for test_path in target["targeted_tests"]:
            assert (ROOT / test_path).exists(), test_path

    validation = {row["status"] for row in closeout["validation"]}
    assert "pass" in validation
