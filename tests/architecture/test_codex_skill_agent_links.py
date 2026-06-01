"""Architecture guardrails for Codex skill runtime links."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture

def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _skill_files(root: Path) -> list[Path]:
    return sorted((root / ".codex" / "skills").glob("*/SKILL.md"))


def test_codex_skills_must_not_reference_ai_claude_runtime_tree() -> None:
    """Prevent new Codex skill dependencies on the retiring `ai/claude` tree."""
    root = _project_root()
    offenders: list[str] = []

    for skill_path in _skill_files(root):
        content = skill_path.read_text(encoding="utf-8")
        if "ai/claude/" in content:
            offenders.append(skill_path.relative_to(root).as_posix())

    assert offenders == [], (
        "Retiring 'ai/claude/' references found in Codex skill files: "
        + ", ".join(offenders)
    )
