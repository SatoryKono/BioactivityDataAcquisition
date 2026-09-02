# pyright: reportArgumentType=false
"""Architecture guards for pr-gate-complete aggregator (#9975)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "configs/quality/github_required_checks.yaml"
COORDINATOR = ROOT / ".github/workflows/pr-required.yml"
GITHUB_POLICY = ROOT / "docs/00-project/governance/05-github-policy.md"

EXPECTED_GATES = {
    "lint-arch",
    "tests",
    "type-checking",
    "security",
    "codeql",
    "docker",
    "duplication",
    "root-hygiene",
    "generated-artifacts",
    "compiled-artifacts",
    "commit-governance",
    "docs-governance",
}
EXPECTED_CANONICAL_CHECKS = {
    "ruff",
    "mypy",
    "dependency-lock",
    "architecture",
    "integration",
    "dq-consistency",
    "root-hygiene",
    "compiled-artifacts",
    "security-scans",
    "canonical-manifest-hashes",
    "commit-governance",
    "docs-governance",
}

def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_catalog_exists_and_has_expected_gates() -> None:
    assert CATALOG.is_file()
    data = _load_yaml(CATALOG)
    assert data.get("aggregator") == "pr-gate-complete"
    assert data.get("coordinator_workflow") == ".github/workflows/pr-required.yml"
    assert data.get("version") == 2
    assert data.get("schema_version") == 1
    gates = {g["id"] for g in data.get("gates", [])}
    assert EXPECTED_GATES.issubset(gates)
    policy = data.get("policy", {})
    assert policy.get("allow_skipped_as_success") is False
    assert policy.get("require_sha_binding") is True
    for gate in data["gates"]:
        assert "owner_workflow" in gate
        assert "allowed_results" in gate

    canonical_checks = data.get("canonical_checks", [])
    assert {check["id"] for check in canonical_checks} == EXPECTED_CANONICAL_CHECKS
    assert len({check["id"] for check in canonical_checks}) == len(canonical_checks)
    for check in canonical_checks:
        assert check["owner_workflow"].startswith(".github/workflows/")
        assert check["owner_jobs"]
        assert check["selectors"]
        assert check["events"]
        assert check["status"] in {"blocking", "advisory_evidence"}
        assert check["duplicate_policy"] == "forbidden"


def test_coordinator_materializes_on_every_main_pr_after_owner_cutover() -> None:
    assert COORDINATOR.is_file()
    data = _load_yaml(COORDINATOR)
    on = data.get("on", data.get(True, {}))
    assert isinstance(on, dict)
    assert set(on) == {"pull_request", "workflow_dispatch"}
    assert on["pull_request"] == {"branches": ["main"]}
    perms = data.get("permissions", {})
    assert perms == {"contents": "read"} or perms.get("contents") == "read"
    conc = data.get("concurrency", {})
    group = str(conc.get("group", ""))
    assert "github.workflow" in group
    assert "github.event.pull_request.number" in group or "github.sha" in group
    assert "cancel-in-progress" in conc


def test_coordinator_has_classify_and_aggregate_jobs() -> None:
    data = _load_yaml(COORDINATOR)
    jobs = data.get("jobs", {})
    assert "classify-changes" in jobs
    assert "pr-gate-complete" in jobs
    agg = jobs["pr-gate-complete"]
    assert str(agg.get("if", "")).strip() == "${{ always() }}"
    needs = agg.get("needs", [])
    assert "classify-changes" in needs
    for gate in EXPECTED_GATES:
        assert gate in needs or f"{gate}-not-applicable" in needs
    classify = jobs["classify-changes"]
    assert "head_sha" in str(classify.get("outputs", {}))


def test_leaf_workflows_expose_workflow_call() -> None:
    data = _load_yaml(CATALOG)
    for gate in data["gates"]:
        if gate["id"] not in EXPECTED_GATES:
            continue
        wf_path = ROOT / gate["owner_workflow"]
        assert wf_path.is_file()
        wf = _load_yaml(wf_path)
        on = wf.get("on", wf.get(True, {}))
        assert isinstance(on, dict)
        assert "workflow_call" in on
        assert "pull_request" not in on


def test_policy_doc_mentions_shadow_aggregator() -> None:
    text = GITHUB_POLICY.read_text(encoding="utf-8")
    assert "pr-gate-complete" in text
    assert "configs/quality/github_required_checks.yaml" in text
    assert "shadow" in text.lower()


def test_aggregator_does_not_use_continue_on_error() -> None:
    text = COORDINATOR.read_text(encoding="utf-8")
    assert "continue-on-error" not in text
