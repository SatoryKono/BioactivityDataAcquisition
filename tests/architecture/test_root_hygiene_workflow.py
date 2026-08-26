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
"""Architecture tests for root hygiene CI enforcement."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


def test_root_hygiene_workflow_runs_for_all_pr_and_push_changes() -> None:
    workflow = Path(".github/workflows/root-hygiene.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "paths-ignore:" not in workflow


def test_root_hygiene_workflow_uses_strict_audit_and_unit_tests() -> None:
    workflow = Path(".github/workflows/root-hygiene.yml").read_text(encoding="utf-8")

    assert (
        "python -m scripts.engineering.repo check-cleanliness --strict-untracked"
        in workflow
    )
    assert "--check-local-forbidden-outputs" in workflow
    assert "python -m scripts.engineering.repo check-cleanup-governance" in workflow
    assert "python -m scripts.engineering.repo check-root-governance-docs" in workflow
    assert "python -m scripts.engineering.repo check-root-review-registry" in workflow
    assert (
        "python -m scripts.engineering.diagnostics audit-structure --path ." in workflow
    )
    assert "tests/unit/scripts/repo/test_audit_root_cleanliness.py" in workflow
    assert "tests/unit/scripts/repo/test_check_cleanup_governance.py" in workflow
    assert "tests/unit/scripts/repo/test_check_root_governance_docs.py" in workflow
    assert "tests/unit/scripts/repo/test_cleanup_repository.py" in workflow
    assert "tests/unit/scripts/repo/test_cleanup_root_local_clutter.py" in workflow
    assert "tests/unit/scripts/repo/test_audit_structure.py" in workflow
    assert (
        "tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py" in workflow
    )
    assert "tests/architecture/test_root_hygiene_workflow.py" in workflow
    assert "tests/architecture/test_root_hygiene_review_registry.py" in workflow
    assert "tests/architecture/test_env_example_reference_policy.py" in workflow
    assert "-q" in workflow


def test_root_hygiene_workflow_uploads_cleanup_classification_artifact() -> None:
    workflow = Path(".github/workflows/root-hygiene.yml").read_text(encoding="utf-8")

    assert "cleanup_repository.py" in workflow
    assert (
        "--report-json reports/quality/root-hygiene-cleanup-classification.json"
        in workflow
    )
    assert (
        "--report-root-review-json reports/quality/root-hygiene-review-evidence.json"
        in workflow
    )
    assert (
        "--report-reports-workspace-json reports/quality/reports-workspace-review.json"
        in workflow
    )
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a" in workflow
    )
    assert "root-hygiene-cleanup-classification" in workflow
    assert "root-hygiene-review-evidence" in workflow
    assert "reports-workspace-review" in workflow


def test_github_policy_lists_root_hygiene_as_required_check() -> None:
    policy = Path("docs/00-project/governance/05-github-policy.md").read_text(
        encoding="utf-8"
    )
    critical_section = policy.split("### Recommended", maxsplit=1)[0]

    assert "| `root-hygiene`" in critical_section


def test_retention_sensitive_cleanup_template_requires_evidence_pack() -> None:
    template = Path(".github/ISSUE_TEMPLATE/retention_sensitive_cleanup.yml").read_text(
        encoding="utf-8"
    )

    for required_fragment in (
        "candidate_inventory",
        "classification_table",
        "dry_run_evidence",
        "reviewed_apply_list",
        "verification",
        "rollback",
        "retention-sensitive-cleanup.md",
    ):
        assert required_fragment in template


def test_github_policy_records_root_hygiene_admin_verification_lane() -> None:
    policy = Path("docs/00-project/governance/05-github-policy.md").read_text(
        encoding="utf-8"
    )

    assert "Branch Protection Verification" in policy
    assert "Activated and re-verified on `2026-08-19`" in policy
    assert "#3380" in policy
    assert "root-hygiene-required-check" in policy
    assert "/rules/15730586" in policy
    assert "Enforcement: `disabled`" in policy
    assert "`checks-complete` and `root-hygiene`" in policy
    assert "Direct merge allowed; no active required-check ruleset" in policy
