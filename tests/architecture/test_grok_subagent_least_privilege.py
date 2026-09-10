# pyright: reportUnknownMemberType=false
"""Least-privilege contract for Grok child agents and Codex py-* descriptors."""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

from scripts.ai.codex import native_runtime_contract

pytestmark = pytest.mark.architecture
ROOT = Path(__file__).resolve().parents[2]
GROK_AGENTS = ROOT / "docs/00-project/ai/grok/agents"
GROK_PERSONAS = ROOT / "docs/00-project/ai/grok/personas"
EXPECTED_GROK_AGENTS = {
    "explore",
    "implementer",
    "obs-dashboard",
    "plan",
    "py-audit-bot",
    "py-config-bot",
    "py-debug-bot",
    "py-doc-bot",
    "py-plan-bot",
    "py-test-bot",
}
EXPECTED_GROK_ONLY_AGENTS = {"implementer", "obs-dashboard"}
EXPECTED_GROK_PERSONAS = {"closeout-table", "rca-handoff"}
GOVERNED_PY_AGENTS = {
    "py-audit-bot",
    "py-config-bot",
    "py-debug-bot",
    "py-doc-bot",
    "py-plan-bot",
    "py-test-bot",
}


def test_tracked_grok_child_agents_are_wave_b_plus_grok_only() -> None:
    names = {path.stem for path in GROK_AGENTS.glob("*.md")}
    assert names == EXPECTED_GROK_AGENTS
    assert "py-github-bot" not in names
    assert EXPECTED_GROK_ONLY_AGENTS <= names
    assert not (ROOT / ".codex/agents/implementer.md").exists()
    assert not (ROOT / ".codex/agents/obs-dashboard.md").exists()
    assert not (ROOT / ".junie/agents/implementer.md").exists()
    assert not (ROOT / ".devin/agents/implementer.md").exists()
    assert set(native_runtime_contract.AGENT_NAMES) == GOVERNED_PY_AGENTS


def test_grok_only_agents_keep_named_mcp_without_github() -> None:
    implementer = (GROK_AGENTS / "implementer.md").read_text(encoding="utf-8")
    obs = (GROK_AGENTS / "obs-dashboard.md").read_text(encoding="utf-8")
    assert _named_mcp_names(implementer) == ["ast-grep", "code-analyzer"]
    assert _named_mcp_names(obs) == ["grafana", "prometheus"]
    assert "docker-compose.monitoring.yml" in obs
    assert "DEGRADED_MCP" in obs
    assert "git push" in implementer
    assert "worktree" in implementer.lower()


def test_grok_personas_are_overlays_without_mcp_or_github_tools() -> None:
    names = {path.stem for path in GROK_PERSONAS.glob("*.toml")}
    assert names == EXPECTED_GROK_PERSONAS
    for path in sorted(GROK_PERSONAS.glob("*.toml")):
        text = path.read_text(encoding="utf-8")
        data = tomllib.loads(text)
        assert "mcpInheritance" not in text
        assert "mcp" not in data
        instructions = str(data["instructions"])
        assert "gh" in instructions.lower()
        assert "github-ops" not in path.stem


def test_grok_child_agents_use_named_mcp_without_github() -> None:
    for path in sorted(GROK_AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "mcpInheritance:" in text, path
        assert "named:" in text, path
        assert "mcpInheritance: all" not in text
        assert "- github" not in text
        assert "github" not in _named_mcp_block(text)
        assert "Do not run `gh`" in text or "Do not run gh" in text


def test_codex_py_toml_declares_allowed_and_forbidden_mcp() -> None:
    for name in native_runtime_contract.AGENT_NAMES:
        text = (ROOT / ".codex/agents" / f"{name}.toml").read_text(encoding="utf-8")
        data = tomllib.loads(text)
        instructions = str(data["developer_instructions"])
        assert "Allowed MCP" in instructions, name
        assert "Forbidden MCP includes github" in instructions, name
        assert "Do not call undeclared MCP" in instructions, name
        profile = (ROOT / ".codex/agents" / f"{name}.md").read_text(encoding="utf-8")
        assert "Forbidden MCP includes `github`" in profile, name


def _named_mcp_block(text: str) -> str:
    start = text.find("mcpInheritance:")
    end = text.find("\n---", start + 1)
    if end < 0:
        end = text.find("\n\n", start)
    return text[start:end]


def _named_mcp_names(text: str) -> list[str]:
    names: list[str] = []
    for line in _named_mcp_block(text).splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            names.append(stripped[2:].strip())
    return names

