# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface - product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""AUD-007 (#10597): retained public export facade count ratchets 4 -> 3.

The ``maintenance_api`` module stays a retained public entrypoint (it is still
part of the 12-row inventory), but it no longer carries a separate
``public_export_contract`` budget. Canonical maintenance symbol access is
governed by ``bioetl.composition.entrypoints`` and the owner-only
service-access seams.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architecture._platform_skip_support import mounted_worktree_skip_reason

pytestmark = [pytest.mark.architecture, pytest.mark.timeout(300)]

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "configs" / "quality" / "compatibility_facade_inventory.yaml"
SCORECARD = ROOT / "configs" / "quality" / "debt_scorecard.yaml"
MAINTENANCE_API_PATH = "src/bioetl/composition/maintenance_api.py"
EXPECTED_PUBLIC_EXPORT_FACADES = {
    "src/bioetl/composition/entrypoints.py",
    "src/bioetl/composition/health_api.py",
    "src/bioetl/infrastructure/config/__init__.py",
}
REVIEWED_PUBLIC_EXPORT_FACADE_COUNT = 3


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _inventory_rows() -> dict[str, dict[str, Any]]:
    inventory = _load_yaml(INVENTORY)
    return {
        str(row["path"]): row
        for row in inventory["retained_entrypoints"]
        if isinstance(row, dict)
    }


def test_issue_10597_maintenance_api_stays_retained_without_export_budget() -> None:
    rows = _inventory_rows()
    assert (ROOT / MAINTENANCE_API_PATH).exists()
    assert MAINTENANCE_API_PATH in rows, (
        "maintenance_api must stay a retained entrypoint"
    )
    row = rows[MAINTENANCE_API_PATH]
    assert "public_export_contract" not in row
    assert row["status"] == "public-entrypoint"
    assert row["sunset_status"] == "permanent"
    assert "bioetl.composition.entrypoints" in str(row["migration_path"])
    assert "#10597" in str(row["compatibility_role"])


def test_issue_10597_inventory_export_facade_rows_are_reviewed_three() -> None:
    rows = _inventory_rows()
    export_facades = {
        path for path, row in rows.items() if "public_export_contract" in row
    }
    assert export_facades == EXPECTED_PUBLIC_EXPORT_FACADES
    assert len(export_facades) == REVIEWED_PUBLIC_EXPORT_FACADE_COUNT
    assert len(rows) == 12

    inventory = _load_yaml(INVENTORY)
    exit_criteria = inventory["retained_compatibility_freeze_policy"]["exit_criteria"]
    assert any(
        "retained_public_export_facade_count" in str(item)
        and f"reviewed inventory count of {REVIEWED_PUBLIC_EXPORT_FACADE_COUNT}"
        in str(item)
        for item in exit_criteria
    )


def test_issue_10597_entrypoints_budget_does_not_grow() -> None:
    """Folding is done via existing seams; no export budget may increase."""
    rows = _inventory_rows()
    entrypoints_contract = rows["src/bioetl/composition/entrypoints.py"][
        "public_export_contract"
    ]
    assert entrypoints_contract["max_public_exports"] <= 10
    health_contract = rows["src/bioetl/composition/health_api.py"][
        "public_export_contract"
    ]
    assert health_contract["max_public_exports"] <= 7
    config_contract = rows["src/bioetl/infrastructure/config/__init__.py"][
        "public_export_contract"
    ]
    assert config_contract["max_public_exports"] <= 18


def test_issue_10597_debt_scorecard_current_count_is_three() -> None:
    scorecard = _load_yaml(SCORECARD)
    metric = scorecard["sanctioned_public_entrypoint_governance"]["metrics"][
        "public_export_facade_count"
    ]
    assert metric["current_count"] == REVIEWED_PUBLIC_EXPORT_FACADE_COUNT
    assert metric["linked_issue"] == "10597"


@pytest.mark.skipif(
    mounted_worktree_skip_reason() is not None,
    reason=mounted_worktree_skip_reason() or "",
)
def test_issue_10597_live_census_reports_three_public_export_facades() -> None:
    from scripts.engineering.qa.report_compatibility_importer_census import (
        build_compatibility_importer_census,
    )

    payload = build_compatibility_importer_census(ROOT, snapshot_date="2026-09-22")
    summary = payload["summary"]
    assert (
        summary["retained_public_export_facade_count"]
        == REVIEWED_PUBLIC_EXPORT_FACADE_COUNT
    )
    assert summary["retained_entrypoint_count"] == 12
    facade_paths = {
        str(row["path"])
        for row in payload["retained_public_export_facades"]
        if isinstance(row, dict)
    }
    assert facade_paths == EXPECTED_PUBLIC_EXPORT_FACADES
    retained_by_path = {
        str(row["path"]): row
        for row in payload["retained_entrypoints"]
        if isinstance(row, dict)
    }
    assert MAINTENANCE_API_PATH in retained_by_path
    assert "public_export_count" not in retained_by_path[MAINTENANCE_API_PATH]
