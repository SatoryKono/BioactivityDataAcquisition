"""Architecture guardrails for Codex skill -> Claude agent links."""

from __future__ import annotations

import re
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _skill_files(root: Path) -> list[Path]:
    return sorted((root / ".codex" / "skills").glob("*/SKILL.md"))


def test_codex_skills_must_not_reference_removed_codex_agents_dir() -> None:
    """Prevent regressions to deprecated `.codex/agents` paths."""
    root = _project_root()
    offenders: list[str] = []

    for skill_path in _skill_files(root):
        content = skill_path.read_text(encoding="utf-8")
        if ".codex/agents/" in content:
            offenders.append(skill_path.relative_to(root).as_posix())

    assert offenders == [], (
        "Deprecated '.codex/agents/' references found in skill files: "
        + ", ".join(offenders)
    )


def test_codex_skills_claude_agent_links_must_exist() -> None:
    """Every `.claude/agents/*.md` path mentioned in skills must resolve."""
    root = _project_root()
    missing: list[str] = []
    pattern = re.compile(r"`([^`\n]{1,512}\.claude/agents/[^`\n]{1,512}\.md)`")

    for skill_path in _skill_files(root):
        content = skill_path.read_text(encoding="utf-8")
        for rel_ref in pattern.findall(content):
            target = (skill_path.parent / rel_ref).resolve()
            if not target.exists():
                missing.append(
                    f"{skill_path.relative_to(root).as_posix()} -> {rel_ref}"
                )

    assert missing == [], "Broken `.claude/agents` references: " + ", ".join(missing)
