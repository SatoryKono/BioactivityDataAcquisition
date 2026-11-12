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
"""Architecture tests for active runtime docs mirror and freshness guardrails."""

from __future__ import annotations

import pytest

import importlib
from pathlib import Path
import subprocess
from types import ModuleType


pytestmark = pytest.mark.architecture


def test_local_worktree_guard_is_owned_by_both_root_entrypoints() -> None:
    """Workstation placement, env consent and full-tree gates stay coupled."""
    for path in (Path("AGENTS.md"), Path(".junie/guidelines.md")):
        content = path.read_text(encoding="utf-8")
        section = content.split("## Local Git Tree Placement", 1)[1].split("\n## ", 1)[
            0
        ]
        for anchor in (
            "D:\\github\\BioactivityDataAcquisition-worktrees\\<task>",
            "symlinks and junctions",
            "older checkouts",
            "scripts/engineering/repo/create_worktree.py",
            "bioetl-create-worktree.py",
            "Direct `git worktree add`, including `--no-checkout`, is forbidden",
            "per-task `.env.example` approval",
            "full-tree commit gate",
        ):
            assert anchor in section
    for path in (
        Path("docs/03-guides/github-local-workflow.md"),
        Path("docs/03-guides/github-quick-reference.md"),
    ):
        content = path.read_text(encoding="utf-8")
        assert "git worktree add .worktrees/" not in content
        assert (
            "D:/github/BioactivityDataAcquisition/.git/hooks/bioetl-create-worktree.py"
            in content
        )


def _load_doc_drift_module() -> ModuleType:
    return importlib.import_module("scripts.docs.checks.check_drift")


def _issues_to_text(report: object) -> str:
    issues = report.issues
    return "\n".join(
        f"{issue.category}::{issue.doc_file}::{issue.detail}" for issue in issues
    )


def test_runtime_agent_mirror_drift_check_passes_current_repo() -> None:
    mod = _load_doc_drift_module()
    report = mod.DriftReport()
    mod.check_runtime_mirrors(report)

    assert not report.issues, (
        "Critical runtime docs mirrors drifted from canonical .codex sources.\n"
        f"{_issues_to_text(report)}"
    )


def test_runtime_doc_freshness_check_passes_current_repo() -> None:
    mod = _load_doc_drift_module()
    report = mod.DriftReport()
    mod.check_freshness(report)

    assert not report.error_count, (
        "Active runtime/governance docs contain freshness or version drift.\n"
        f"{_issues_to_text(report)}"
    )


def test_runtime_ownership_covers_tracked_devin_profiles() -> None:
    root_contract = Path("AGENTS.md").read_text(encoding="utf-8")
    junie_contract = Path(".junie/guidelines.md").read_text(encoding="utf-8")
    ownership = Path(
        "docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md"
    ).read_text(encoding="utf-8")

    for content in (root_contract, junie_contract, ownership):
        assert ".devin/agents/DEVIN-RUNTIME.md" in content
        assert ".devin/agents/*/AGENT.md" in content

    assert "not** a parallel 9-bot agent registry" not in ownership


def test_runtime_ownership_keeps_devin_source_above_foreign_profiles() -> None:
    ownership = Path(
        "docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md"
    ).read_text(encoding="utf-8")
    delegation = ownership.split("## Precedence Model", 1)[1].split(
        "## Sync Direction", 1
    )[0]
    assert "sole repository precedence is `AGENTS.md`" in delegation
    assert "1. active runtime" not in delegation

    root = Path("AGENTS.md").read_text(encoding="utf-8")
    precedence = root.split("## Canonical Precedence", 1)[1].split(
        "## Instruction Scope", 1
    )[0]

    root_contract = precedence.index("repository-wide root contract")
    devin_runtime = precedence.index(".devin/agents/DEVIN-RUNTIME.md")
    matching_profiles = precedence.index("runtime profiles and skills")
    devin_profile = precedence.index(".devin/agents/*/AGENT.md")

    assert root_contract < devin_runtime < matching_profiles < devin_profile


def test_no_tracked_devin_atomic_temp_config_duplicates() -> None:
    tracked = subprocess.check_output(
        ["git", "ls-files", ".devin/"],
        text=True,
    ).splitlines()
    assert not [path for path in tracked if Path(path).name.startswith(".tmp")]


def test_active_runtime_maps_require_explicit_memory_actor_provenance() -> None:
    runtime_maps = (
        Path(".codex/agents/CODEX-RUNTIME.md"),
        Path(".junie/agents/JUNIE-RUNTIME.md"),
        Path(".devin/agents/DEVIN-RUNTIME.md"),
    )
    for runtime_map in runtime_maps:
        content = runtime_map.read_text(encoding="utf-8")
        assert "BIOETL_AI_RUNTIME=" in content
        assert "BIOETL_AI_AGENT=" in content
        assert "BIOETL_AI_MODEL=" in content


@pytest.mark.parametrize(
    "path",
    [
        "docs/00-project/ai/agents/guides/grok-operator-runbook.md",
        "docs/00-project/ai/prompts/library/session/bootstrap.md",
        "docs/03-guides/development/pycharm-setup.md",
        "docs/03-guides/github-workflow-diagrams.md",
    ],
)
def test_active_worktree_examples_delegate_creation_to_governed_helper(
    path: str,
) -> None:
    text = " ".join(Path(path).read_text(encoding="utf-8").split())
    assert "git worktree add .worktrees/" not in text
    assert "Prefer `git worktree add`" not in text
    assert "`git worktree add` only when" not in text
    assert "governed helper" in text or "governed worktree helper" in text.lower()
