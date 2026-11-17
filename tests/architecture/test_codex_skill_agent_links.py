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
NEIGHBOR_SKILL_RE = re.compile(r"use ([a-z0-9-]+)\.$")
LIVE_SKILL_HEADING = "## Live skills"
RETIRED_SKILL_HEADING = "## Retired names"
BACKTICK_SKILL_RE = re.compile(r"`([a-z0-9-]+)`")
DESCRIPTION_LIMIT = 200


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
    assert project_names
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


def _runtime_skill_names(root: Path) -> set[str]:
    return {_expected_skill_name(path) for path in _skill_files(root)}


def _live_index_names(text: str, path: Path) -> set[str]:
    start = text.find(LIVE_SKILL_HEADING)
    end = text.find(RETIRED_SKILL_HEADING, start + 1)
    assert start != -1 and end != -1, f"{path} must mark live and retired sections"
    return set(BACKTICK_SKILL_RE.findall(text[start:end]))


def test_codex_skill_descriptions_route_to_one_neighbor() -> None:
    """Trigger text stays short and points away from the neighboring skill."""
    root = _project_root()
    names = _runtime_skill_names(root)
    problems: list[str] = []

    for skill_path in _skill_files(root):
        frontmatter = _frontmatter(skill_path)
        name = str(frontmatter["name"])
        description = frontmatter.get("description")
        if not isinstance(description, str):
            problems.append(f"{name}: description must be a string")
            continue
        if len(description) > DESCRIPTION_LIMIT:
            problems.append(
                f"{name}: description length {len(description)} > {DESCRIPTION_LIMIT}"
            )
        match = NEIGHBOR_SKILL_RE.search(description)
        neighbor = match.group(1) if match else ""
        if neighbor not in names or neighbor == name:
            problems.append(f"{name}: description must end with a different live skill")

    assert problems == []


def test_devin_shared_skill_descriptions_match_codex() -> None:
    """Devin may keep its own skill body, but the trigger sentence stays aligned."""
    root = _project_root()
    mismatches: list[str] = []

    for skill_path in _skill_files(root):
        devin_path = root / ".devin" / "skills" / skill_path.parent.name / "SKILL.md"
        if not devin_path.is_file():
            mismatches.append(f"missing Devin skill: {skill_path.parent.name}")
            continue
        codex_description = _frontmatter(skill_path).get("description")
        devin_description = _frontmatter(devin_path).get("description")
        if codex_description != devin_description:
            mismatches.append(skill_path.parent.name)

    assert mismatches == []


def test_docs_skill_indexes_list_only_live_runtime_skills() -> None:
    """Operator indexes must not advertise skills that are absent from Codex."""
    root = _project_root()
    expected = _runtime_skill_names(root)
    problems: list[str] = []
    index_paths = (
        root / "docs" / "00-project" / "ai" / "skills" / "SKILLS-CATALOG.md",
        root / "docs" / "00-project" / "ai" / "skills" / "SKILLS-PRACTICAL-INDEX.md",
    )

    for path in index_paths:
        found = _live_index_names(path.read_text(encoding="utf-8"), path)
        if found != expected:
            problems.append(
                f"{path.relative_to(root).as_posix()}: extra={sorted(found - expected)} "
                f"missing={sorted(expected - found)}"
            )

    assert problems == []
