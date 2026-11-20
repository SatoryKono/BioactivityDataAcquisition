"""Owned-hook evidence keeps bounded CI owners and unknown reports fail closed."""

from __future__ import annotations


from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("suffix", ["acceptance.md", "evidence.json"])
def test_owned_hook_evidence_selects_actual_guard_regressions(suffix: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [f"reports/review/ai-rules-epic-13056-{suffix}"], repo_root=root
    )
    for test in (
        "tests/unit/scripts/test_coalesced_precommit.py",
        "tests/unit/scripts/test_parallel_precommit.py",
        "tests/unit/scripts/test_partitioned_diff.py",
        "tests/unit/scripts/test_readonly_message.py",
        "tests/unit/scripts/test_owned_guard_execution.py",
        "tests/unit/scripts/repo/test_hook_receipts.py",
        "tests/unit/scripts/repo/test_check_no_partial_tree.py",
    ):
        assert test in report["selected"]


def test_other_owned_hook_evidence_stays_unmapped() -> None:
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            ["reports/review/ai-rules-epic-13056-unreviewed.json"],
            repo_root=Path(__file__).resolve().parents[5],
        )
