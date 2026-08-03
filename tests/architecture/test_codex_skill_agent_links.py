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
"""Architecture guardrails for Codex skill runtime links."""

from __future__ import annotations

import os
import re

import pytest

from pathlib import Path
from typing import Any

import yaml


pytestmark = pytest.mark.architecture

FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---", re.DOTALL)
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _skill_files(root: Path) -> list[Path]:
    return sorted((root / ".codex" / "skills").rglob("SKILL.md"))


def _frontmatter(skill_path: Path) -> dict[str, Any]:
    content = skill_path.read_text(encoding="utf-8")
    match = FRONTMATTER_RE.match(content)
    assert match is not None, f"{skill_path} is missing YAML frontmatter"
    payload = yaml.safe_load(match.group("body"))
    assert isinstance(payload, dict), f"{skill_path} frontmatter must be a mapping"
    return payload


def _expected_skill_name(skill_path: Path) -> str:
    return skill_path.parent.name


def _is_local_markdown_target(target: str) -> bool:
    if target.startswith(("http://", "https://", "mailto:", "#")):
        return False
    return target.endswith(".md") or ".md#" in target


def _target_path(skill_path: Path, target: str) -> Path:
    clean_target = target.split("#", 1)[0]
    return (skill_path.parent / clean_target).resolve()


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


def test_codex_skill_frontmatter_names_match_directory_names() -> None:
    """Keep the trigger name aligned with the actual skill directory."""
    root = _project_root()
    mismatches: list[str] = []

    for skill_path in _skill_files(root):
        frontmatter = _frontmatter(skill_path)
        actual = frontmatter.get("name")
        expected = _expected_skill_name(skill_path)
        if actual != expected:
            mismatches.append(
                f"{skill_path.relative_to(root).as_posix()}: name={actual!r}, expected={expected!r}"
            )

    assert mismatches == []


def test_codex_skill_markdown_links_resolve() -> None:
    """Broken skill references defeat progressive disclosure."""
    root = _project_root()
    broken: list[str] = []

    for skill_path in _skill_files(root):
        content = skill_path.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(content):
            target = match.group("target").strip()
            if not _is_local_markdown_target(target):
                continue
            target_path = _target_path(skill_path, target)
            if not target_path.exists():
                broken.append(f"{skill_path.relative_to(root).as_posix()} -> {target}")

    assert broken == []


def test_codex_active_skills_have_openai_metadata_or_explicit_tombstone() -> None:
    """Active project skills should be visible in the skill UI with usable metadata."""
    root = _project_root()
    missing: list[str] = []
    invalid: list[str] = []

    for skill_path in _skill_files(root):
        frontmatter = _frontmatter(skill_path)
        skill_name = str(frontmatter["name"])
        metadata_path = skill_path.parent / "agents" / "openai.yaml"
        if not metadata_path.exists():
            missing.append(skill_path.relative_to(root).as_posix())
            continue

        metadata = yaml.safe_load(metadata_path.read_text(encoding="utf-8"))
        interface = metadata.get("interface") if isinstance(metadata, dict) else None
        if not isinstance(interface, dict):
            invalid.append(
                f"{metadata_path.relative_to(root).as_posix()}: missing interface"
            )
            continue

        default_prompt = interface.get("default_prompt")
        short_description = interface.get("short_description")
        if (
            not isinstance(default_prompt, str)
            or f"${skill_name}" not in default_prompt
        ):
            invalid.append(
                f"{metadata_path.relative_to(root).as_posix()}: default_prompt must mention ${skill_name}"
            )
        if not isinstance(short_description, str) or not (
            25 <= len(short_description) <= 64
        ):
            invalid.append(
                f"{metadata_path.relative_to(root).as_posix()}: short_description must be 25-64 chars"
            )

    assert missing == []
    assert invalid == []


def test_codex_project_skills_do_not_have_user_global_duplicates() -> None:
    """Project `.codex/skills` must win over confusing user-global BioETL copies."""
    root = _project_root()
    home = Path(os.environ.get("HOME", "")).expanduser()
    global_skills_root = home / ".codex" / "skills"
    if not global_skills_root.exists():
        return

    project_names = {_frontmatter(path)["name"] for path in _skill_files(root)}
    duplicate_names: list[str] = []
    for global_skill in sorted(global_skills_root.rglob("SKILL.md")):
        if ".system" in global_skill.parts:
            continue
        frontmatter = _frontmatter(global_skill)
        name = frontmatter.get("name")
        if name in project_names:
            duplicate_names.append(str(name))

    # This is a local environment check, not a project code error.
    # Warn instead of fail to avoid blocking CI on user-global state.
    if duplicate_names:
        pytest.skip(
            f"User-global BioETL skills shadow project skills: {', '.join(duplicate_names)}. "
            "This is a local environment state, not a project code error. "
            "Consider removing or renaming conflicting skills in ~/.codex/skills/."
        )
