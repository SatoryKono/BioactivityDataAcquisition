"""Closeout guards for branch coverage readiness issue #5978."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.architecture._module_coverage_inventory_support import (
    skip_if_module_coverage_inventory_is_dirty,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5978-closeout.json"
MODULE_COVERAGE_GATES = ROOT / "configs" / "quality" / "module_coverage_gates.yaml"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    import yaml

    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


@pytest.mark.architecture
def test_issue_5978_branch_coverage_is_promoted_to_hard_gate() -> None:
    """Branch coverage readiness is promoted to the coverage-verify hard gate."""
    closeout = _load_json(CLOSEOUT)

    assert closeout["issue"]["number"] == 5978
    assert closeout["closeout"]["status"] == "closeable"

    # Verify current branch coverage state
    branch_state = closeout["current_branch_coverage_state"]
    assert branch_state["branch_rate_percent"] == 85.002
    assert branch_state["branch_covered"] == 17218
    assert branch_state["branch_total"] == 20256
    assert branch_state["branch_threshold_margin"] == 0
    assert branch_state["measurement_mode"] == "enabled"
    assert branch_state["policy"] == "blocking"

    # Verify gate requirements
    gate_reqs = closeout["branch_coverage_gate_requirements"]
    assert gate_reqs["hard_gate_threshold_percent"] == 85
    assert gate_reqs["current_policy"] == "blocking"
    assert len(gate_reqs["promotion_criteria"]) == 3

    stability = closeout["stability_evidence"]
    assert stability["status"] == "passed"
    assert len(stability["consecutive_checks"]) == 3
    assert all(check["status"] == "pass" for check in stability["consecutive_checks"])


@pytest.mark.architecture
def test_issue_5978_coverage_tail_status_documented() -> None:
    """Coverage tail status is documented and meets requirements."""
    skip_if_module_coverage_inventory_is_dirty(
        root=ROOT,
        inventory_path=MODULE_COVERAGE,
    )
    closeout = _load_json(CLOSEOUT)
    module_coverage = _load_json(MODULE_COVERAGE)

    # Verify coverage tail status
    tail_status = closeout["coverage_tail_status"]
    assert tail_status["unmeasured_module_count"] == 0
    assert tail_status["uncovered_module_count"] == 0
    assert tail_status["below_85_branch_file_count"] == 552
    assert tail_status["ranked_low_tail_modules"] == 6
    assert tail_status["owner_tests_status"] == "focused_owner_tests_added"

    # The closeout captures the historical ceiling. Current coverage may improve,
    # but it must not grow the documented low-coverage tail.
    coverage_summary = module_coverage["summary"]
    below_85 = [
        row
        for row in module_coverage["modules"]
        if row["coverage_percent"] is not None and row["coverage_percent"] < 85
    ]
    assert len(below_85) <= tail_status["below_85_module_count"]
    assert (
        coverage_summary["unmeasured_module_count"]
        <= tail_status["unmeasured_module_count"]
    )
    assert (
        coverage_summary["uncovered_module_count"]
        <= tail_status["uncovered_module_count"]
    )


@pytest.mark.architecture
def test_issue_5978_module_coverage_gates_policy_aligned() -> None:
    """Module coverage gates policy is aligned with closeout rationale."""
    closeout = _load_json(CLOSEOUT)
    gates_config = _load_yaml(MODULE_COVERAGE_GATES)

    # Verify branch coverage policy from gates config
    branch_config = gates_config["branch_coverage"]
    assert branch_config["measurement"] == "enabled"
    assert branch_config["policy"] == "blocking"
    assert branch_config["decision_date"] == "2026-07-06"
    assert branch_config["hard_gate_threshold_percent"] == 85

    # Verify promotion criteria match
    promotion_criteria = closeout["branch_coverage_gate_requirements"][
        "promotion_criteria"
    ]
    gates_promotion = branch_config["promotion_criteria"]
    assert len(promotion_criteria) == len(gates_promotion)

    # Verify rationale mentions the hard gate policy
    rationale = closeout["closeout"]["rationale"]
    assert "blocking" in rationale.lower()
    assert "check-branch-coverage" in rationale


@pytest.mark.architecture
def test_issue_5978_evidence_paths_exist() -> None:
    """All documented evidence paths exist."""
    closeout = _load_json(CLOSEOUT)

    for evidence_path in closeout["evidence"]:
        path = ROOT / evidence_path
        assert path.exists(), f"Evidence path does not exist: {evidence_path}"


@pytest.mark.architecture
def test_issue_5983_branch_gate_promotion_evidence_is_current() -> None:
    """Issue #5983 has explicit hard-gate promotion evidence."""
    evidence = _load_json(ROOT / "reports/quality/branch-coverage-gate-evidence.json")
    gates_config = _load_yaml(MODULE_COVERAGE_GATES)

    assert evidence["linked_issue"] == 5983
    assert evidence["promotion_status"] == "promoted_to_blocking_gate"
    assert evidence["branch_rate_percent"] == 85.002
    assert evidence["branch_covered"] == 17218
    assert evidence["branch_total"] == 20256
    assert evidence["required_branch_covered"] == 17218
    assert evidence["threshold_margin"] == 0
    assert len(evidence["consecutive_checks"]) == 3
    assert all(check["status"] == "pass" for check in evidence["consecutive_checks"])
    assert gates_config["branch_coverage"]["policy"] == "blocking"
    assert "check-branch-coverage" in evidence["gate_command"]
