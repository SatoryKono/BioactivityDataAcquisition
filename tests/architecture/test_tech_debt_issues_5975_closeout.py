"""Closeout guards for slow governance scan hotspot reduction issue #5975."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5975-closeout.json"
SLOW_TEST = ROOT / "tests" / "architecture" / "test_debt_governance_telemetry_reporting.py"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


@pytest.mark.architecture
def test_issue_5975_slow_governance_scan_deferred_with_optimization_plan() -> None:
    """Slow governance scan hotspot reduction is deferred with documented optimization plan."""
    closeout = _load_json(CLOSEOUT)
    
    assert closeout["issue"]["number"] == 5975
    assert closeout["closeout"]["status"] == "deferred_with_optimization_plan"
    
    # Verify performance analysis is documented
    perf_analysis = closeout["performance_analysis"]
    assert perf_analysis["slowest_test"] == "test_debt_governance_snapshot_matches_live_sources"
    assert perf_analysis["duration_seconds"] == 24.73
    assert len(perf_analysis["bottleneck_operations"]) > 0
    
    # Verify current caching strategy is documented
    caching = perf_analysis["current_caching_strategy"]
    assert "test_governance_report" in caching
    assert caching["test_governance_report"] == "cached via _collect_test_governance_report_cached"
    
    # Verify proposed improvements are documented
    improvements = closeout["proposed_improvements"]
    assert improvements["status"] == "documented_for_optimization"
    assert len(improvements["recommended_actions"]) > 0


@pytest.mark.architecture
def test_issue_5975_slow_test_file_exists() -> None:
    """The slow test file referenced in closeout exists."""
    assert SLOW_TEST.exists(), f"Slow test file must exist: {SLOW_TEST}"
    
    # Verify the slow test function exists
    test_content = SLOW_TEST.read_text(encoding="utf-8")
    assert "test_debt_governance_snapshot_matches_live_sources" in test_content


@pytest.mark.architecture
def test_issue_5975_evidence_paths_exist() -> None:
    """All documented evidence paths exist."""
    closeout = _load_json(CLOSEOUT)
    
    for evidence_path in closeout["evidence"]:
        path = ROOT / evidence_path
        assert path.exists(), f"Evidence path does not exist: {evidence_path}"
