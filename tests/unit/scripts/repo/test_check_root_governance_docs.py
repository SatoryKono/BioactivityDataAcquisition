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
"""Unit tests for root-governance docs parity guard."""

from __future__ import annotations

import pytest

from scripts.engineering.repo import check_root_governance_docs as module


pytestmark = pytest.mark.unit


def test_missing_machine_readable_refs_reports_all_missing_entries() -> None:
    issues = module._missing_machine_readable_refs(
        "Canonical root policy lives in .github/root-allowlist.txt only."
    )

    assert "configs/quality/repo_structure_catalog.yaml" in issues
    assert "configs/quality/root_hygiene_review_registry.yaml" in issues
    assert "configs/quality/generated_artifact_routing.yaml" in issues


def test_missing_root_dir_mentions_flags_omitted_catalog_entry() -> None:
    issues = module._missing_root_dir_mentions(
        approved_root_directories=frozenset({".codex", ".devin", "scripts"}),
        policy_text="Approved roots: `.codex`, `scripts`.",
    )

    assert issues == [".devin"]


def test_plans_readme_issues_require_catalog_reference_and_active_backlog_link() -> (
    None
):
    issues = module._plans_readme_issues(
        catalog={
            "plans": {
                "readme": "docs/plans/README.md",
                "allowed_files": [
                    {
                        "path": "docs/plans/consolidated-open-tasks-plan-2026-03-21.md",
                        "lifecycle": "active_backlog",
                    }
                ],
            }
        },
        readme_text="Only one tracked plan file may hold lifecycle `active_backlog`.",
    )

    assert "docs/plans/README.md must reference repo_structure_catalog.yaml" in issues
    assert (
        "docs/plans/README.md must link the active backlog consolidated-open-tasks-plan-2026-03-21.md"
        in issues
    )


def test_ops_index_issues_reject_root_script_codex_reference() -> None:
    issues = module._ops_index_issues("- `script-codex/helper/ensure-codex-cli.sh`\n")

    assert any("script-codex" in issue for issue in issues)
    assert any(
        "scripts/ai/codex/helper/ensure-codex-cli.sh" in issue for issue in issues
    )
