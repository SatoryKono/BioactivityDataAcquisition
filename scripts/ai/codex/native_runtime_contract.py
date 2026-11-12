#!/usr/bin/env python3
"""Static contract helpers for the project-scoped Codex runtime."""

from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
import tomllib
from pathlib import Path
from typing import Any


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
ROOT_CONTRACT_FILE = "AGENTS.md"
DEVIN_CONFIG_FILE = ".devin/config.json"
DEVIN_RUNTIME_FILE = ".devin/agents/DEVIN-RUNTIME.md"
CODEX_RUNTIME_FILE = ".codex/agents/CODEX-RUNTIME.md"
RULE_NATIVE_CANDIDATE = "native_candidate"
RULE_CONFIGURATION = "configuration"
RULE_INSTRUCTION_DRIVEN = "instruction_driven"
RULE_SELECTED_PROFILE = "selected_profile"
RULE_SELECTED_SKILL = "selected_skill"
RULE_NOT_PROVEN = "NOT_PROVEN"
RULE_SOURCE_PATTERNS = {
    "codex": (
        (RULE_NATIVE_CANDIDATE, "AGENTS.override.md"),
        (RULE_NATIVE_CANDIDATE, ROOT_CONTRACT_FILE),
        (RULE_CONFIGURATION, ".codex/config.toml"),
        (RULE_INSTRUCTION_DRIVEN, CODEX_RUNTIME_FILE),
        (RULE_SELECTED_PROFILE, ".codex/agents/py-*.toml"),
        (RULE_SELECTED_PROFILE, ".codex/agents/py-*.md"),
        (RULE_SELECTED_SKILL, ".codex/skills/*/SKILL.md"),
    ),
    "junie": (
        (RULE_NATIVE_CANDIDATE, ".junie/AGENTS.md"),
        (RULE_NATIVE_CANDIDATE, ROOT_CONTRACT_FILE),
        ("legacy_candidate", ".junie/guidelines.md"),
        (RULE_CONFIGURATION, ".junie/config.json"),
        (RULE_INSTRUCTION_DRIVEN, ".junie/agents/JUNIE-RUNTIME.md"),
        (RULE_SELECTED_PROFILE, ".junie/agents/py-*.md"),
        (RULE_SELECTED_SKILL, ".junie/skills/*/SKILL.md"),
    ),
    "devin": (
        (RULE_NATIVE_CANDIDATE, ROOT_CONTRACT_FILE),
        (RULE_CONFIGURATION, DEVIN_CONFIG_FILE),
        (RULE_INSTRUCTION_DRIVEN, DEVIN_RUNTIME_FILE),
        (RULE_SELECTED_PROFILE, ".devin/agents/*/AGENT.md"),
        (RULE_SELECTED_SKILL, ".devin/skills/*/SKILL.md"),
    ),
    "opencode": (
        ("subordinate_candidate", ROOT_CONTRACT_FILE),
        (RULE_CONFIGURATION, "opencode.json"),
        (RULE_SELECTED_PROFILE, ".opencode/agent/*.md"),
    ),
}
RULE_SOURCE_MAX_BYTES = 1024 * 1024


def _rule_configuration(path: Path, raw: bytes) -> dict[str, object]:
    """Expose only a declared import flag, never credentials or parser details."""
    text = raw.decode("utf-8-sig")
    data = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("configuration must be an object")
    if not path.as_posix().endswith(DEVIN_CONFIG_FILE):
        return {}
    declared = data.get("read_config_from", {}).get("agents_standard")
    return {
        "declared_agents_standard": declared if isinstance(declared, bool) else None
    }


def _rule_source(root: Path, path: Path, connection: str) -> dict[str, object]:
    """Fingerprint only declared repository sources, never raw contents/errors."""
    item: dict[str, object] = {
        "path": path.relative_to(root).as_posix(),
        "connection": connection,
        "presence": "MISSING",
        "loading": RULE_NOT_PROVEN,
        "execution": RULE_NOT_PROVEN,
    }
    try:
        if not path.exists():
            return item
        resolved = path.resolve()
        if not resolved.is_relative_to(
            root.resolve()
        ) or resolved.name.casefold().startswith(".env"):
            raise ValueError("protected or external source")
        with resolved.open("rb") as stream:
            raw = stream.read(RULE_SOURCE_MAX_BYTES + 1)
        if len(raw) > RULE_SOURCE_MAX_BYTES:
            raise ValueError("oversized source")
        item.update(
            presence="PRESENT", sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw)
        )
        if connection == RULE_CONFIGURATION:
            item.update(_rule_configuration(path, raw))
    except (OSError, ValueError, TypeError, AttributeError):
        item.update(presence="ERROR", reason="source unavailable or invalid")
    return item


def rule_loading_inventory(repo_root: Path) -> dict[str, object]:
    """Observe candidate sources only; never infer native loading or execute tools."""
    records = []
    for runtime, patterns in RULE_SOURCE_PATTERNS.items():
        sources = []
        for connection, pattern in patterns:
            paths = (
                sorted(repo_root.glob(pattern))
                if "*" in pattern
                else [repo_root / pattern]
            )
            sources.extend(_rule_source(repo_root, path, connection) for path in paths)
        records.append(
            {
                "runtime": runtime,
                "status": RULE_NOT_PROVEN,
                "version": None,
                "native_configuration": RULE_NOT_PROVEN,
                "model_execution": RULE_NOT_PROVEN,
                "scope": "subordinate" if runtime == "opencode" else "repository",
                "enabled_by_diagnostic": False,
                "sources": sources,
            }
        )
    return {
        "schema_version": 1,
        "status": RULE_NOT_PROVEN,
        "scope": "declared repository candidates; global layers and client state not inspected",
        "runtime_process_started": False,
        "runtimes": records,
    }


BOOTSTRAP_BASELINE_BYTES = 465_721
BOOTSTRAP_BASELINE_LINES = 8_324
BOOTSTRAP_MAX_BYTES = BOOTSTRAP_BASELINE_BYTES * 70 // 100
BOOTSTRAP_CORPUS_PATHS = (
    ROOT_CONTRACT_FILE,
    CODEX_RUNTIME_FILE,
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
    CODEX_RUNTIME_FILE,
    ".codex/agents/ORCHESTRATION.md",
    ".codex/agents/README.md",
    *tuple(f".codex/agents/{name}.md" for name in AGENT_NAMES),
    *tuple(f".codex/agents/{name}.toml" for name in AGENT_NAMES),
    *tuple(f".codex/skills/{name}/SKILL.md" for name in AGENT_NAMES),
    ".junie/agents/JUNIE-RUNTIME.md",
    DEVIN_RUNTIME_FILE,
    ".devin/agents/ORCHESTRATION.md",
    "docs/00-project/ai/memory/agent-memory.md",
    *tuple(f"docs/00-project/ai/memory/memory-{name}.md" for name in AGENT_NAMES),
)
AI_LAUNCHER_TEXT_PATHS = (
    "scripts/ai/vibe/launch.sh",
    "scripts/ai/vibe/launch.ps1",
)
UNSAFE_LAUNCHER_PATTERNS = {
    "full prompt logging": re.compile(r"Prompt:\s*\$\*"),
    "pipe-to-shell installer guidance": re.compile(
        r"curl[^\n|]*\|[^\n]*(?:bash|sh)",
        re.I,
    ),
}
STALE_RUNTIME_PATTERNS = {
    "provider-specific model label": re.compile(r"\b(?:opus|sonnet)\b", re.I),
    "obsolete runtime/tool wording": re.compile(
        r"Claude Code|WebSearch|WebFetch|TodoWrite|Task tool|Read tool|Grep tool"
    ),
    "ghost skill discovery path": re.compile(r"\.agents/skills"),
    "retired role name": re.compile(
        r"py-review-orchestrator|py-architecture-debt-bot|py-test-swarm"
    ),
    "stale catalog count": re.compile(r"\b(?:nine|девять|9 активн)\b", re.I),
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


def validate_ai_launcher_safety(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Reject AI launchers that expose prompt content or pipe downloads to shells."""

    findings: list[Finding] = []
    for relative in AI_LAUNCHER_TEXT_PATHS:
        path = repo_root / relative
        if not path.is_file():
            findings.append(
                Finding("launcher.missing", "AI launcher is missing", relative)
            )
            continue
        content = path.read_text(encoding="utf-8")
        for label, pattern in UNSAFE_LAUNCHER_PATTERNS.items():
            if pattern.search(content):
                findings.append(
                    Finding(
                        "launcher.unsafe",
                        f"contains {label}",
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


def _agent_inventory_findings(agent_dir: Path) -> list[Finding]:
    actual = {path.stem for path in agent_dir.glob("py-*.toml")}
    expected = set(AGENT_NAMES)
    return [
        *(
            Finding(
                "agent.missing",
                f"native descriptor is missing: {name}",
                str(agent_dir),
            )
            for name in sorted(expected - actual)
        ),
        *(
            Finding(
                "agent.unexpected",
                f"unexpected native descriptor: {name}",
                str(agent_dir),
            )
            for name in sorted(actual - expected)
        ),
    ]


def _load_agent_descriptor(
    path: Path,
) -> tuple[dict[str, object] | None, Finding | None]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8")), None
    except (OSError, tomllib.TOMLDecodeError) as exc:
        return None, Finding("agent.invalid", str(exc), str(path))


def _agent_descriptor_field_findings(
    agent_name: str,
    path: Path,
    data: dict[str, object],
) -> list[Finding]:
    findings = [
        Finding(
            "agent.field",
            f"required non-empty string is missing: {key}",
            str(path),
        )
        for key in ("name", "description", "developer_instructions")
        if not isinstance(data.get(key), str) or not str(data[key]).strip()
    ]
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
    return findings


def _agent_instruction_findings(
    repo_root: Path,
    agent_name: str,
    path: Path,
    instructions: str,
) -> list[Finding]:
    required_refs = (
        ROOT_CONTRACT_FILE,
        f".codex/agents/{agent_name}.md",
        f".codex/skills/{agent_name}/SKILL.md",
        f"docs/00-project/ai/memory/memory-{agent_name}.md",
    )
    findings: list[Finding] = []
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


def validate_agents(repo_root: Path = REPO_ROOT) -> list[Finding]:
    agent_dir = repo_root / ".codex/agents"
    findings = _agent_inventory_findings(agent_dir)
    for agent_name in AGENT_NAMES:
        path = agent_dir / f"{agent_name}.toml"
        if not path.is_file():
            continue
        data, load_finding = _load_agent_descriptor(path)
        if load_finding is not None:
            findings.append(load_finding)
            continue
        assert data is not None
        findings.extend(_agent_descriptor_field_findings(agent_name, path, data))
        instructions = data.get("developer_instructions", "")
        findings.extend(
            _agent_instruction_findings(
                repo_root,
                agent_name,
                path,
                instructions if isinstance(instructions, str) else "",
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


def validate_skill_routes(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Resolve explicit agent skill allowlists within their own runtime tree."""
    findings: list[Finding] = []
    for runtime in (".codex", ".junie", ".devin"):
        agents = repo_root / runtime / "agents"
        paths = [
            *agents.glob("py-*.md"),
            *agents.glob("py-*.toml"),
            *agents.glob("*/AGENT.md"),
        ]
        for path in paths:
            content = path.read_text(encoding="utf-8")
            allowlist = content.partition("Allowed skills:")[2]
            if not allowlist:
                continue
            allowlist = re.split(r"\.\s|\n\s*\n|Allowed MCP:", allowlist, maxsplit=1)[0]
            entries = re.split(r"[,;]|\band\b", allowlist)
            for entry in entries:
                name = entry.strip().removesuffix("opt-in").strip().strip("`.")
                valid_name = re.fullmatch(r"[a-z][a-z0-9_-]*", name)
                if (
                    not valid_name
                    or not (
                        repo_root / runtime / "skills" / name / "SKILL.md"
                    ).is_file()
                ):
                    findings.append(
                        Finding(
                            "skill.route",
                            f"project skill entrypoint is missing: {name}",
                            path.relative_to(repo_root).as_posix(),
                        )
                    )
    return findings


DEVIN_RESTRICTED_PROFILES = frozenset(
    {"py-audit-bot", "py-debug-bot", "py-plan-bot", "py-test-bot"}
)
DEVIN_READ_TOOLS = frozenset({"read", "grep", "glob"})
DEVIN_PROFILE_CODE = "devin.profile"
DEVIN_TOOLS_KEY = "allowed-tools"
DEVIN_PERMISSIONS_KEY = "permissions"
DEVIN_DELEGATION_BLOCK = "Native delegation of restricted profiles is blocked until"


def _devin_permission_groups(path: Path) -> dict[str, set[str]]:
    permissions = json.loads(path.read_text(encoding="utf-8"))["permissions"]
    groups = {}
    for key in ("ask", "allow", "deny"):
        values = permissions[key]
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise ValueError("invalid permission list")
        groups[key] = set(values)
    return groups


def _devin_project_findings(path: Path, groups: dict[str, set[str]]) -> list[Finding]:
    findings = []
    if groups["ask"] & groups["allow"]:
        findings.append(
            Finding("devin.permissions", "ask/allow intersection", str(path))
        )
    for rule in ("Read(.env*)", "Read(**/.env*)"):
        if rule not in groups["ask"] or rule in groups["allow"]:
            findings.append(
                Finding(
                    "devin.env", "env read must have one project ask policy", str(path)
                )
            )
    for rule in ("Write(.env*)", "Write(**/.env*)"):
        if rule not in groups["deny"]:
            findings.append(
                Finding("devin.env", "protected env write denial is missing", str(path))
            )
    required_parent_asks = {"exec", "Write(**)"}
    if not required_parent_asks.issubset(groups["ask"]) or (
        required_parent_asks & groups["deny"]
    ):
        findings.append(
            Finding(
                "devin.parent",
                "parent command/write actions must remain explicit",
                str(path),
            )
        )
    if any(
        rule.casefold() == "exec" or rule.casefold().startswith(("exec(", "write("))
        for rule in groups["allow"]
    ):
        findings.append(
            Finding(
                "devin.parent", "automatic command/write grant is prohibited", str(path)
            )
        )
    return findings


def _declared_string_list(text: str, key: str, indent: int) -> list[str]:
    """Accept the governed block-list spelling only, not arbitrary vendor YAML."""
    lines = text.splitlines()
    marker = " " * indent + key + ":"
    pattern = re.compile(r"^" + " " * indent + re.escape(key) + r"[ \t]*:")
    positions = [index for index, line in enumerate(lines) if pattern.match(line)]
    if len(positions) != 1 or lines[positions[0]] != marker:
        raise ValueError("missing/duplicate declared list")
    result = []
    item_indent: int | None = None
    for line in lines[positions[0] + 1 :]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"( *)- (.+)", line)
        if match is None:
            if len(line) - len(line.lstrip()) <= indent:
                break
            raise ValueError("unsupported list continuation")
        current_indent = len(match[1])
        if current_indent < indent or (
            item_indent is not None and current_indent != item_indent
        ):
            raise ValueError("unsupported list indentation")
        item_indent = current_indent
        value = match[2].strip()
        if value.startswith(("'", '"')):
            # Only the unescaped quoted subset is governed here. Python string
            # escapes differ from YAML (notably single quotes); never decode
            # these permission declarations with ast.literal_eval.
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError("unsupported quoted list scalar")
            value = value[1:-1]
            if any(char in value for char in ("\\", "'", '"')):
                raise ValueError("unsupported quoted list escape")
        if not re.fullmatch(r"[A-Za-z]\w*(?:\([^\r\n()]+\))?", value, re.ASCII):
            raise ValueError("unsupported list scalar")
        result.append(value)
    if not result:
        raise ValueError("empty declared list")
    return result


def _validate_devin_mapping_keys(text: str, indent: int, known: set[str]) -> None:
    """Reject quoted, complex, duplicate and unsupported mapping declarations."""
    keys = []
    prefix = " " * indent
    for line in text.splitlines():
        if not line.startswith(prefix):
            continue
        raw = line[indent:]
        if not raw or raw.startswith((" ", "#", "- ")):
            continue
        key, separator, _ = raw.partition(":")
        if not separator:
            raise ValueError("unsupported metadata line")
        keys.append(key.strip())
    if len(set(keys)) != len(keys) or set(keys) - known:
        raise ValueError("duplicate or unsupported metadata key")


def _devin_header(text: str) -> str:
    """Reject ambiguous keys; only line delimiters terminate frontmatter."""
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("missing metadata")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("missing metadata terminator") from exc
    header = "\n".join(lines[1:end]) + "\n"
    known = {
        "name",
        "description",
        "model",
        "max-nesting",
        DEVIN_TOOLS_KEY,
        DEVIN_PERMISSIONS_KEY,
    }
    _validate_devin_mapping_keys(header, 0, known)
    return header


def _devin_tool_metadata(path: Path) -> dict[str, Any]:
    """Read our bounded declaration subset; this is not a native YAML evaluator."""
    header = _devin_header(path.read_text(encoding="utf-8"))
    blocks = re.findall(r"(?m)^permissions:\n((?: +[^\n]*\n|#[^\n]*\n|\n)*)", header)
    if len(blocks) != 1:
        raise ValueError("missing/duplicate permission metadata")
    _validate_devin_mapping_keys(blocks[0], 2, {"allow", "deny"})
    keys = re.findall(r"(?m)^ {2}([^ \t:#-][^:\n]*):", blocks[0])
    if len(keys) != 2 or set(keys) != {"allow", "deny"}:
        raise ValueError("duplicate or unsupported permission key")
    return {
        DEVIN_TOOLS_KEY: _declared_string_list(header, DEVIN_TOOLS_KEY, 0),
        DEVIN_PERMISSIONS_KEY: {
            key: _declared_string_list(blocks[0], key, 2) for key in ("allow", "deny")
        },
    }


def _devin_profile_findings(repo_root: Path, name: str) -> list[Finding]:
    path = repo_root / f".devin/agents/{name}/AGENT.md"
    try:
        metadata = _devin_tool_metadata(path)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError):
        return [Finding(DEVIN_PROFILE_CODE, "invalid profile tool contract", str(path))]
    findings = []
    if name in DEVIN_RESTRICTED_PROFILES:
        if set(metadata[DEVIN_TOOLS_KEY]) != DEVIN_READ_TOOLS:
            findings.append(
                Finding(
                    DEVIN_PROFILE_CODE,
                    "restricted profile must expose read/search tools only",
                    str(path),
                )
            )
        findings.extend(_devin_legacy_denial_findings(metadata, name, path))
    return findings


def _devin_legacy_denial_findings(
    metadata: dict[str, Any], name: str, path: Path
) -> list[Finding]:
    """Preserve declared denials without treating legacy metadata as enforcement."""
    try:
        legacy = metadata[DEVIN_PERMISSIONS_KEY]
        allow, deny = legacy["allow"], legacy["deny"]
        if not isinstance(allow, list) or not isinstance(deny, list):
            raise ValueError("invalid legacy lists")
        if any(not isinstance(item, str) for item in [*allow, *deny]):
            raise ValueError("invalid legacy permission")
    except (KeyError, TypeError, ValueError):
        return [
            Finding(
                DEVIN_PROFILE_CODE,
                "declared legacy denials must be preserved",
                str(path),
            )
        ]
    expected = {"write", "edit"}
    if name == "py-test-bot":
        expected = {
            "Write(src/**)",
            "Write(configs/**)",
            "Write(docs/**)",
            "Exec(gh)",
            "Exec(hub)",
        }
    findings = []
    if not expected.issubset(set(deny)):
        findings.append(
            Finding(
                DEVIN_PROFILE_CODE, "declared legacy denials were weakened", str(path)
            )
        )
    if any(
        item.casefold() in {"exec", "write", "edit"}
        or item.casefold().startswith(("exec(", "write("))
        for item in allow
    ):
        findings.append(
            Finding(
                DEVIN_PROFILE_CODE,
                "restricted legacy metadata must not grant commands/writes",
                str(path),
            )
        )
    return findings


def validate_devin_permission_contract(repo_root: Path) -> list[Finding]:
    """Check declared fail-closed routes; never claim native/OS enforcement."""
    config = repo_root / DEVIN_CONFIG_FILE
    try:
        groups = _devin_permission_groups(config)
    except (OSError, ValueError, KeyError, TypeError):
        return [
            Finding(
                "devin.permissions", "invalid project permission contract", str(config)
            )
        ]
    findings = _devin_project_findings(config, groups)
    runtime_path = repo_root / DEVIN_RUNTIME_FILE
    try:
        blocked = DEVIN_DELEGATION_BLOCK in runtime_path.read_text(encoding="utf-8")
    except OSError:
        blocked = False
    if not blocked:
        findings.append(
            Finding(
                "devin.delegation",
                "unqualified restricted delegation must stay blocked",
                str(runtime_path),
            )
        )
    for name in AGENT_NAMES:
        findings.extend(_devin_profile_findings(repo_root, name))
    return findings


def validate_native_runtime(repo_root: Path = REPO_ROOT) -> list[Finding]:
    """Validate every repository-native Codex discovery surface."""

    return [
        *validate_project_config(repo_root),
        *validate_agents(repo_root),
        *validate_canonical_skills(repo_root),
        *validate_skill_routes(repo_root),
        *validate_runtime_context(repo_root),
        *validate_ai_launcher_safety(repo_root),
        *validate_devin_permission_contract(repo_root),
    ]
