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


def test_normalize_codex_agents_preserves_role_memory_requirements(
    tmp_path: Path,
) -> None:
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    path = agents / "py-test-swarm.md"
    path.write_text(
        "\n".join(
            [
                "## Canonical Sources",
                "",
                "Read before planning or editing:",
                "",
                "- `docs/00-project/NORMATIVE_SOURCES.md`",
                "- `AGENTS.md`",
                "",
                "# py-test-swarm",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_agents(tmp_path, check_only=False)

    assert issues == []
    assert (
        "docs/00-project/ai/memory/memory-py-test-swarm.md"
        in path.read_text(encoding="utf-8")
    )


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


def test_normalize_codex_skills_adds_all_governance_tokens(tmp_path: Path) -> None:
    skills = tmp_path / ".codex" / "skills" / "suggest-users"
    skills.mkdir(parents=True)
    path = skills / "SKILL.md"
    path.write_text(
        "\n".join(
            [
                "# Suggest Users",
                "",
                "## Source Of Truth",
                "",
                "- Root runtime contract: `../../../AGENTS.md`",
                "- Project rules: `../../../docs/00-project/RULES.md`",
                "",
                "## Workflow",
                "",
                "1. Suggest reviewers.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_skills(tmp_path, check_only=False)

    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert "../../../docs/01-requirements/REQUIREMENTS.md" in text
    assert "../../../docs/02-architecture/decisions" in text
    assert "../../../docs/00-project/NORMATIVE_SOURCES.md" in text


def test_sync_docs_skill_mirrors_adds_runtime_header_and_tokens(
    tmp_path: Path,
) -> None:
    skills = tmp_path / "docs/00-project/ai/skills/local/public/architecture-guardian"
    skills.mkdir(parents=True)
    path = skills / "SKILL.md"
    path.write_text(
        "\n".join(
            [
                "---",
                'name: "architecture-guardian"',
                "---",
                "",
                "# Architecture Guardian",
                "",
                "## Workflow",
                "",
                "1. Check architecture.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.sync_docs_skill_mirrors(tmp_path, check_only=False)

    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert text.startswith("> Mirror status:")
    assert "not a canonical runtime surface" in "\n".join(text.splitlines()[:40])
    assert ".codex/skills/public/architecture-guardian/SKILL.md" in "\n".join(
        text.splitlines()[:40]
    )
    assert "AI_RUNTIME_MIRROR_OWNERSHIP.md" in "\n".join(text.splitlines()[:40])
    assert "../../../../../../AGENTS.md" in text
    assert "../../../../NORMATIVE_SOURCES.md" in text

    before = text
    assert sync_ai_governance.sync_docs_skill_mirrors(tmp_path, check_only=False) == []
    assert path.read_text(encoding="utf-8") == before
