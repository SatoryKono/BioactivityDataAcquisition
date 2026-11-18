"""Keep pr13166 inventory review snapshots on their bounded impact owners."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    build_shadow_compare,
)

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[5]
OWNERS = {
    "tests/architecture/test_external_resource_inventory_catalog.py",
    "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
}
UNKNOWN = "configs/quality/external_resource_inventory_pr0_unreviewed.json"


@pytest.mark.parametrize(
    "path",
    [
        "configs/quality/external_resource_inventory_pr13166_review_findings_review.json",
        "configs/quality/external_resource_inventory_pr13166_schema_selection_review.json",
        "configs/quality/external_resource_inventory_pr13166_assembly_ownership_review.json",
    ],
)
def test_pr13166_inventory_review_snapshots_keep_bounded_owners(path: str) -> None:
    selected = affected_pytest_targets([path], repo_root=ROOT)
    assert OWNERS.issubset(selected)
    assert build_shadow_compare([path], repo_root=ROOT)["covers_full_suite"] is False
    with pytest.raises(ValueError, match="unmapped"):
        build_shadow_compare([path, UNKNOWN], repo_root=ROOT)
