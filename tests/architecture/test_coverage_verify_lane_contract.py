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
"""coverage-verify lane contract (T-TEST-006 / #6777)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_MATRIX = _REPO / "configs/quality/test_matrix.yaml"
_WORKFLOW = _REPO / ".github/workflows/tests.yml"


@pytest.mark.architecture
def test_coverage_verify_lane_is_hard_merge_truth() -> None:
    """coverage-verify remains a named hard-merge lane with branch enforcement."""
    matrix = yaml.safe_load(_MATRIX.read_text(encoding="utf-8"))
    authority = matrix["test_lanes"]["authority_model"]
    assert "coverage-verify" in authority["hard_merge_truth"]
    assert "branch_coverage" in authority["hard_merge_truth"]


@pytest.mark.architecture
def test_coverage_verify_workflow_enforces_line_and_branch() -> None:
    """Workflow must keep fail-under=85 and check-branch-coverage min 85."""
    text = _WORKFLOW.read_text(encoding="utf-8")
    assert "coverage-verify" in text or "fail-under=85" in text
    assert "check-branch-coverage" in text
    assert "--min-percent 85" in text
    assert "fail-under=85" in text


@pytest.mark.architecture
def test_coverage_candidate_producer_precedes_required_currentness_gate() -> None:
    """First trusted refresh must not deadlock on its own stale-artifact check."""
    text = _WORKFLOW.read_text(encoding="utf-8")
    producer_start = text.index("  coverage-verify:\n")
    currentness_start = text.index("  coverage-inventory-currentness:\n")
    producer = text[producer_start:currentness_start]
    currentness = text[currentness_start:]

    assert "module-coverage-inventory.candidate.json" in producer
    assert "cmp --silent" not in producer
    assert "needs: coverage-verify" in currentness
    assert "cmp --silent" in currentness


@pytest.mark.architecture
def test_skip_inventory_policy_forbids_assertion_weakening() -> None:
    """Collection/flake remediation must not heal via assertion weakening."""
    e2e_slo = yaml.safe_load(
        (_REPO / "configs/quality/e2e_skip_rate_slo.yaml").read_text(encoding="utf-8")
    )
    assert e2e_slo["policy"]["forbid_assertion_weakening"] is True
    assert e2e_slo["policy"]["forbid_retries_to_heal_flakes"] is True
