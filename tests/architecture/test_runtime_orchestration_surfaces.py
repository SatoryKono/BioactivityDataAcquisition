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
"""Architecture tests for active runtime orchestration surface wording."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

ACTIVE_RUNTIME_ORCHESTRATION_FILES = (
    Path(".codex/agents/ORCHESTRATION.md"),
    Path(".codex/agents/CODEX-RUNTIME.md"),
)


def test_active_runtime_orchestration_surfaces_do_not_reference_py_doc_swarm() -> None:
    for relative_path in ACTIVE_RUNTIME_ORCHESTRATION_FILES:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use current docs-audit surfaces instead of "
            "legacy docs-swarm references"
        )


def test_devin_role_skills_point_team_orchestration_at_devin_runtime() -> None:
    """#9277: Devin py-* skills must not route Team orchestration through Codex."""
    root = Path(__file__).resolve().parents[2]
    skills_root = root / ".devin" / "skills"
    offenders: list[str] = []
    missing: list[str] = []
    for name in (
        "py-audit-bot",
        "py-config-bot",
        "py-debug-bot",
        "py-doc-bot",
        "py-plan-bot",
        "py-test-bot",
    ):
        skill_path = skills_root / name / "SKILL.md"
        text = skill_path.read_text(encoding="utf-8")
        relative = skill_path.relative_to(root).as_posix()
        if ".codex/agents/ORCHESTRATION.md" in text:
            offenders.append(relative)
        if "Team orchestration: `.devin/agents/ORCHESTRATION.md`" not in text:
            missing.append(relative)
    assert offenders == [], (
        "Devin skills still point Team orchestration at Codex: "
        + ", ".join(offenders)
    )
    assert missing == [], (
        "Devin skills missing .devin/agents/ORCHESTRATION.md Team orchestration: "
        + ", ".join(missing)
    )


def test_gemini_md_does_not_document_retired_make_ai_targets() -> None:
    """#9294: GEMINI.md must use live py-* routes, not missing make ai-* targets."""
    root = Path(__file__).resolve().parents[2]
    text = (root / "GEMINI.md").read_text(encoding="utf-8")
    assert "**make ai-review:**" not in text
    assert "**make ai-test:**" not in text
    assert "**make ai-docs:**" not in text
    assert "py-audit-bot" in text
    assert "py-test-bot" in text
    assert "py-doc-bot" in text


def test_devin_py_test_bot_does_not_invent_domain_coverage_gate() -> None:
    """#9293: Devin py-test-bot follows RULES ≥85% overall, not a 90% domain MUST."""
    root = Path(__file__).resolve().parents[2]
    text = (root / ".devin" / "agents" / "py-test-bot" / "AGENT.md").read_text(
        encoding="utf-8"
    )
    assert "≥90% domain" not in text
    assert "Coverage (domain)" not in text
    assert "≥85%" in text


def test_agent_guide_does_not_recommend_git_add_dot() -> None:
    """#9292: AGENT.md must not recommend `git add .`."""
    root = Path(__file__).resolve().parents[2]
    text = (
        root / "docs" / "00-project" / "ai" / "agents" / "guides" / "AGENT.md"
    ).read_text(encoding="utf-8")
    assert "git add . && git commit" not in text
    assert "git add <touched-paths>" in text


def test_mcp_docker_prune_supports_dry_run() -> None:
    """#9296: MCP prune helpers honor BIOETL_MCP_PRUNE_DRY_RUN."""
    root = Path(__file__).resolve().parents[2]
    sh = (root / "scripts" / "ai" / "mcp" / "support" / "mcp_docker_prune.sh").read_text(
        encoding="utf-8"
    )
    ps1 = (
        root / "scripts" / "ai" / "mcp" / "support" / "mcp_docker_prune.ps1"
    ).read_text(encoding="utf-8")
    assert "BIOETL_MCP_PRUNE_DRY_RUN" in sh
    assert "BIOETL_MCP_PRUNE_DRY_RUN" in ps1
    assert "dry-run: would docker rm -f" in sh
    assert "dry-run: would docker rm -f" in ps1
