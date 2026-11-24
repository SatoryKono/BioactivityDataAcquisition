"""The projection move retains its runtime, export and acceptance guards."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_projection_move_selects_real_consumers_without_a_kernel_catch_all():
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["src/iuphar_target_class/bioetl_input.py"],
        repo_root=root,
    )
    assert set(report["selected"]) == {
        "tests/unit/iuphar_target_class/test_composite_features_rf003.py",
        "tests/unit/iuphar_target_class/test_stage0_v2.py",
        "tests/unit/iuphar_target_class/test_integration_acceptance.py",
        "tests/unit/infrastructure/adapters/iuphar/test_target_classification.py",
        "tests/unit/infrastructure/adapters/iuphar/test_classification_evidence_boundaries.py",
    }
    assert report["covers_full_suite"] is False
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            ["src/iuphar_target_class/unreviewed_projection.py"], repo_root=root
        )
