"""Gitignore last-match policy for secrets and tracked agent skills (#9698).REQ-ENV-003: secrets stay out of git and agent surfaces."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def test_gitignore_ignores_dotenv_and_keeps_example() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "\n.env\n" in gitignore or gitignore.startswith(".env\n")
    assert "!.env.example" in gitignore
    ignored = subprocess.check_output(
        ["git", "check-ignore", "-v", ".env"],
        cwd=ROOT,
        text=True,
    )
    assert ".gitignore:" in ignored
    assert ".env" in ignored
    not_ignored = subprocess.run(
        ["git", "check-ignore", "-q", ".env.example"],
        cwd=ROOT,
        check=False,
    )
    assert not_ignored.returncode == 1


def test_gitignore_last_match_keeps_agents_skill_unignore() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    marker = "!.agents/skills/*/SKILL.md"
    assert marker in gitignore
    after = gitignore.split(marker, 1)[-1]
    assert "\n.agents/\n" not in after
    assert not after.lstrip().startswith(".agents/")


def test_startup_wrappers_share_mcp_check_path() -> None:
    sh = (ROOT / "scripts" / "startup.sh").read_text(encoding="utf-8")
    ps1 = (ROOT / "scripts" / "startup.ps1").read_text(encoding="utf-8")
    assert "scripts/ai/mcp/check.sh" in sh
    assert "scripts/ai/mcp/check.sh" in ps1
    assert "codex mcp list" not in ps1


def test_runtime_guides_start_at_agents_and_runtime_maps() -> None:
    for rel in (
        "docs/00-project/ai/agents/guides/CODEX.md",
        "docs/00-project/ai/agents/guides/GEMINI.md",
        "docs/00-project/ai/agents/guides/AGENT.md",
        "GEMINI.md",
    ):
        text = (ROOT / rel).read_text(encoding="utf-8")
        agents_at = text.find("`AGENTS.md`")
        assert agents_at != -1, rel
        prefix = text[: agents_at + 20]
        assert "AGENTS.md" in prefix
        assert "CODEX-RUNTIME.md" in text, rel
        assert "JUNIE-RUNTIME.md" in text, rel


def test_junie_runtime_and_all_agent_language_contracts() -> None:
    junie = (ROOT / ".junie" / "agents" / "JUNIE-RUNTIME.md").read_text(
        encoding="utf-8"
    )
    codex = (ROOT / ".codex" / "agents" / "CODEX-RUNTIME.md").read_text(
        encoding="utf-8"
    )
    needle = "${BIOETL_WSL_VENV_DIR:-$HOME/.venvs/bioetl}/bin/python"
    assert needle in junie
    assert needle in codex
    review_surfaces = (
        "AGENTS.md .codex/agents/CODEX-RUNTIME.md .junie/guidelines.md "
        ".junie/agents/JUNIE-RUNTIME.md .devin/agents/DEVIN-RUNTIME.md "
        ".devin/workflows/review.md .github/copilot-instructions.md GEMINI.md "
        "docs/00-project/ai/rules/cursor/05-agent-workflow.mdc "
        "docs/00-project/ai/rules/windsurf/rules/05-agent-workflow.md "
        "docs/00-project/ai/rules/windsurf/workflows/review.md"
    ).split()
    review_anchors = (
        "`gh pr review`",
        "review body",
        "inline review comments",
        "**MUST** be written in Russian",
    )
    for relative_path in review_surfaces:
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        for anchor in review_anchors:
            text = " ".join(text.split())
            assert anchor in text, f"{relative_path}: missing {anchor}"
    assert "byte-compared" in junie
    assert "junie-mirror-contract.json" in junie
