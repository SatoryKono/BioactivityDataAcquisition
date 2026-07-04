"""Unit tests for AI governance sync script."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai import sync_ai_governance

pytestmark = pytest.mark.unit


def test_normalize_codex_agents_strips_mirror_header(tmp_path: Path) -> None:
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    path = agents / "demo.md"
    path.write_text(
        "> Mirror status: mirror\n"
        "> Edit runtime first.\n"
        "______________________________________________________________________\n\n"
        "# Demo\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_agents(tmp_path, check_only=False)
    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert "Mirror status" not in text
    assert "NORMATIVE_SOURCES.md" in text


def test_inject_docs_agent_sources_adds_block(tmp_path: Path) -> None:
    agents = tmp_path / "docs/00-project/ai/agents/agents"
    agents.mkdir(parents=True)
    path = agents / "demo.md"
    path.write_text(
        "> Mirror status: mirror\n"
        "______________________________________________________________________\n\n"
        "name: demo\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.inject_docs_agent_sources(tmp_path, check_only=False)
    assert issues == []
    assert "## Canonical Sources" in path.read_text(encoding="utf-8")
