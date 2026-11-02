"""Shadow-compare route coverage for RF-003 safe evidence resolver surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_rf003_store_and_resolver() -> None:
    """Src RF-003 modules select unit layer dirs; docs keep sync+contracts."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "src/bioetl/infrastructure/control_plane/file_evidence_location_store.py",
            "src/bioetl/infrastructure/control_plane/evidence_location_path_safety.py",
            "src/bioetl/application/services/control_plane/evidence_location/resolver.py",
            "docs/04-reference/reports/run-reports.md",
        ],
        repo_root=repo_root,
    )
    assert report["covers_full_suite"] is False
    selected = report["selected"]
    assert "tests/unit/infrastructure" in selected
    assert "tests/unit/application" in selected
    assert "tests/architecture/test_documentation_sync.py" in selected
    assert "tests/unit/domain/run_reports/test_contracts.py" in selected


@pytest.mark.parametrize(
    "path",
    (
        "configs/quality/external_resource_inventory_pr12702_rf003_review.json",
        "configs/quality/external_resource_inventory_pr12702_rf003_arch_review.json",
    ),
)
def test_shadow_compare_routes_rf003_inventory_review(path: str) -> None:
    """COMP-004 RF-003 review JSON keeps catalog + requalify governing tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=repo_root)
    assert report["covers_full_suite"] is False
    selected = set(report["selected"])
    assert "tests/architecture/test_external_resource_inventory_catalog.py" in selected
    assert (
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py"
        in selected
    )
