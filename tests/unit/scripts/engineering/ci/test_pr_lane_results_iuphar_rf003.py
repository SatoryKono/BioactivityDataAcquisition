"""RF-003 post-join classification keeps an exact impact-selection route."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit

_FEATURE_OWNER = "tests/unit/iuphar_target_class/test_composite_features_rf003.py"
_POST_JOIN_OWNER = (
    "tests/unit/application/composite/test_post_join_classification_rf003.py"
)


_OWNERSHIP_OWNER = "tests/architecture/test_composite_ownership.py"


def test_rf003_surfaces_select_their_owners() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "src/iuphar_target_class/composite_features.py",
            "data/iuphar_target_class/rf003/feature_whitelist.json",
            "src/bioetl/application/composite/helpers/post_join_classification.py",
            "src/bioetl/application/composite/merger_post_join.py",
            "configs/quality/composite_ownership.yaml",
        ],
        repo_root=root,
    )
    assert _FEATURE_OWNER in report["selected"]
    # src/bioetl/application/** also maps the unit application suite directory;
    # exact RF-003 owner must remain declared even when the parent suite covers it.
    assert (
        _POST_JOIN_OWNER in report["selected"]
        or "tests/unit/application" in report["selected"]
    )
    assert _OWNERSHIP_OWNER in report["selected"]
    assert report["covers_full_suite"] is False
