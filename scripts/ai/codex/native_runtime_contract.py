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
AGENT_NAMES = (
    "py-audit-bot",
    "py-config-bot",
    "py-debug-bot",
    "py-doc-bot",
    "py-plan-bot",
    "py-test-bot",
)
READ_ONLY_AGENTS = {
    "py-audit-bot",
    "py-debug-bot",
    "py-plan-bot",
}
BOOTSTRAP_BASELINE_BYTES = 465_721
BOOTSTRAP_BASELINE_LINES = 8_324
BOOTSTRAP_MAX_BYTES = BOOTSTRAP_BASELINE_BYTES * 70 // 100
BOOTSTRAP_CORPUS_PATHS = (
    "AGENTS.md",
    ".codex/agents/CODEX-RUNTIME.md",
    ".codex/agents/ORCHESTRATION.md",
    *tuple(f".codex/agents/{name}.md" for name in AGENT_NAMES),
    *tuple(f".codex/skills/{name}/SKILL.md" for name in AGENT_NAMES),
    ".codex/skills/py-audit-bot/references/wrapper-contract.md",
    "docs/00-project/NORMATIVE_SOURCES.md",
    "docs/00-project/RULES.md",
    "docs/01-requirements/REQUIREMENTS.md",
    "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
    "docs/00-project/ai/memory/agent-memory.md",
    *tuple(f"docs/00-project/ai/memory/memory-{name}.md" for name in AGENT_NAMES),
    "src/memory/DAILY_WORKFLOW.md",
)
ACTIVE_RUNTIME_TEXT_PATHS = (
    ".codex/agents/CODEX-RUNTIME.md",
    ".codex/agents/ORCHESTRATION.md",
    ".codex/agents/README.md",
    *tuple(f".codex/agents/{name}.md" for name in AGENT_NAMES),
    *tuple(f".codex/agents/{name}.toml" for name in AGENT_NAMES),
    *tuple(f".codex/skills/{name}/SKILL.md" for name in AGENT_NAMES),
    ".junie/agents/JUNIE-RUNTIME.md",
    ".devin/agents/DEVIN-RUNTIME.md",
    ".devin/agents/ORCHESTRATION.md",
    "docs/00-project/ai/memory/agent-memory.md",
    *tuple(f"docs/00-project/ai/memory/memory-{name}.md" for name in AGENT_NAMES),
)
STALE_RUNTIME_PATTERNS = {
    "provider-specific model label": re.compile(r"\b(?:opus|sonnet)\b", re.I),
    "obsolete runtime/tool wording": re.compile(
        r"Claude Code|WebSearch|WebFetch|TodoWrite|Task tool|Read tool|Grep tool"
    ),
    "ghost skill discovery path": re.compile(r"\.agents/skills"),
    "retired role name": re.compile(
        r"py-review-orchestrator|py-architecture-debt-bot|py-test-swarm"
    ),
    "stale catalog count": re.compile(
        r"\b(?:nine|девять|9 активн)\b", re.I
    ),
}

GENERATED_MARKER = "<!-- generated-by: scripts.ai.codex.native_runtime_contract -->"


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


def bootstrap_corpus_stats(repo_root: Path = REPO_ROOT) -> dict[str, int]:
    """Measure the governed mandatory/root-plus-role bootstrap corpus."""

    byte_count = 0
    line_count = 0
    for relative in BOOTSTRAP_CORPUS_PATHS:
        payload = (repo_root / relative).read_bytes()
        byte_count += len(payload)
        line_count += len(payload.splitlines())
    return {
        "files": len(BOOTSTRAP_CORPUS_PATHS),
        "bytes": byte_count,
        "lines": line_count,
    }


def validate_runtime_context(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Guard the bootstrap budget and reject stale runtime semantics."""

    findings: list[Finding] = []
    missing = [
        relative
        for relative in BOOTSTRAP_CORPUS_PATHS
        if not (repo_root / relative).is_file()
    ]
    for relative in missing:
        findings.append(
            Finding("context.missing", "bootstrap source is missing", relative)
        )
    if not missing:
        stats = bootstrap_corpus_stats(repo_root)
        if stats["bytes"] > BOOTSTRAP_MAX_BYTES:
            findings.append(
                Finding(
                    "context.budget",
                    f"bootstrap corpus is {stats['bytes']} bytes; "
                    f"maximum is {BOOTSTRAP_MAX_BYTES}",
                    "runtime bootstrap corpus",
                )
            )

    for relative in ACTIVE_RUNTIME_TEXT_PATHS:
        path = repo_root / relative
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for label, pattern in STALE_RUNTIME_PATTERNS.items():
            match = pattern.search(content)
            if match:
                findings.append(
                    Finding(
                        "context.stale",
                        f"contains {label}: {match.group(0)!r}",
                        relative,
                    )
                )
    return findings


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
    # Current Codex documentation defines `max_threads` as the legacy alias for
    # `max_concurrent_threads_per_session`. Keep the tracked portable baseline on
    # the already benchmarked alias and value; changing either requires a
    # versioned compatibility check and concurrency evidence.
    if not isinstance(agents, dict) or agents.get("max_threads") != 3:
        findings.append(
            Finding(
                "config.agents",
                "agents.max_threads must equal 3",
                str(path),
            )
        )
    if "max_concurrent_threads_per_session" in agents:
        findings.append(
            Finding(
                "config.agents",
                "use agents.max_threads = 3 for the tracked portable baseline; "
                "Codex documents it as the legacy alias for "
                "agents.max_concurrent_threads_per_session",
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


def validate_canonical_skills(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Validate the sole project-scoped Codex skill discovery surface."""

    try:
        canonical_skills(repo_root)
    except ValueError as exc:
        return [
            Finding("skill.canonical", str(exc), str(repo_root / CANONICAL_SKILLS_DIR))
        ]
    return []


def validate_native_runtime(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Validate every repository-native Codex discovery surface."""

    return [
        *validate_project_config(repo_root),
        *validate_agents(repo_root),
        *validate_canonical_skills(repo_root),
        *validate_runtime_context(repo_root),
    ]
