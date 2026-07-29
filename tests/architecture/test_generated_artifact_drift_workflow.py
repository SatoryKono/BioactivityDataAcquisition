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
"""Governance guards for generated artifact drift workflow documentation."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
RUNBOOK = (
    ROOT
    / "docs"
    / "05-operations"
    / "runbooks"
    / "generated-artifact-drift-workflow.md"
)
EVIDENCE_DOC = ROOT / "docs" / "02-architecture" / "governance-audit-evidence.md"


def test_generated_artifact_drift_workflow_declares_canonical_commands() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    required_commands = {
        "python -m scripts.schema generate-config-matrix --check",
        "pytest tests/architecture/test_config_surface_entity_residual_plateau.py",
        "python -m scripts.engineering.qa report-module-coverage --check --allow-missing-coverage-xml",
        "python -m scripts.engineering.qa report-vcr-metadata --check",
        "pytest tests/architecture/test_content_hash_datetime_policy_inventory.py",
        "python -m scripts.engineering.qa report-family-baseline --check",
        "python -m scripts.engineering.qa report-contract-coverage-matrix --check",
    }

    missing = sorted(command for command in required_commands if command not in text)

    assert missing == []


def test_generated_artifact_drift_workflow_forbids_budget_growth() -> None:
    text = RUNBOOK.read_text(encoding="utf-8")

    assert "`decreased`" in text
    assert "`flat`" in text
    assert "`increased`" in text
    assert "Do not increase budgets" in text
    assert "Budget edits are not a remedy for drift" in text


def test_architecture_governance_evidence_doc_is_mirror_only() -> None:
    text = EVIDENCE_DOC.read_text(encoding="utf-8")

    assert "does not redefine runtime behavior" in text
    assert "reports/quality/architecture-quality-scorecard.json" in text
    assert "reports/quality/hotspot-family-baseline.json" in text
    assert "reports/quality/layer-contract-coverage-matrix.json" in text
    assert "configs/quality/time_seam_classification.yaml" in text
    assert "Technical-debt budgets can only stay flat or decrease" in text
