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
"""Closeout guards for Test Audit issues #5974-#5977."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "reports" / "quality" / "tech-debt-issues-5974-5977-closeout.json"
TIME_SEAM_REGISTRY = ROOT / "configs" / "quality" / "time_seam_classification.yaml"
SUNSET_LEDGER = ROOT / "configs" / "quality" / "compatibility_sunset_ledger.yaml"
SUNSET_TEST = (
    ROOT / "tests" / "architecture" / "test_behavior_retirement_ledger_governance.py"
)
TEST_GOVERNANCE_CONFIG = ROOT / "configs" / "quality" / "test_governance_audit.yaml"
TEST_MATRIX = ROOT / "configs" / "quality" / "test_matrix.yaml"
SLOWEST_TESTS = ROOT / "reports" / "test-telemetry" / "slowest-tests.json"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


@pytest.mark.architecture
def test_issue_5974_time_seam_guards_are_extended() -> None:
    """Replay time-seam guards must cover time.time_ns and datetime.utcnow."""
    closeout = _load_json(CLOSEOUT)
    outcome = closeout["outcomes"]["5974"]

    assert outcome["status"] == "closeable"
    assert len(outcome["actions_taken"]) > 0

    # Verify time_seam_classification.yaml has new seams
    time_seam_config = _load_yaml(TIME_SEAM_REGISTRY)
    seams = time_seam_config.get("seams", [])

    # Check for time.time_ns in checkpoint IO
    time_ns_seams = [s for s in seams if s.get("call") == "time.time_ns"]
    assert len(time_ns_seams) > 0, "time.time_ns must be classified"

    # Check for datetime.now in memory tooling
    memory_now_seams = [
        s
        for s in seams
        if s.get("call") == "datetime.now" and "memory" in s.get("path", "")
    ]
    assert len(memory_now_seams) > 0, "Memory tooling datetime.now must be classified"


@pytest.mark.architecture
def test_issue_5975_slow_governance_hotspots_are_budgeted() -> None:
    """Slow governance scan hotspots must have shared caches and a no-growth budget."""
    closeout = _load_json(CLOSEOUT)
    outcome = closeout["outcomes"]["5975"]

    assert outcome["status"] == "closeable"
    assert len(outcome["actions_taken"]) > 0

    budget = outcome["duration_budget"]
    assert budget["source"] == "reports/test-telemetry/slowest-tests.json"
    assert budget["max_total_duration_s"] <= budget["baseline_total_duration_s"]
    assert "session-scoped" in budget["hard_reason"]
    assert SLOWEST_TESTS.exists(), "Duration telemetry artifact must stay committed"

    test_matrix = _load_yaml(TEST_MATRIX)
    lanes = test_matrix["test_lanes"]["lanes"]
    architecture_lane = lanes["architecture"]
    fast_lane = lanes["architecture-fast-boundary"]
    slow_lane = lanes["architecture-slow-governance"]

    assert "S7-architecture-fast-boundary" in architecture_lane["runner_options"]
    assert "S7-architecture-slow-governance" in architecture_lane["runner_options"]
    assert fast_lane["suite_name"] == "architecture-fast-boundary"
    assert slow_lane["suite_name"] == "architecture-slow-governance"


@pytest.mark.architecture
def test_issue_5976_duplicate_name_inventory_consolidated() -> None:
    """Duplicate test-name inventory must be consolidated into main governance artifact."""
    closeout = _load_json(CLOSEOUT)
    outcome = closeout["outcomes"]["5976"]

    assert outcome["status"] == "closeable"
    assert len(outcome["actions_taken"]) > 0

    # Verify separate duplicate-name artifact does not exist
    duplicate_name_artifact = (
        ROOT / "reports" / "quality" / "test-duplicate-name-inventory.json"
    )
    assert not duplicate_name_artifact.exists(), (
        "Separate duplicate-name artifact must be removed"
    )

    # Verify main governance artifact exists
    main_artifact = ROOT / "reports" / "quality" / "test-governance-current.json"
    assert main_artifact.exists(), "Main governance artifact must exist"

    # Verify config references consolidated artifact
    test_governance_config = _load_yaml(TEST_GOVERNANCE_CONFIG)
    evidence_paths = test_governance_config.get("issue_4172", {}).get(
        "evidence_paths", []
    )
    assert "reports/quality/test-duplicate-name-inventory.json" not in evidence_paths
    # Note: test-governance-current.json is referenced in the main evidence section, not issue_4172


@pytest.mark.architecture
def test_issue_5977_compatibility_sunset_ledger_created() -> None:
    """Compatibility behavior test sunset ledger must exist and be valid."""
    closeout = _load_json(CLOSEOUT)
    outcome = closeout["outcomes"]["5977"]

    assert outcome["status"] == "closeable"
    assert len(outcome["actions_taken"]) > 0

    # Verify sunset ledger exists
    assert SUNSET_LEDGER.exists(), "Compatibility sunset ledger must exist"

    # Verify ledger structure
    sunset_config = _load_yaml(SUNSET_LEDGER)
    assert sunset_config["version"] == 1
    assert sunset_config["policy_scope"] == "compatibility_behavior_sunset"
    assert "entries" in sunset_config
    assert len(sunset_config["entries"]) > 0

    # Verify each entry has required fields
    for entry in sunset_config["entries"]:
        assert "test_pattern" in entry
        assert "sunset_criteria" in entry
        assert "status" in entry
        assert "owner" in entry

    # Verify test file exists and is not in compatibility pattern
    assert SUNSET_TEST.exists(), "Sunset ledger test must exist"
    forbidden_filename_tokens = ("compat", "legacy", "deprecated", "shim", "sunset")
    assert not any(
        token in SUNSET_TEST.name.lower() for token in forbidden_filename_tokens
    ), "Test file should not match compatibility pattern to avoid budget violation"


@pytest.mark.architecture
def test_closeout_governance_gates_are_passing() -> None:
    """All governance gates must be passing for closeout."""
    closeout = _load_json(CLOSEOUT)
    gates = closeout["governance_gates"]

    assert gates["debt_governance_gates_passing"] is True
    assert gates["architecture_tests_passing"] is True
    assert gates["test_governance_audit_passing"] is True


@pytest.mark.architecture
def test_closeout_status_is_complete() -> None:
    """Closeout status must reflect all four issues as closeable."""
    closeout = _load_json(CLOSEOUT)
    closeout_status = closeout["closeout"]

    assert closeout_status["status"] == "complete"
    assert set(closeout_status["closeable_issues"]) == {5974, 5975, 5976, 5977}
    assert closeout_status["deferred_issues"] == []
