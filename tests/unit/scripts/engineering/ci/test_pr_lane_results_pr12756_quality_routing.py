"""Focused shadow-compare routes for #12756 quality inputs."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_pr12756_quality_inputs() -> None:
    """PR #12756 inventory review and acceptance baseline keep explicit owners."""
    repo_root = Path(__file__).resolve().parents[5]
    expected = {
        "configs/quality/external_resource_inventory_pr12756_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
        "configs/quality/external_resource_inventory_pr12756_main_12748_review.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
        },
        "configs/quality/architecture_acceptance_baseline.yaml": {
            "tests/architecture/test_architecture_acceptance_baseline.py",
        },
    }
    for path, owning_tests in expected.items():
        selection = build_shadow_compare([path], repo_root=repo_root)
        assert owning_tests <= set(selection["selected"]), path
        assert selection["covers_full_suite"] is False
