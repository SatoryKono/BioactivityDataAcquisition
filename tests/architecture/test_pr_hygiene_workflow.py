"""Architecture guardrails for deterministic PR hygiene governance."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-hygiene.yml"
POLICY = ROOT / ".github" / "PULL_REQUEST_HYGIENE.md"


def test_pr_hygiene_policy_documents_issue_first_governance() -> None:
    content = POLICY.read_text(encoding="utf-8")

    assert "issues" in content
    assert "draft PRs" in content
    assert "report-only" in content
    assert "bot-generated" in content
    assert "21" in content


def test_pr_hygiene_workflow_is_manual_and_scheduled() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "30 6 * * 1"' in workflow


def test_pr_hygiene_workflow_closes_only_stale_report_noise_drafts() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "actions/github-script@f28e40c7f34bde8b3046d885e986cb6290c5673b" in workflow
    assert "pull-requests: write" in workflow
    assert "issues: write" in workflow
    assert "pr.draft" in workflow
    assert "STALE_LABEL = 'stale'" in workflow
    assert "AUTO_CLOSE_INACTIVE_DAYS = 21" in workflow
    assert "report-only" in workflow
    assert "bot-generated" in workflow
    assert "generated report" in workflow
    assert "generated artifact" in workflow
    assert ".github/PULL_REQUEST_HYGIENE.md" in workflow
