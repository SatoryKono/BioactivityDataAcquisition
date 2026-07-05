"""Closeout guards for governance/evidence issues #5954, #5955, #5962, #5963."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_SCRIPT = ROOT / "src" / "memory" / "tooling" / "workflow.py"
PRETEST_GUARDRAILS = ROOT / "scripts" / "engineering" / "dev" / "pretest_guardrails.sh"
DEBT_GATES = ROOT / "reports" / "quality" / "debt-governance-gates.json"
FLAKY_REVIEW = ROOT / "reports" / "quality" / "flaky-test-burndown-review.json"
OBSERVABILITY_GOVERNANCE = (
    ROOT / "configs" / "quality" / "observability_metric_governance.yaml"
)
TESTS_WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), path
    return payload


def _gate(payload: dict[str, Any], name: str) -> dict[str, Any]:
    for gate in payload["gates"]:
        if gate["name"] == name:
            return gate
    raise AssertionError(f"missing debt governance gate: {name}")


def test_issue_5954_memory_workflow_smoke_is_bounded_and_wired() -> None:
    workflow_text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")
    pretest_text = PRETEST_GUARDRAILS.read_text(encoding="utf-8")

    assert "DEFAULT_POST_TASK_REFRESH_TIMEOUT_SECONDS = 15.0" in workflow_text
    assert "def smoke_workflow(" in workflow_text
    assert "memory-workflow-smoke" in pretest_text
    assert '"$PYTHON_BIN" -m memory.tooling.workflow smoke' in pretest_text


def test_issue_5955_debt_governance_rollup_blocks_budget_growth() -> None:
    gates = _load_json(DEBT_GATES)
    tests_workflow = TESTS_WORKFLOW.read_text(encoding="utf-8")

    assert gates["summary"]["release_gate_status"] == "passing"
    assert _gate(gates, "debt_scorecard_budget_violations")["status"] == "pass"
    assert _gate(gates, "debt_budget_growth_policy")["status"] == "pass"
    assert _gate(gates, "debt_scorecard_budget_no_growth")["status"] == "pass"
    assert (
        "report-debt-governance-gates --check --changed-from-ref refs/remotes/origin/main"
        in tests_workflow
    )


def test_issue_5962_flaky_inventory_is_explicit_and_fail_fast() -> None:
    gates = _load_json(DEBT_GATES)
    review = _load_json(FLAKY_REVIEW)

    assert "#5962" in review["linked_issues"]
    assert review["summary"]["total_flaky"] == 0
    assert review["reviewed_flaky_tests"] == []
    assert review["policy"]["no_growth_gate"].endswith("flaky_test_total_count")
    assert _gate(gates, "flaky_test_total_count")["status"] == "pass"
    assert _gate(gates, "flaky_test_untriaged_count")["status"] == "pass"


def test_issue_5963_observability_freshness_and_zero_debt_gates_are_release_blocking() -> (
    None
):
    gates = _load_json(DEBT_GATES)
    governance = _load_yaml(OBSERVABILITY_GOVERNANCE)
    change_gate = governance["runtime_cardinality_review"]["live_evidence"][
        "touched_metric_change_gate"
    ]

    assert change_gate["mode"] == "changed_paths_require_fresh_release_review"
    assert "grafana/dashboards/" in change_gate["changed_path_trigger_prefixes"]
    assert "grafana/prometheus-rules/" in change_gate["changed_path_trigger_prefixes"]
    for gate_name in (
        "observability_dashboarded_without_declaration",
        "observability_dashboarded_without_emission",
        "observability_alerted_without_emission",
        "observability_unused_declared_metrics",
        "observability_runtime_cardinality_review_required",
        "observability_runtime_cardinality_threshold_violations",
        "observability_release_review_status",
        "observability_release_review_freshness",
        "observability_touched_metric_inventory_freshness",
        "observability_touched_metric_review_freshness",
    ):
        assert _gate(gates, gate_name)["status"] == "pass"
