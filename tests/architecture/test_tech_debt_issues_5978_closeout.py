"""Closeout guards for branch coverage readiness issue #5978."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5978-closeout.json"
MODULE_COVERAGE = ROOT / "reports" / "quality" / "module-coverage-inventory.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


@pytest.mark.architecture
def test_issue_5978_branch_coverage_readiness_deferred() -> None:
    """Branch coverage readiness is deferred with documented improvement plan."""
    closeout = _load_json(CLOSEOUT)
    
    assert closeout["issue"]["number"] == 5978
    assert closeout["closeout"]["status"] == "deferred_with_branch_coverage_plan"
    
    # Verify rationale explains the deferral and improvement plan
    rationale = closeout["closeout"]["rationale"]
    assert "branch coverage" in rationale.lower()
    assert "deferred" in rationale.lower()
    assert "improvement plan" in rationale.lower() or "analysis task" in rationale.lower()
    
    # Verify required evidence is documented
    branch_analysis = closeout["branch_coverage_analysis"]
    assert branch_analysis["status"] == "deferred_for_dedicated_analysis"
    assert len(branch_analysis["required_evidence"]) > 0


@pytest.mark.architecture
def test_issue_5978_current_coverage_state_documented() -> None:
    """Current line coverage state is documented for reference."""
    closeout = _load_json(CLOSEOUT)
    module_coverage = _load_json(MODULE_COVERAGE)
    
    # Verify closeout references current coverage state
    coverage_state = closeout["current_coverage_state"]
    assert coverage_state["below_85_module_count"] == 80
    assert coverage_state["uncovered_module_count"] == 0
    assert coverage_state["unmeasured_module_count"] == 0
    
    # Verify module coverage inventory exists and has summary
    assert "summary" in module_coverage
    # Verify the summary contains coverage metrics
    summary = module_coverage["summary"]
    assert "coverage_xml_present" in summary


@pytest.mark.architecture
def test_issue_5978_evidence_paths_exist() -> None:
    """All documented evidence paths exist."""
    closeout = _load_json(CLOSEOUT)
    
    for evidence_path in closeout["evidence"]:
        path = ROOT / evidence_path
        assert path.exists(), f"Evidence path does not exist: {evidence_path}"
