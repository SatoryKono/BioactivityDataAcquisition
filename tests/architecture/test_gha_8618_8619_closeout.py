# pyright: reportArgumentType=false
"""Architecture guards for GHA-002/GHA-003 closeout (#8618/#8619)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
GITIGNORE = ROOT / ".gitignore"
DOCS_WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
GITHUB_POLICY = ROOT / "docs" / "00-project" / "governance" / "05-github-policy.md"


def test_gha_002_docs_workflow_is_present_and_not_ignored() -> None:
    """GHA-002: docs.yml must be a real tracked gate surface, not gitignored."""
    assert DOCS_WORKFLOW.is_file(), "docs.yml must exist"
    gitignore_lines = {
        line.strip()
        for line in GITIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    assert ".github/workflows/docs.yml" not in gitignore_lines
    assert "docs-governance:" in DOCS_WORKFLOW.read_text(encoding="utf-8")


def test_github_policy_documents_live_root_hygiene_ruleset() -> None:
    """GHA-003: policy SSOT must document the live ruleset enforcement state."""
    text = GITHUB_POLICY.read_text(encoding="utf-8")
    assert "root-hygiene-required-check" in text
    # Live: 13643213 active with pr-gate-complete; 15730586 stays disabled.
    assert "Enforcement: `active`" in text
    assert "Enforcement: `disabled`" in text
    assert "`pr-gate-complete`" in text
    assert "`checks-complete`" in text
    assert "`root-hygiene`" in text
    assert "no bypass actors" in text
    assert "required checks and ref protection active" not in text
    assert "Rules currently enforced:" not in text
    assert "13643213 both active" not in text
    assert "#10267" in text
    assert "applied_required_status_checks" in text
