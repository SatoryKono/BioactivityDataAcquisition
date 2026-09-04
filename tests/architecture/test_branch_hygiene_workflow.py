"""Contracts for branch naming and report-only lifecycle automation."""

from __future__ import annotations

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


def test_branch_hygiene_allows_established_automation_providers() -> None:
    """Workflow and policy must agree on supported automation branch prefixes."""
    workflow = WORKFLOW.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")

    for provider in ("dependabot", "renovate", "devin", "bolt", "copilot"):
        assert provider in workflow
        assert f"`{provider}/`" in policy


def test_branch_lifecycle_policy_protects_active_work() -> None:
    policy = POLICY.read_text(encoding="utf-8")

    assert "active PR head" in policy
    assert "checked out by" in policy and "worktree" in policy
    assert "MUST default to dry-run" in policy
    assert "Branch-count ceilings MUST NOT be enforced" in policy
