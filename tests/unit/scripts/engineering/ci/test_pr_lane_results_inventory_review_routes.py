"""Keep inventory review snapshots on their bounded impact owners."""

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


def test_issue13285_inventory_decisions_keep_bounded_owners() -> None:
    path = "configs/quality/external_resource_inventory_issue13285_decisions.json"
    selected = affected_pytest_targets([path], repo_root=ROOT)
    assert OWNERS.issubset(selected)
    assert build_shadow_compare([path], repo_root=ROOT)["covers_full_suite"] is False
    with pytest.raises(ValueError, match="unmapped"):
        build_shadow_compare([path, UNKNOWN], repo_root=ROOT)


@pytest.mark.parametrize(
    "path",
    [
        "configs/quality/external_resource_inventory_pr13166_review_findings_review.json",
        "configs/quality/external_resource_inventory_pr13166_schema_selection_review.json",
        "configs/quality/external_resource_inventory_pr13166_assembly_ownership_review.json",
        "configs/quality/external_resource_inventory_pr13166_row_lifecycle_review.json",
        "configs/quality/external_resource_inventory_pr13166_replay_preflight_review.json",
        "configs/quality/external_resource_inventory_pr13166_eager_reader_review.json",
        "configs/quality/external_resource_inventory_pr13166_template_lifecycle_review.json",
        "configs/quality/external_resource_inventory_pr13166_workflow_replay_review.json",
        "configs/quality/external_resource_inventory_pr13166_batch_writer_review.json",
        "configs/quality/external_resource_inventory_pr13166_deferred_evidence_scope_review.json",
        "configs/quality/external_resource_inventory_pr13166_runtime_dq_review.json",
        "configs/quality/external_resource_inventory_pr13166_writer_boundaries_review.json",
    ],
)
def test_pr13166_inventory_review_snapshots_keep_bounded_owners(path: str) -> None:
    selected = affected_pytest_targets([path], repo_root=ROOT)
    assert OWNERS.issubset(selected)
    assert build_shadow_compare([path], repo_root=ROOT)["covers_full_suite"] is False
    with pytest.raises(ValueError, match="unmapped"):
        build_shadow_compare([path, UNKNOWN], repo_root=ROOT)


def test_target_replay_owner_keeps_lock_and_admission_coverage() -> None:
    selected = affected_pytest_targets(
        ["src/bioetl/composition/bootstrap/cli/lock.py"], repo_root=ROOT
    )
    owners = {
        "tests/unit/composition/bootstrap/test_lock_bootstrap.py",
        "tests/unit/composition/test_target_workflow_admission.py",
        "tests/unit/composition/test_target_classification_runtime.py",
    }
    assert all(
        any(
            owner == target or owner.startswith(target.rstrip("/") + "/")
            for target in selected
        )
        for owner in owners
    )
