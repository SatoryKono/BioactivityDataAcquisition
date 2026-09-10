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
EXPECTED_GROK_AGENTS = {
    "explore",
    "plan",
    "py-audit-bot",
    "py-config-bot",
    "py-debug-bot",
    "py-doc-bot",
    "py-plan-bot",
    "py-test-bot",
}


def test_tracked_grok_child_agents_are_exactly_the_wave_b_set() -> None:
    names = {path.stem for path in GROK_AGENTS.glob("*.md")}
    assert names == EXPECTED_GROK_AGENTS
    assert "py-github-bot" not in names
    assert "implementer" not in names
    assert "obs-dashboard" not in names


def test_grok_child_agents_use_named_mcp_without_github() -> None:
    for path in sorted(GROK_AGENTS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        assert "mcpInheritance:" in text, path
        assert "named:" in text, path
        assert "mcpInheritance: all" not in text
        named_mcp_block = _named_mcp_block(text)
        assert "github" not in named_mcp_block
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
    if start < 0:
        return ""
    frontmatter_start = text.find("\n") + 1
    end = text.find("\n---", frontmatter_start)
    if end < 0:
        end = text.find("\r\n---", frontmatter_start)
    if end < 0:
        end = len(text)
    return text[start:end]
