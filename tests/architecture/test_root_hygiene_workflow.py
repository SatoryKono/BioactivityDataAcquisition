"""Architecture tests for root hygiene CI enforcement."""

from __future__ import annotations

from pathlib import Path


def test_root_hygiene_workflow_runs_for_all_pr_and_push_changes() -> None:
    workflow = Path(".github/workflows/root-hygiene.yml").read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "push:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "paths-ignore:" not in workflow


def test_root_hygiene_workflow_uses_strict_audit_and_unit_tests() -> None:
    workflow = Path(".github/workflows/root-hygiene.yml").read_text(encoding="utf-8")

    assert "audit_root_cleanliness.py --strict-untracked" in workflow
    assert "check_root_hygiene_review_registry.py" in workflow
    assert "tests/unit/scripts/repo/test_audit_root_cleanliness.py" in workflow
    assert (
        "tests/unit/scripts/repo/test_check_root_hygiene_review_registry.py"
        in workflow
    )
    assert "tests/architecture/test_root_hygiene_workflow.py" in workflow
    assert "tests/architecture/test_root_hygiene_review_registry.py" in workflow
    assert "-q" in workflow


def test_github_policy_lists_root_hygiene_as_required_check() -> None:
    policy = Path("docs/00-project/governance/05-github-policy.md").read_text(
        encoding="utf-8"
    )
    critical_section = policy.split("### Recommended", maxsplit=1)[0]

    assert "| `root-hygiene`" in critical_section
