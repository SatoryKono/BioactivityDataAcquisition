"""Closeout guards for branch coverage readiness issue #5978."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

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
def test_issue_5978_branch_coverage_deferred_with_promotion_criteria() -> None:
    """Branch coverage readiness is deferred with documented promotion criteria."""
    closeout = _load_json(CLOSEOUT)
    
    assert closeout["issue"]["number"] == 5978
    assert closeout["closeout"]["status"] == "deferred_with_promotion_criteria"
    
    # Verify current branch coverage state
    branch_state = closeout["current_branch_coverage_state"]
    assert branch_state["branch_rate_percent"] == 82.99
    assert branch_state["measurement_mode"] == "enabled"
    assert branch_state["policy"] == "advisory"
    
    # Verify gate requirements
    gate_reqs = closeout["branch_coverage_gate_requirements"]
    assert gate_reqs["hard_gate_threshold_percent"] == 85
    assert gate_reqs["current_policy"] == "advisory"
    assert len(gate_reqs["promotion_criteria"]) == 3
    
    # Verify deferred actions
    deferred = closeout["deferred_actions"]
    assert deferred["status"] == "deferred_until_stable_above_85"
    assert "85%" in deferred["rationale"]
    assert len(deferred["next_steps"]) > 0


@pytest.mark.architecture
def test_issue_5978_coverage_tail_status_documented() -> None:
    """Coverage tail status is documented and meets requirements."""
    closeout = _load_json(CLOSEOUT)
    module_coverage = _load_json(MODULE_COVERAGE)
    
    # Verify coverage tail status
    tail_status = closeout["coverage_tail_status"]
    assert tail_status["unmeasured_module_count"] == 0
    assert tail_status["uncovered_module_count"] == 0
    assert tail_status["below_85_module_count"] == 80
    assert tail_status["ranked_low_tail_modules"] == 6
    assert tail_status["owner_tests_status"] == "focused_owner_tests_added"
    
    # Verify alignment with module coverage inventory
    coverage_summary = module_coverage["summary"]
    assert coverage_summary["unmeasured_module_count"] == 0
    assert coverage_summary["uncovered_module_count"] == 0


@pytest.mark.architecture
def test_issue_5978_module_coverage_gates_policy_aligned() -> None:
    """Module coverage gates policy is aligned with closeout rationale."""
    closeout = _load_json(CLOSEOUT)
    gates_config = _load_yaml(MODULE_COVERAGE_GATES)
    
    # Verify branch coverage policy from gates config
    branch_config = gates_config["branch_coverage"]
    assert branch_config["measurement"] == "enabled"
    assert branch_config["policy"] == "advisory"
    assert branch_config["decision_date"] == "2026-06-17"
    
    # Verify promotion criteria match
    promotion_criteria = closeout["branch_coverage_gate_requirements"]["promotion_criteria"]
    gates_promotion = branch_config["promotion_criteria"]
    assert len(promotion_criteria) == len(gates_promotion)
    
    # Verify rationale mentions advisory policy
    rationale = closeout["closeout"]["rationale"]
    assert "advisory" in rationale.lower()
    assert "85%" in rationale


@pytest.mark.architecture
def test_issue_5978_evidence_paths_exist() -> None:
    """All documented evidence paths exist."""
    closeout = _load_json(CLOSEOUT)
    
    for evidence_path in closeout["evidence"]:
        path = ROOT / evidence_path
        assert path.exists(), f"Evidence path does not exist: {evidence_path}"
