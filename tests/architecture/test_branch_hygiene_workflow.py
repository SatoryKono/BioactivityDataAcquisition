"""Contracts for branch naming and report-only lifecycle automation."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/branch-hygiene.yml"
POLICY = ROOT / "docs/00-project/governance/05-github-policy.md"


def test_branch_hygiene_workflow_enforces_only_current_pr_head() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "HEAD_REF: ${{ github.head_ref }}" in workflow
    assert "validate-pr-branch-name" in workflow
    assert "generate-branch-cleanup-inventory" in workflow
    assert "github.event_name != 'pull_request'" in workflow
    assert "apply-branch-cleanup" not in workflow
    assert "--apply" not in workflow


def test_branch_hygiene_allows_established_automation_providers() -> None:
    """Workflow and policy must agree on supported automation branch prefixes."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")

    for provider in ("dependabot", "renovate", "devin", "bolt", "copilot", "codex"):
        assert provider in workflow
        assert f"`{provider}/`" in policy


def test_committed_branch_hygiene_inventory_is_dry_run() -> None:
    snapshot = ROOT / "reports" / "quality" / "branch-hygiene-inventory-2026-09-09.json"
    payload = json.loads(snapshot.read_text(encoding="utf-8"))

    assert payload["mode"] == "dry-run"
    assert payload["deletion_applied"] is False
    assert payload["non_compliant_owner_decisions"]
    for row in payload["non_compliant_owner_decisions"]:
        assert row["proposed_action"] in {"keep", "tag", "delete", "review"}
    for worktree in payload.get("local_worktrees", []):
        assert "path" not in worktree


def test_branch_lifecycle_policy_protects_active_work() -> None:
    policy = POLICY.read_text(encoding="utf-8")

    assert "active PR head" in policy
    assert "checked out by" in policy and "worktree" in policy
    assert "MUST default to dry-run" in policy
    assert "Branch-count ceilings MUST NOT be enforced" in policy
    assert "master20260910" in policy
    assert "temp-branch" in policy
    assert "12323" in policy


@pytest.mark.parametrize(
    ("branch", "accepted"),
    [
        ("codex/operator-regression-10167-10185-10171", True),
        ("codex/repair-ci", True),
        ("dependabot/pip/requests-2.32.0", True),
        ("copilot/fix-error", True),
        ("codex/", False),
        ("codex-repair-ci", False),
        ("unknown/repair-ci", False),
        ("tmp", False),
    ],
)
def test_automation_branch_pattern_accepts_only_named_namespaces(
    branch: str, accepted: bool
) -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    match = re.search(r"automation='([^']+)'", workflow)
    assert match is not None
    assert (re.fullmatch(match.group(1), branch) is not None) is accepted
