# pyright: reportArgumentType=false
"""Architecture guards for GHA-002/GHA-003 closeout (#8618/#8619)."""

from __future__ import annotations

import json
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
    assert "Safe only after #10267" not in text
    assert "empty applied rules as merge protection" not in text


def test_ruleset_10267_closeout_evidence_matches_live_contract() -> None:
    """Sanitized closeout GET must match the #10267 live ruleset contract."""
    path = (
        ROOT / "reports" / "governance" / "ruleset-10267-closeout-get-2026-09-10.json"
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["repository"] == "SatoryKono/BioactivityDataAcquisition"
    assert data["default_branch"] == "main"
    assert data["allow_auto_merge"] is True
    assert data["applied_required_status_checks"] == ["pr-gate-complete"]
    assert "deletion" in data["applied_rules_main"]
    assert "required_status_checks" in data["applied_rules_main"]
    by_id = {item["id"]: item for item in data["rulesets"]}
    main_rs = by_id[13643213]
    assert main_rs["name"] == "main"
    assert main_rs["enforcement"] == "active"
    assert main_rs["required_status_checks"] == ["pr-gate-complete"]
    assert main_rs["required_approving_review_count"] == 0
    assert main_rs["bypass_actors"] == []
    assert main_rs["strict_required_status_checks_policy"] is True
    companion = by_id[15730586]
    assert companion["name"] == "root-hygiene-required-check"
    assert companion["enforcement"] == "disabled"
    assert companion["required_status_checks"] == ["checks-complete", "root-hygiene"]
