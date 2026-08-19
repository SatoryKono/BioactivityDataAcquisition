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


def test_github_policy_documents_active_root_hygiene_ruleset() -> None:
    """GHA-003: policy SSOT must document active always-on ruleset on main."""
    text = GITHUB_POLICY.read_text(encoding="utf-8")
    assert "root-hygiene-required-check" in text
    assert "Enforcement: `active`." in text
    assert "`checks-complete`" in text
    assert "`root-hygiene`" in text
    assert "Direct merge allowed; no active required-check ruleset" not in text
    assert "no bypass actors" in text
    assert (
        "enforcement=disabled"
        not in text.split("Live GitHub enforcement state:", 1)[-1]
    )
