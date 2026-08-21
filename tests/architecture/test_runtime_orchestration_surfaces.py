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

DEVIN_PY_BOT_SKILLS = (
    Path(".devin/skills/py-audit-bot/SKILL.md"),
    Path(".devin/skills/py-config-bot/SKILL.md"),
    Path(".devin/skills/py-debug-bot/SKILL.md"),
    Path(".devin/skills/py-doc-bot/SKILL.md"),
    Path(".devin/skills/py-plan-bot/SKILL.md"),
    Path(".devin/skills/py-test-bot/SKILL.md"),
)


def test_active_runtime_orchestration_surfaces_do_not_reference_py_doc_swarm() -> None:
    for relative_path in ACTIVE_RUNTIME_ORCHESTRATION_FILES:
        text = relative_path.read_text(encoding="utf-8")
        assert "py-doc-swarm" not in text, (
            f"{relative_path} should use current docs-audit surfaces instead of "
            "legacy docs-swarm references"
        )


def test_devin_py_bot_skills_point_team_orchestration_at_devin_runtime() -> None:
    for relative_path in DEVIN_PY_BOT_SKILLS:
        text = relative_path.read_text(encoding="utf-8")
        assert ".codex/agents/ORCHESTRATION.md" not in text, (
            f"{relative_path} must not route Devin Team orchestration to Codex"
        )
        assert "Team orchestration: `../../agents/ORCHESTRATION.md`" in text, (
            f"{relative_path} must point Team orchestration at "
            ".devin/agents/ORCHESTRATION.md via ../../agents/ORCHESTRATION.md"
        )


def test_devin_py_test_bot_does_not_invent_domain_coverage_gate() -> None:
    """#9293: Devin py-test-bot follows RULES ≥85% overall, not a 90% domain MUST."""
    text = Path(".devin/agents/py-test-bot/AGENT.md").read_text(encoding="utf-8")
    assert "≥90% domain" not in text
    assert "Coverage (domain)" not in text
    assert "≥85%" in text


def test_mcp_docker_prune_ps1_supports_dry_run() -> None:
    """#9296: PowerShell MCP prune honors BIOETL_MCP_PRUNE_DRY_RUN; bash stays apply-opt-in."""
    sh = Path("scripts/ai/mcp/support/mcp_docker_prune.sh").read_text(encoding="utf-8")
    ps1 = Path("scripts/ai/mcp/support/mcp_docker_prune.ps1").read_text(encoding="utf-8")
    assert "MCP_DOCKER_PRUNE_APPLY" in sh
    assert "BIOETL_MCP_PRUNE_DRY_RUN" in ps1
    assert "dry-run: would docker rm -f" in ps1
    assert "docker rm -f" in sh
