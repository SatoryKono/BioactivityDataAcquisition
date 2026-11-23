"""RF-008 qualification keeps an exact impact-selection route."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit

_OWNER = "tests/unit/iuphar_target_class/test_rf008_qualification.py"


def test_rf008_qualification_selects_its_owner() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "src/iuphar_target_class/rf008_qualification.py",
            "data/iuphar_target_class/acceptance/rf008/profile.json",
        ],
        repo_root=root,
    )
    assert _OWNER in report["selected"]
    assert report["covers_full_suite"] is False
