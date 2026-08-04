#!/usr/bin/env python3
"""Static contract helpers for the project-scoped Codex runtime."""

from __future__ import annotations

import ast
import dataclasses
import re
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_SKILLS_DIR = Path(".codex/skills")
DISCOVERY_SKILLS_DIR = Path(".agents/skills")
GENERATED_MARKER = "<!-- generated-by: scripts/ai/codex/sync_native_skills.py -->"
AGENT_NAMES = (
    "py-architecture-debt-bot",
    "py-audit-bot",
    "py-config-bot",
    "py-debug-bot",
    "py-doc-bot",
    "py-plan-bot",
    "py-review-orchestrator",
    "py-test-bot",
    "py-test-swarm",
)
READ_ONLY_AGENTS = {
    "py-architecture-debt-bot",
    "py-audit-bot",
    "py-debug-bot",
    "py-plan-bot",
    "py-review-orchestrator",
    "py-test-swarm",
}


@dataclasses.dataclass(frozen=True)
class Finding:
    """One actionable static-contract finding."""

    code: str
    message: str
    path: str

    def as_dict(self) -> dict[str, str]:
        return dataclasses.asdict(self)


def _frontmatter_value(raw: str) -> str:
    value = raw.strip()
    if value.startswith(("'", '"')):
        parsed = ast.literal_eval(value)
        if not isinstance(parsed, str):
            raise ValueError("frontmatter value must be a string")
        return parsed
    return value


def skill_metadata(skill_file: Path) -> tuple[str, str]:
    """Read the required name and description from a canonical SKILL.md."""

    lines = skill_file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"missing YAML frontmatter in {skill_file}")

    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, separator, raw = line.partition(":")
        if separator and key.strip() in {"name", "description"}:
            values[key.strip()] = _frontmatter_value(raw)
    missing = {"name", "description"} - values.keys()
    if missing:
        raise ValueError(f"missing {sorted(missing)} in {skill_file}")
    return values["name"], values["description"]


def canonical_skills(repo_root: Path = REPO_ROOT) -> dict[str, tuple[str, str]]:
    """Return canonical skill directory names and discovery metadata."""

    root = repo_root / CANONICAL_SKILLS_DIR
    result: dict[str, tuple[str, str]] = {}
    for skill_file in sorted(root.glob("*/SKILL.md")):
        directory_name = skill_file.parent.name
        name, description = skill_metadata(skill_file)
        if name != directory_name:
            raise ValueError(
                f"skill name {name!r} does not match directory {directory_name!r}"
            )
        result[directory_name] = (name, description)
    return result


def render_skill_adapter(skill_name: str, description: str) -> str:
    """Render a portable native-discovery adapter for one canonical skill."""

    escaped_description = description.replace("\\", "\\\\").replace('"', '\\"')
    return f'''---
name: "{skill_name}"
description: "{escaped_description}"
---

# {skill_name} discovery adapter

{GENERATED_MARKER}

This file exposes the repository skill through Codex native discovery. The
canonical operating contract remains `.codex/skills/{skill_name}/SKILL.md`.

Before taking any task action:

1. Read `.codex/skills/{skill_name}/SKILL.md` completely.
2. Follow that canonical skill and every required reference it selects.
3. Treat this adapter as discovery metadata only; do not redefine behavior here.
'''


def validate_project_config(repo_root: Path = REPO_ROOT) -> list[Finding]:
    path = repo_root / ".codex/config.toml"
    if not path.is_file():
        return [
            Finding("config.missing", "tracked project config is missing", str(path))
        ]
    try:
        parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return [Finding("config.invalid", str(exc), str(path))]

    findings: list[Finding] = []
    allowed_top_level = {"agents"}
    unexpected = sorted(set(parsed) - allowed_top_level)
    if unexpected:
        findings.append(
            Finding(
                "config.nonportable",
                f"unexpected project-scoped keys: {', '.join(unexpected)}",
                str(path),
            )
        )
    agents = parsed.get("agents", {})
    if (
        not isinstance(agents, dict)
        or agents.get("max_concurrent_threads_per_session") != 3
    ):
        findings.append(
            Finding(
                "config.agents",
                "agents.max_concurrent_threads_per_session must equal 3",
                str(path),
            )
        )
    content = path.read_text(encoding="utf-8")
    forbidden_patterns = {
        "secret-bearing key": r"(?i)(?:api[_-]?key|access[_-]?token|password)\s*=",
        "home-relative path": r"(?:^|[\s='\"])(?:~[/\\]|\$HOME[/\\])",
        "POSIX workstation path": r"(?:^|[\s='\"])/(?:home|mnt|Users)/",
        "Windows workstation path": r"(?:^|[\s='\"])[A-Za-z]:[\\/]",
    }
    for label, pattern in forbidden_patterns.items():
        if re.search(pattern, content, flags=re.MULTILINE):
            findings.append(
                Finding("config.portability", f"contains {label}", str(path))
            )
    return findings


def validate_agents(repo_root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    agent_dir = repo_root / ".codex/agents"
    actual = {path.stem for path in agent_dir.glob("py-*.toml")}
    expected = set(AGENT_NAMES)
    for missing in sorted(expected - actual):
        findings.append(
            Finding(
                "agent.missing",
                f"native descriptor is missing: {missing}",
                str(agent_dir),
            )
        )
    for extra in sorted(actual - expected):
        findings.append(
            Finding(
                "agent.unexpected",
                f"unexpected native descriptor: {extra}",
                str(agent_dir),
            )
        )

    for agent_name in AGENT_NAMES:
        path = agent_dir / f"{agent_name}.toml"
        if not path.is_file():
            continue
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            findings.append(Finding("agent.invalid", str(exc), str(path)))
            continue
        for key in ("name", "description", "developer_instructions"):
            if not isinstance(data.get(key), str) or not data[key].strip():
                findings.append(
                    Finding(
                        "agent.field",
                        f"required non-empty string is missing: {key}",
                        str(path),
                    )
                )
        if data.get("name") != agent_name:
            findings.append(
                Finding("agent.name", f"name must equal {agent_name!r}", str(path))
            )
        if "model" in data:
            findings.append(
                Finding(
                    "agent.model",
                    "project descriptors must inherit the parent model",
                    str(path),
                )
            )
        expected_sandbox = (
            "read-only" if agent_name in READ_ONLY_AGENTS else "workspace-write"
        )
        if data.get("sandbox_mode") != expected_sandbox:
            findings.append(
                Finding(
                    "agent.sandbox",
                    f"sandbox_mode must equal {expected_sandbox!r}",
                    str(path),
                )
            )
        instructions = data.get("developer_instructions", "")
        required_refs = (
            "AGENTS.md",
            f".codex/agents/{agent_name}.md",
            f".codex/skills/{agent_name}/SKILL.md",
            f"docs/00-project/ai/memory/memory-{agent_name}.md",
        )
        for reference in required_refs:
            if reference not in instructions:
                findings.append(
                    Finding(
                        "agent.instructions",
                        f"developer_instructions must reference {reference}",
                        str(path),
                    )
                )
            elif not (repo_root / reference).is_file():
                findings.append(
                    Finding(
                        "agent.reference",
                        f"referenced owner surface is missing: {reference}",
                        str(path),
                    )
                )
    return findings


def validate_skill_adapters(repo_root: Path = REPO_ROOT) -> list[Finding]:
    findings: list[Finding] = []
    try:
        skills = canonical_skills(repo_root)
    except ValueError as exc:
        return [
            Finding("skill.canonical", str(exc), str(repo_root / CANONICAL_SKILLS_DIR))
        ]

    discovery_root = repo_root / DISCOVERY_SKILLS_DIR
    actual = {path.parent.name for path in discovery_root.glob("*/SKILL.md")}
    expected = set(skills)
    for missing in sorted(expected - actual):
        findings.append(
            Finding(
                "skill.missing",
                f"native discovery adapter is missing: {missing}",
                str(discovery_root),
            )
        )
    for extra in sorted(actual - expected):
        findings.append(
            Finding(
                "skill.unexpected",
                f"unexpected discovery adapter: {extra}",
                str(discovery_root),
            )
        )
    for directory_name, (_, description) in skills.items():
        path = discovery_root / directory_name / "SKILL.md"
        if not path.is_file():
            continue
        expected_content = render_skill_adapter(directory_name, description)
        if path.read_text(encoding="utf-8") != expected_content:
            findings.append(
                Finding(
                    "skill.drift", "adapter differs from generated contract", str(path)
                )
            )
    return findings


def validate_native_runtime(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Validate every repository-native Codex discovery surface."""

    return [
        *validate_project_config(repo_root),
        *validate_agents(repo_root),
        *validate_skill_adapters(repo_root),
    ]
