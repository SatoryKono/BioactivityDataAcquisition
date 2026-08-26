#!/usr/bin/env python3
"""check_doc_drift.py - Detect documentation drift between code and docs.

Verifies that key entities referenced in architecture documentation still
exist in the codebase.  Catches common drift scenarios:

  1. Port protocols renamed/removed but docs still reference old names
  2. Class names changed but architecture docs not updated
  3. Module paths moved but docs still point to old locations
  4. Provider/entity lists changed but reference docs are stale
  5. Factory/registry changes not reflected in composition docs
  6. Active runtime docs mirrors drift from canonical `.codex/` / `.junie/` sources
  7. Freshness/version markers in active docs disagree with canonical runtime docs

Usage:
    python -m scripts.docs check-drift              # Full drift check
    python -m scripts.docs check-drift --ports      # Only port drift
    python -m scripts.docs check-drift --classes    # Only class drift
    python -m scripts.docs check-drift --modules    # Only module path drift
    python -m scripts.docs check-drift --runtime-mirrors
    python -m scripts.docs check-drift --freshness
    python -m scripts.docs check-drift --json       # Machine-readable JSON output

Exit code: 0 = no drift, 1 = drift detected

References:
    - docs/02-architecture/ (layer documentation)
    - docs/00-project/glossary.md (ubiquitous language)
    - ADR-040 (diagram governance)
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scripts.docs.common.bootstrap import DOCS_DIR, PROJECT_ROOT
else:
    from scripts.docs.common.bootstrap import DOCS_DIR, PROJECT_ROOT

SRC_DIR = PROJECT_ROOT / "src" / "bioetl"
MANDATORY_TRACING_COVERAGE_PATH = (
    PROJECT_ROOT / "configs" / "quality" / "mandatory_tracing_coverage.yaml"
)
README_FILENAME = "README.md"
ROOT_README_PATH = PROJECT_ROOT / README_FILENAME
WORKFLOW_GUIDE_PATH = DOCS_DIR / "03-guides" / "workflows.md"


@dataclass
class DriftIssue:
    """A single documentation drift finding."""

    category: str
    severity: str  # ERROR, WARNING
    doc_file: str
    detail: str

    def to_dict(self) -> dict[str, str]:
        """Serialize to dictionary."""
        return {
            "category": self.category,
            "severity": self.severity,
            "doc_file": self.doc_file,
            "detail": self.detail,
        }


@dataclass
class DriftReport:
    """Aggregated drift detection results."""

    issues: list[DriftIssue] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        """Count of ERROR-severity issues."""
        return sum(1 for issue in self.issues if issue.severity == "ERROR")

    @property
    def warning_count(self) -> int:
        """Count of WARNING-severity issues."""
        return sum(1 for issue in self.issues if issue.severity == "WARNING")

    def add(
        self,
        category: str,
        severity: str,
        doc_file: str,
        detail: str,
    ) -> None:
        """Append a drift issue to the report."""
        self.issues.append(DriftIssue(category, severity, doc_file, detail))

    def to_dict(self) -> dict[str, object]:
        """Serialize the full report."""
        return {
            "status": "FAIL" if self.error_count else "PASS",
            "errors": self.error_count,
            "warnings": self.warning_count,
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True)
class RuntimeMirrorRule:
    """Pairing between a canonical runtime doc and its published mirror."""

    name: str
    canonical: Path
    mirror: Path
    sections: tuple[str, ...] = ()
    compare_version: bool = False


@dataclass(frozen=True)
class AIDocsMirrorTarget:
    """Docs mirror file that must declare its canonical runtime source."""

    relative_path: Path
    canonical_sources: tuple[Path, ...]


AI_MEMORY_DOCS_DIR = "docs/00-project/ai/memory"
AGENT_MEMORY_DOC = "agent-memory.md"
AGENT_MEMORY_PATH = Path(AI_MEMORY_DOCS_DIR) / AGENT_MEMORY_DOC
FILE_POLICY_PATH = Path("docs/00-project/governance/03-file-policy.md")
RUNTIME_AGENT_GUIDE_PATH = "docs/00-project/ai/agents/guides/MEMORY_USAGE.md"
RUNTIME_POST_CHANGE_PATH = "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md"
RUNTIME_AGENT_MEMORY_PATH = f"{AI_MEMORY_DOCS_DIR}/{AGENT_MEMORY_DOC}"
CODEX_RUNTIME_DOC_PATH = ".codex/agents/CODEX-RUNTIME.md"
GEMINI_RUNTIME_DOC_PATH = ".gemini/agents/GEMINI-RUNTIME.md"
CODEX_RUNTIME_DOC_README_PATH = ".codex/agents/README.md"
GEMINI_RUNTIME_DOC_README_PATH = ".gemini/agents/README.md"
GEMINI_PY_CONFIG_BOT_DOC_PATH = ".gemini/agents/py-config-bot.md"
GEMINI_PY_AUDIT_BOT_DOC_PATH = ".gemini/agents/py-audit-bot.md"
GEMINI_PY_REVIEW_ORCHESTRATOR_DOC_PATH = ".gemini/agents/py-review-orchestrator.md"
CODEX_PY_AUDIT_BOT_DOC_PATH = ".codex/agents/py-audit-bot.md"
CODEX_PY_CONFIG_BOT_DOC_PATH = ".codex/agents/py-config-bot.md"
CODEX_PY_REVIEW_ORCHESTRATOR_DOC_PATH = ".codex/agents/py-review-orchestrator.md"
CODEX_RUNTIME_DOC_TOKEN = CODEX_RUNTIME_DOC_PATH
GEMINI_RUNTIME_DOC_TOKEN = GEMINI_RUNTIME_DOC_PATH
AGENTS_DOC_TOKEN = "AGENTS.md"
NORMATIVE_SOURCES_DOC_TOKEN = "docs/00-project/NORMATIVE_SOURCES.md"
RULES_DOC_TOKEN = "docs/00-project/RULES.md"
REQUIREMENTS_DOC_TOKEN = "docs/01-requirements/REQUIREMENTS.md"
ADR_DIR_DOC_TOKEN = "docs/02-architecture/decisions/"
NORMATIVE_STACK_TOKENS: tuple[str, ...] = (
    NORMATIVE_SOURCES_DOC_TOKEN,
    RULES_DOC_TOKEN,
    REQUIREMENTS_DOC_TOKEN,
    ADR_DIR_DOC_TOKEN,
    AGENTS_DOC_TOKEN,
)
MEMORY_USAGE_TOKEN = "MEMORY_USAGE.md"
POST_CHANGE_TOKEN = "POST_CHANGE_VALIDATION.md"
POST_CHANGE_DOC_TOKEN = "../policy/POST_CHANGE_VALIDATION.md"
MEMORY_DOC_TOKEN = "../memory/agent-memory.md"
GEMINI_AUDIT_BOT_TOKEN = GEMINI_PY_AUDIT_BOT_DOC_PATH
RUNTIME_VERSION_PATTERN = re.compile(r"(?m)^\*Версия:\s*(\d+(?:\.\d+)*)")
RULES_VERSION_PATTERN = re.compile(r"(?m)^Version:\s*(\d+(?:\.\d+)*)")
LAST_UPDATED_PATTERN = re.compile(r"Последнее обновление:\s*(\d{4}-\d{2}-\d{2})")
AI_RULES_README_PATH = Path("docs/00-project/ai/rules/README.md")
CURSOR_RULE_DOCS_DIR = Path("docs/00-project/ai/rules/cursor")
CURSOR_RULES_DIR = Path(".cursor/rules")
WINDSURF_RULE_DOCS_DIR = Path("docs/00-project/ai/rules/windsurf/rules")
WINDSURF_WORKFLOW_DOCS_DIR = Path("docs/00-project/ai/rules/windsurf/workflows")
WINDSURF_REVIEW_PATH = Path("docs/00-project/ai/rules/windsurf/workflows/review.md")
CURSOR_RULE_EXCLUDED_FILENAMES = frozenset({"sonarqube_mcp_instructions.mdc"})
DOCS_MIRROR_SKILLS_DIR = Path("docs/00-project/ai/skills/local")
AI_RULES_MIRROR_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    AI_RULES_README_PATH: (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    ),
    Path("docs/00-project/ai/rules/bioetl-ai-rules.md"): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    ),
}
AI_GEMINI_RUNTIME_CLAIM_GUARD_PATHS: tuple[Path, ...] = (
    Path("GEMINI.md"),
    Path(".github/copilot-instructions.md"),
    Path(".cursor/rules/05-agent-workflow.mdc"),
    Path("docs/00-project/ai/rules/cursor/05-agent-workflow.mdc"),
)
AI_OPTIONAL_LOCAL_RUNTIME_CLAIM_GUARD_PATHS = frozenset(
    {Path(".cursor/rules/05-agent-workflow.mdc")}
)
AI_GEMINI_RUNTIME_CLAIM_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.gemini/\*\*\s+is\s+the\s+active\s+Gemini\s+runtime\s+tree"),
    re.compile(r"\.codex/\*\*\s+and\s+\.gemini/\*\*\s+are\s+active\s+runtime\s+trees"),
    re.compile(
        r"active\s+\.gemini/agents/\*\*\s+and\s+\.gemini/skills/\*\*\s+surfaces"
    ),
    re.compile(r"Runtime source:\s*`?\.codex/agents/?`?,\s*`?\.gemini/agents/?"),
)

RUNTIME_MIRROR_RULES: tuple[RuntimeMirrorRule, ...] = (
    RuntimeMirrorRule(
        name="orchestration",
        canonical=Path(".codex/agents/ORCHESTRATION.md"),
        mirror=Path("docs/00-project/ai/agents/agents/ORCHESTRATION.md"),
        sections=(
            "## Authority and bootstrap",
            "## Risk tiers and routing",
            "## Standard task loop",
        ),
    ),
    RuntimeMirrorRule(
        name="py-audit-bot",
        canonical=Path(CODEX_PY_AUDIT_BOT_DOC_PATH),
        mirror=Path("docs/00-project/ai/agents/agents/py-audit-bot.md"),
        sections=("## Purpose", "## Procedure", "## Finding contract"),
    ),
    RuntimeMirrorRule(
        name="py-config-bot",
        canonical=Path(CODEX_PY_CONFIG_BOT_DOC_PATH),
        mirror=Path("docs/00-project/ai/agents/agents/py-config-bot.md"),
        sections=("## Purpose and authority", "## Canonical hierarchy", "## Procedure"),
    ),
)

RUNTIME_DOC_TOKENS: tuple[str, ...] = (
    RUNTIME_AGENT_GUIDE_PATH,
    RUNTIME_POST_CHANGE_PATH,
)
RUNTIME_DOC_TOKENS_WITH_CANONICAL_RUNTIME: tuple[str, ...] = (
    *RUNTIME_DOC_TOKENS,
    CODEX_RUNTIME_DOC_PATH,
)
RUNTIME_DOC_TOKENS_WITH_MEMORY: tuple[str, ...] = (
    *RUNTIME_DOC_TOKENS,
    RUNTIME_AGENT_MEMORY_PATH,
)
SKILL_REQUIRED_TOKENS: tuple[str, ...] = (
    AGENTS_DOC_TOKEN,
    MEMORY_USAGE_TOKEN,
    POST_CHANGE_TOKEN,
)
WRITE_CAPABLE_SKILL_PATHS = (
    ".codex/skills/observability-dashboard/SKILL.md",
    ".codex/skills/observability-prometheus/SKILL.md",
    ".codex/skills/technical-designer-mermaid/SKILL.md",
    ".codex/skills/vcr-record/SKILL.md",
)
ROLE_PROFILE_MEMO_DOC_TOKENS: tuple[str, ...] = (
    RUNTIME_AGENT_GUIDE_PATH,
    RUNTIME_AGENT_MEMORY_PATH,
)
ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS: tuple[str, ...] = (
    *ROLE_PROFILE_MEMO_DOC_TOKENS,
    RUNTIME_POST_CHANGE_PATH,
)
ROLE_PROFILE_MEMO_DOC_BY_RUNTIME: dict[Path, tuple[str, ...]] = {
    Path(GEMINI_PY_AUDIT_BOT_DOC_PATH): (
        RUNTIME_DOC_TOKENS + (RUNTIME_AGENT_MEMORY_PATH,)
    ),
    Path(".gemini/agents/py-plan-bot.md"): (
        RUNTIME_DOC_TOKENS + (RUNTIME_AGENT_MEMORY_PATH,)
    ),
    Path(GEMINI_PY_CONFIG_BOT_DOC_PATH): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".gemini/agents/py-debug-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".gemini/agents/py-doc-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".gemini/agents/py-test-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(
        ".gemini/agents/py-architecture-debt-bot.md"
    ): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(
        GEMINI_PY_REVIEW_ORCHESTRATOR_DOC_PATH
    ): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".gemini/agents/py-test-swarm.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(CODEX_PY_AUDIT_BOT_DOC_PATH): (
        RUNTIME_DOC_TOKENS + (RUNTIME_AGENT_MEMORY_PATH,)
    ),
    Path(".codex/agents/py-plan-bot.md"): (
        RUNTIME_DOC_TOKENS + (RUNTIME_AGENT_MEMORY_PATH,)
    ),
    Path(CODEX_PY_CONFIG_BOT_DOC_PATH): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".codex/agents/py-debug-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".codex/agents/py-doc-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
    Path(".codex/agents/py-test-bot.md"): ROLE_PROFILE_MEMO_DOC_WITH_POLICY_TOKENS,
}
ACTIVE_NON_CANONICAL_EVIDENCE_SUMMARIES = (
    Path("docs/reports/evidence/project-test-health/SUMMARY.md"),
)
REQUIRED_EVIDENCE_METADATA_FIELDS = frozenset(
    {
        "status",
        "last_verified",
        "canonical_sources",
        "freshness_window_days",
        "owner",
    }
)
AI_SURFACE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path("AGENTS.md"): (
        *RUNTIME_DOC_TOKENS_WITH_CANONICAL_RUNTIME,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    ),
    Path("GEMINI.md"): (
        *RUNTIME_DOC_TOKENS,
        RUNTIME_AGENT_MEMORY_PATH,
        *NORMATIVE_STACK_TOKENS,
    ),
    Path(".github/copilot-instructions.md"): (
        *RUNTIME_DOC_TOKENS,
        *NORMATIVE_STACK_TOKENS,
    ),
    Path(CODEX_RUNTIME_DOC_PATH): (
        *RUNTIME_DOC_TOKENS,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
        AGENTS_DOC_TOKEN,
    ),
    Path("docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md"): (
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
        AGENTS_DOC_TOKEN,
    ),
    Path(CODEX_RUNTIME_DOC_README_PATH): (
        AGENTS_DOC_TOKEN,
        CODEX_RUNTIME_DOC_PATH,
        *RUNTIME_DOC_TOKENS,
    ),
    Path("docs/00-project/ai/agents/guides/CODEX.md"): (
        *RUNTIME_DOC_TOKENS_WITH_MEMORY,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
    ),
    Path("docs/00-project/ai/agents/guides/AGENT.md"): (
        MEMORY_USAGE_TOKEN,
        POST_CHANGE_DOC_TOKEN,
        MEMORY_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
    ),
    WINDSURF_REVIEW_PATH: (
        AGENTS_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    ),
}
AI_WRITE_CAPABLE_SKILL_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path(skill_path): SKILL_REQUIRED_TOKENS for skill_path in WRITE_CAPABLE_SKILL_PATHS
}
AI_ROLE_PROFILE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path(CODEX_PY_AUDIT_BOT_DOC_PATH): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-audit-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-audit-bot.md",
    ),
    Path(".codex/agents/py-plan-bot.md"): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-plan-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-plan-bot.md",
    ),
    Path(CODEX_PY_CONFIG_BOT_DOC_PATH): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-config-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-config-bot.md",
    ),
    Path(".codex/agents/py-debug-bot.md"): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-debug-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-debug-bot.md",
    ),
    Path(".codex/agents/py-doc-bot.md"): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-doc-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-doc-bot.md",
    ),
    Path(".codex/agents/py-test-bot.md"): (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        ".codex/skills/py-test-bot/SKILL.md",
        "docs/00-project/ai/memory/memory-py-test-bot.md",
    ),
}
AI_ROLE_MEMORY_COVERAGE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path("docs/00-project/ai/memory/README.md"): (
        "memory-py-audit-bot.md",
        "memory-py-plan-bot.md",
        "memory-py-test-bot.md",
        "memory-py-config-bot.md",
        "memory-py-debug-bot.md",
        "memory-py-doc-bot.md",
    ),
    AGENT_MEMORY_PATH: (
        "memory-py-audit-bot.md",
        "memory-py-plan-bot.md",
        "memory-py-test-bot.md",
        "memory-py-config-bot.md",
        "memory-py-debug-bot.md",
        "memory-py-doc-bot.md",
    ),
}
AI_MIRROR_NOTICE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path("docs/00-project/ai/skills/README.md"): (
        "Non-Canonical Mirror Notice",
        "docs/00-project/ai/skills/**",
        ".codex/skills/**",
    ),
    Path("docs/00-project/ai/agents/agents/README.md"): (
        "Non-Canonical Mirror Notice",
        "docs/00-project/ai/agents/agents/**",
        ".codex/agents/**",
    ),
}
AI_DOCS_RUNTIME_MIRROR_HEADER_LINE_LIMIT = 40
AI_DOCS_RUNTIME_MIRROR_REQUIRED_TOKENS = (
    "Mirror status:",
    "not a canonical runtime surface",
    "AI_RUNTIME_MIRROR_OWNERSHIP.md",
)
AI_SURFACE_CLAUDE_PATH_PATTERN: re.Pattern[str] = re.compile(r"\.claude/")
AI_SURFACE_FILE_MISSING_MESSAGE = "AI surface file missing"
SKILL_FILE_NAME = "SKILL.md"
AI_SURFACE_STALE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"docs/00-project/ai/agents/runtime/agent-memory\.md"),
    re.compile(r"(?<!\.)runtime/agent-memory\.md"),
)
AI_SURFACE_FORBIDDEN_PATTERNS: dict[Path, tuple[re.Pattern[str], ...]] = {
    Path(CODEX_RUNTIME_DOC_PATH): (AI_SURFACE_CLAUDE_PATH_PATTERN,),
    Path(CODEX_PY_AUDIT_BOT_DOC_PATH): (AI_SURFACE_CLAUDE_PATH_PATTERN,),
}
RULES_VERSION_LITERAL_PATTERN = re.compile(r"RULES\.md v(\d+(?:\.\d+)*)", re.IGNORECASE)
AI_SURFACES_WITH_RULES_VERSION_LITERAL_GUARD: tuple[Path, ...] = (
    Path("docs/00-project/ai/agents/guides/AGENT.md"),
    Path("docs/00-project/00-map.md"),
)


def _collect_classes(directory: Path) -> set[str]:
    """Collect all class names defined under *directory*."""
    classes: set[str] = set()
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.add(node.name)
    return classes


def _collect_modules(directory: Path) -> set[str]:
    """Collect dotted module paths under *directory* relative to src/."""
    modules: set[str] = set()
    src_root = directory
    while src_root.name != "src" and src_root != src_root.parent:
        src_root = src_root.parent
    for py_file in directory.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        rel = py_file.relative_to(src_root).with_suffix("")
        modules.add(".".join(rel.parts))
    return modules


def _extract_backtick_refs(text: str) -> list[str]:
    """Extract all backtick-quoted references from markdown text."""
    text_without_fences = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return re.findall(r"(?<!`)`([^`\n]+)`(?!`)", text_without_fences)


def _read_doc(path: Path) -> str:
    """Read a documentation file, return empty string if missing."""
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _relative_token(from_dir: Path, target: Path) -> str:
    """Return a stable POSIX relative token from one directory to another path."""
    return Path(os.path.relpath(target, start=from_dir)).as_posix()


def _display_relative_path(path: Path) -> str:
    """Return stable POSIX-style report paths across platforms."""
    return path.as_posix()


def _extract_front_matter_metadata(text: str) -> dict[str, object] | None:
    """Return YAML front-matter metadata when a document declares it."""
    if not text.startswith("---\n"):
        return None
    end_marker = "\n---\n"
    end_index = text.find(end_marker, 4)
    if end_index == -1:
        return None
    payload = yaml.safe_load(text[4:end_index]) or {}
    return payload if isinstance(payload, dict) else None


def _rel(path: Path) -> str:
    """Return path relative to repo root for human-readable reporting."""
    return str(path.relative_to(PROJECT_ROOT))


def _extract_section(text: str, heading: str) -> str | None:
    """Extract a markdown section by exact level-2 heading."""
    match = re.search(rf"(?m)^{re.escape(heading)}\s*$", text)
    if match is None:
        return None

    start = match.start()
    next_heading = re.search(r"(?m)^##\s+", text[match.end() :])
    if next_heading is None:
        return text[start:].strip()

    end = match.end() + next_heading.start()
    return text[start:end].strip()


def _normalize_markdown_block(text: str) -> str:
    """Normalize markdown blocks for deterministic comparison."""
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def _extract_runtime_version(text: str) -> str | None:
    """Extract runtime document version from the standard header marker."""
    match = RUNTIME_VERSION_PATTERN.search(text)
    return match.group(1) if match else None


def _extract_rules_version(text: str) -> str | None:
    """Extract the canonical RULES version marker from text."""
    match = RULES_VERSION_PATTERN.search(text)
    return match.group(1) if match else None


def check_ports(report: DriftReport) -> None:
    """Verify port classes referenced in domain-layer docs exist in code."""
    ports_dir = SRC_DIR / "domain" / "ports"
    if _report_missing_ports_dir(report, ports_dir):
        return

    code_classes = _collect_classes(ports_dir)

    doc_path = DOCS_DIR / "02-architecture" / "01-domain-layer.md"
    doc_text = _read_doc(doc_path)
    if _report_missing_domain_layer_doc(report, doc_path, doc_text):
        return

    port_refs = _documented_port_refs(doc_text)
    _report_missing_documented_ports(report, doc_path, port_refs, code_classes)
    _report_ports_facade_gaps(report, ports_dir, port_refs, code_classes)


def check_classes(report: DriftReport) -> None:
    """Verify key classes referenced in architecture docs exist."""
    all_classes = _collect_classes(SRC_DIR)

    doc_checks: list[tuple[Path, list[str]]] = [
        (
            DOCS_DIR / "02-architecture" / "02-application-layer.md",
            [
                "BasePipeline",
                "BaseTransformer",
                "RecordProcessor",
                "BatchExecutor",
                "PipelineRunner",
                "PipelineService",
                "LockRuntimeService",
                "PreflightService",
                "BatchMetricsRecorderService",
                "FilteredDataSource",
                "CompositePipelineRunner",
                "EnrichmentCoordinatorService",
            ],
        ),
        (
            DOCS_DIR / "02-architecture" / "03-infrastructure-layer.md",
            [
                "BronzeWriter",
                "SilverWriter",
                "GoldWriter",
                "BaseHttpAdapter",
                "UnifiedHTTPClient",
                "TokenBucketRateLimiter",
                "CircuitBreakerGuard",
                "MemoryLock",
            ],
        ),
        (
            DOCS_DIR / "02-architecture" / "05-composition-layer.md",
            [
                "GenericPipelineFactory",
            ],
        ),
    ]

    for doc_path, expected_classes in doc_checks:
        if _report_missing_architecture_doc(report, doc_path):
            continue
        doc_text = _read_doc(doc_path)
        doc_refs = set(_extract_backtick_refs(doc_text))
        _report_expected_class_refs(
            report,
            doc_path=doc_path,
            expected_classes=expected_classes,
            all_classes=all_classes,
            doc_refs=doc_refs,
        )

    check_narrative_surfaces(report)


def check_narrative_surfaces(report: DriftReport) -> None:
    """Detect bounded narrative drift in high-traffic published docs."""
    _check_root_readme_interfaces_surface(report)
    _check_workflow_guide_framing(report)


def _check_root_readme_interfaces_surface(report: DriftReport) -> None:
    """Reject a CLI-only interfaces claim when HTTP surfaces are shipped."""
    if not ROOT_README_PATH.exists():
        return

    http_surface_dir = SRC_DIR / "interfaces" / "http"
    if not http_surface_dir.exists():
        return

    readme_text = ROOT_README_PATH.read_text(encoding="utf-8")
    if "INTERFACES (CLI)" in readme_text:
        report.add(
            "narrative",
            "ERROR",
            _display_relative_path(ROOT_README_PATH.relative_to(PROJECT_ROOT)),
            "Root README still describes the interfaces layer as CLI-only while src/bioetl/interfaces/http/ is shipped",
        )


def _check_workflow_guide_framing(report: DriftReport) -> None:
    """Reject backlog-first workflow guide phrases on the shipped control plane."""
    if not WORKFLOW_GUIDE_PATH.exists():
        return

    guide_text = WORKFLOW_GUIDE_PATH.read_text(encoding="utf-8")
    forbidden_phrases = (
        "Workflow Control Plane backlog.",
        "The workflow backlog implies three different identity layers.",
        "Not yet fully shipped from the open backlog:",
    )
    for phrase in forbidden_phrases:
        if phrase in guide_text:
            report.add(
                "narrative",
                "ERROR",
                _display_relative_path(WORKFLOW_GUIDE_PATH.relative_to(PROJECT_ROOT)),
                f"Workflow guide still contains backlog-first framing: {phrase}",
            )


def _report_missing_ports_dir(report: DriftReport, ports_dir: Path) -> bool:
    """Report and return whether the domain ports directory is missing."""
    if ports_dir.exists():
        return False
    report.add(
        "ports",
        "ERROR",
        "src/bioetl/domain/ports/",
        "Ports directory does not exist",
    )
    return True


def _report_missing_domain_layer_doc(
    report: DriftReport,
    doc_path: Path,
    doc_text: str,
) -> bool:
    """Report and return whether the domain layer doc is unavailable."""
    if doc_text:
        return False
    report.add(
        "ports",
        "WARNING",
        str(doc_path.relative_to(PROJECT_ROOT)),
        "Domain layer doc not found — cannot verify port references",
    )
    return True


def _documented_port_refs(doc_text: str) -> set[str]:
    """Return documented public port names from the domain-layer markdown."""
    refs = _extract_backtick_refs(doc_text)
    return {ref for ref in refs if ref.endswith("Port") and ref[0].isupper()}


def _report_missing_documented_ports(
    report: DriftReport,
    doc_path: Path,
    port_refs: set[str],
    code_classes: set[str],
) -> None:
    """Report documented ports that are no longer defined in code."""
    missing_ports = sorted(
        port_ref for port_ref in port_refs if port_ref not in code_classes
    )
    for port_name in missing_ports:
        report.add(
            "ports",
            "ERROR",
            str(doc_path.relative_to(PROJECT_ROOT)),
            f"Port `{port_name}` referenced in docs but not found in domain/ports/",
        )


def _report_ports_facade_gaps(
    report: DriftReport,
    ports_dir: Path,
    port_refs: set[str],
    code_classes: set[str],
) -> None:
    """Report documented ports that exist but are not re-exported via the facade."""
    init_file = ports_dir / "__init__.py"
    if not init_file.exists():
        return
    init_text = init_file.read_text(encoding="utf-8")
    missing_exports = sorted(
        port_name
        for port_name in port_refs
        if port_name in code_classes and port_name not in init_text
    )
    for port_name in missing_exports:
        report.add(
            "ports",
            "WARNING",
            "src/bioetl/domain/ports/__init__.py",
            f"Port `{port_name}` exists but not re-exported in ports facade",
        )


def _report_missing_architecture_doc(report: DriftReport, doc_path: Path) -> bool:
    """Report and return whether a required architecture doc is missing."""
    if doc_path.exists():
        return False
    report.add(
        "classes",
        "WARNING",
        str(doc_path.relative_to(PROJECT_ROOT)),
        "Architecture doc not found — cannot verify class references",
    )
    return True


def _report_expected_class_refs(
    report: DriftReport,
    *,
    doc_path: Path,
    expected_classes: list[str],
    all_classes: set[str],
    doc_refs: set[str],
) -> None:
    """Report missing or undocumented expected architecture classes."""
    for class_name in expected_classes:
        if class_name not in all_classes:
            report.add(
                "classes",
                "ERROR",
                str(doc_path.relative_to(PROJECT_ROOT)),
                f"Class `{class_name}` expected from docs but not found in codebase",
            )
            continue
        if class_name not in doc_refs:
            report.add(
                "classes",
                "WARNING",
                str(doc_path.relative_to(PROJECT_ROOT)),
                f"Class `{class_name}` exists in code but not referenced in doc",
            )


def _module_docs_to_scan(arch_dir: Path) -> list[Path]:
    """Return unique active documentation files that may reference modules."""
    files_to_scan: list[Path] = []
    files_to_scan.extend(sorted(arch_dir.glob("*.md")))

    readme = PROJECT_ROOT / "README.md"
    if readme.exists():
        files_to_scan.append(readme)

    for subdirectory in ("03-guides", "05-operations"):
        files_to_scan.extend(_active_markdown_files(DOCS_DIR / subdirectory))

    return list(dict.fromkeys(files_to_scan))


def _active_markdown_files(directory: Path) -> list[Path]:
    """Return Markdown files below *directory*, excluding archived docs."""
    if not directory.exists():
        return []
    return [
        path
        for path in sorted(directory.rglob("*.md"))
        if "99-archive" not in path.parts
    ]


def _module_path_resolves(module_path: str, all_modules: set[str]) -> bool:
    """Return whether a documented module path resolves to a source module."""
    return any(
        module == module_path or module.startswith(module_path + ".")
        for module in all_modules
    )


def _check_module_references(
    report: DriftReport,
    doc_path: Path,
    *,
    all_modules: set[str],
    ignored_terms: frozenset[str],
    module_pattern: re.Pattern[str],
) -> None:
    """Report unresolved module references in one documentation file."""
    text = doc_path.read_text(encoding="utf-8")
    for match in module_pattern.finditer(text):
        module_path = match.group(1)
        if module_path in ignored_terms or _module_path_resolves(
            module_path, all_modules
        ):
            continue
        report.add(
            "modules",
            "ERROR",
            str(doc_path.relative_to(PROJECT_ROOT)),
            f"Module path `{module_path}` referenced but not found in src/",
        )


def check_modules(report: DriftReport) -> None:
    """Verify module paths referenced in active documentation resolve."""
    arch_dir = DOCS_DIR / "02-architecture"
    if not arch_dir.exists():
        return

    all_modules = _collect_modules(SRC_DIR)
    ignored_terms = _collect_observability_attribute_terms()
    module_pattern = re.compile(r"`(bioetl\.[a-z_.]+)`")

    for doc_path in _module_docs_to_scan(arch_dir):
        _check_module_references(
            report,
            doc_path,
            all_modules=all_modules,
            ignored_terms=ignored_terms,
            module_pattern=module_pattern,
        )


def _bioetl_terms_from_list(raw_terms: object) -> set[str]:
    if not isinstance(raw_terms, list):
        return set()
    return {
        raw_term
        for raw_term in raw_terms
        if isinstance(raw_term, str) and raw_term.startswith("bioetl.")
    }


def _bioetl_terms_from_file_entry(file_entry: object) -> set[str]:
    if not isinstance(file_entry, dict):
        return set()
    terms: set[str] = set()
    for key in ("required_terms", "forbidden_terms"):
        terms.update(_bioetl_terms_from_list(file_entry.get(key, [])))
    return terms


def _bioetl_terms_from_surface(surface: object) -> set[str]:
    if not isinstance(surface, dict):
        return set()
    files = surface.get("files")
    if not isinstance(files, list):
        return set()
    terms: set[str] = set()
    for file_entry in files:
        terms.update(_bioetl_terms_from_file_entry(file_entry))
    return terms


def _collect_observability_attribute_terms() -> frozenset[str]:
    """Return documented tracing attributes that are intentionally not modules."""
    if not MANDATORY_TRACING_COVERAGE_PATH.exists():
        return frozenset()

    payload = yaml.safe_load(
        MANDATORY_TRACING_COVERAGE_PATH.read_text(encoding="utf-8")
    )
    if not isinstance(payload, dict):
        return frozenset()

    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, dict):
        return frozenset()

    terms: set[str] = set()
    for surface in surfaces.values():
        terms.update(_bioetl_terms_from_surface(surface))
    return frozenset(terms)


def check_providers(report: DriftReport) -> None:
    """Verify documented providers match actual adapter directories."""
    adapters_dir = SRC_DIR / "infrastructure" / "adapters"
    if not adapters_dir.exists():
        return

    non_provider_dirs = frozenset(
        {
            "common",
            "decorators",
            "http",
            "input",
            "__pycache__",
        }
    )

    actual_providers = {
        directory.name
        for directory in adapters_dir.iterdir()
        if directory.is_dir()
        and not directory.name.startswith("_")
        and directory.name not in non_provider_dirs
    }

    providers_doc = DOCS_DIR / "04-reference" / "providers"
    if not providers_doc.exists():
        return

    readme = providers_doc / README_FILENAME
    if not readme.exists():
        return

    doc_text = readme.read_text(encoding="utf-8")

    for provider in sorted(actual_providers):
        if provider not in doc_text and provider.replace("_", "-") not in doc_text:
            report.add(
                "providers",
                "WARNING",
                f"docs/04-reference/providers/{README_FILENAME}",
                f"Provider `{provider}` has adapter but not referenced in provider docs",
            )


def check_glossary(report: DriftReport) -> None:
    """Verify glossary class/module references still exist."""
    glossary_path = DOCS_DIR / "00-project" / "glossary.md"
    if not glossary_path.exists():
        return

    all_classes = _collect_classes(SRC_DIR)
    text = glossary_path.read_text(encoding="utf-8")

    class_refs: list[str] = []
    for line in text.splitlines():
        if "|" in line:
            cols = line.split("|")
            if len(cols) > 4:
                canonical_part = "|".join(cols[:-2])
            else:
                canonical_part = line
        else:
            canonical_part = line
        class_refs.extend(
            re.findall(
                r"`([A-Z][a-zA-Z]+(?:Port|Factory|Service|Writer|Reader|Adapter|Client))`",
                canonical_part,
            )
        )

    for class_name in sorted(set(class_refs)):
        if class_name not in all_classes:
            report.add(
                "glossary",
                "WARNING",
                "docs/00-project/glossary.md",
                f"Glossary references `{class_name}` which no longer exists in codebase",
            )


def check_runtime_mirrors(report: DriftReport) -> None:
    """Verify critical published runtime mirrors stay aligned with canonical docs."""
    for rule in RUNTIME_MIRROR_RULES:
        _check_runtime_mirror_rule(report, rule)


def _check_runtime_mirror_rule(report: DriftReport, rule: RuntimeMirrorRule) -> None:
    canonical_path = PROJECT_ROOT / rule.canonical
    mirror_path = PROJECT_ROOT / rule.mirror
    canonical_text = _read_doc(canonical_path)
    mirror_text = _read_doc(mirror_path)

    if not _validate_runtime_mirror_inputs(
        report,
        canonical_path=canonical_path,
        mirror_path=mirror_path,
        canonical_text=canonical_text,
        mirror_text=mirror_text,
    ):
        return

    assert canonical_text is not None
    assert mirror_text is not None
    _check_runtime_mirror_versions(
        report, rule, mirror_path, canonical_text, mirror_text
    )
    _check_runtime_mirror_sections(
        report,
        rule,
        canonical_path=canonical_path,
        mirror_path=mirror_path,
        canonical_text=canonical_text,
        mirror_text=mirror_text,
    )


def _validate_runtime_mirror_inputs(
    report: DriftReport,
    *,
    canonical_path: Path,
    mirror_path: Path,
    canonical_text: str | None,
    mirror_text: str | None,
) -> bool:
    if not canonical_text:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(canonical_path),
            "Canonical runtime doc missing",
        )
        return False
    if not mirror_text:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(mirror_path),
            "Published runtime mirror missing",
        )
        return False
    return True


def _check_runtime_mirror_versions(
    report: DriftReport,
    rule: RuntimeMirrorRule,
    mirror_path: Path,
    canonical_text: str,
    mirror_text: str,
) -> None:
    if not rule.compare_version:
        return
    canonical_version = _extract_runtime_version(canonical_text)
    mirror_version = _extract_runtime_version(mirror_text)
    if canonical_version is None or mirror_version is None:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(mirror_path),
            f"{rule.name}: could not extract version marker from canonical or mirror",
        )
        return
    if canonical_version != mirror_version:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(mirror_path),
            f"{rule.name}: version marker drifted "
            f"(canonical v{canonical_version}, mirror v{mirror_version})",
        )


def _check_runtime_mirror_sections(
    report: DriftReport,
    rule: RuntimeMirrorRule,
    *,
    canonical_path: Path,
    mirror_path: Path,
    canonical_text: str,
    mirror_text: str,
) -> None:
    for heading in rule.sections:
        _check_runtime_mirror_section(
            report,
            rule,
            heading,
            canonical_path=canonical_path,
            mirror_path=mirror_path,
            canonical_text=canonical_text,
            mirror_text=mirror_text,
        )


def _check_runtime_mirror_section(
    report: DriftReport,
    rule: RuntimeMirrorRule,
    heading: str,
    *,
    canonical_path: Path,
    mirror_path: Path,
    canonical_text: str,
    mirror_text: str,
) -> None:
    canonical_section = _extract_section(canonical_text, heading)
    mirror_section = _extract_section(mirror_text, heading)

    if canonical_section is None:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(canonical_path),
            f"{rule.name}: canonical doc missing required section {heading!r}",
        )
        return
    if mirror_section is None:
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(mirror_path),
            f"{rule.name}: mirror doc missing required section {heading!r}",
        )
        return

    if _normalize_markdown_block(canonical_section) != _normalize_markdown_block(
        mirror_section
    ):
        report.add(
            "runtime-mirrors",
            "ERROR",
            _rel(mirror_path),
            f"{rule.name}: section {heading!r} drifted from canonical runtime doc",
        )


def _check_active_non_canonical_evidence_summary(
    report: DriftReport,
    relative_path: Path,
) -> None:
    """Validate freshness metadata for an active non-canonical evidence summary."""
    path = PROJECT_ROOT / relative_path
    text = _read_doc(path)
    if not text:
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Active non-canonical evidence summary missing",
        )
        return

    metadata = _extract_front_matter_metadata(text)
    if metadata is None:
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Active non-canonical evidence summary lacks YAML front-matter metadata",
        )
        return

    missing_fields = sorted(REQUIRED_EVIDENCE_METADATA_FIELDS - metadata.keys())
    if missing_fields:
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Evidence freshness metadata missing required fields: "
            + ", ".join(missing_fields),
        )
        return

    if metadata["status"] != "active-non-canonical":
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Active evidence summary must declare status=active-non-canonical",
        )

    try:
        last_verified = date.fromisoformat(str(metadata["last_verified"]))
        raw_window = metadata["freshness_window_days"]
        if not isinstance(raw_window, (int, str)):
            raise TypeError
        freshness_window_days = int(raw_window)
    except (TypeError, ValueError):
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Evidence freshness metadata has invalid last_verified or freshness_window_days",
        )
        return

    age_days = (date.today() - last_verified).days
    if age_days > freshness_window_days:
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Active non-canonical evidence summary is stale: "
            f"{age_days}d > {freshness_window_days}d",
        )

    canonical_sources = metadata["canonical_sources"]
    if not isinstance(canonical_sources, list) or not canonical_sources:
        report.add(
            "freshness",
            "ERROR",
            _rel(path),
            "Evidence freshness metadata must list canonical_sources",
        )
        return

    for source in canonical_sources:
        source_path = PROJECT_ROOT / str(source)
        if not source_path.exists():
            report.add(
                "freshness",
                "ERROR",
                _rel(path),
                f"Evidence canonical source does not exist: {source}",
            )
        if f"`{source}`" not in text and str(source) not in text:
            report.add(
                "freshness",
                "ERROR",
                _rel(path),
                f"Evidence summary does not link canonical source: {source}",
            )


def check_freshness(report: DriftReport) -> None:
    """Verify active docs use consistent freshness/version metadata."""
    rules_text = _read_doc(PROJECT_ROOT / RULES_DOC_TOKEN)
    current_rules_version = _extract_rules_version(rules_text)

    agent_memory_text = _read_doc(PROJECT_ROOT / AGENT_MEMORY_PATH)
    if not agent_memory_text:
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
            "Agent memory doc missing",
        )
    else:
        if ".codex/agents/ORCHESTRATION.md" not in agent_memory_text:
            report.add(
                "freshness",
                "ERROR",
                _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
                "Agent memory is missing the canonical ORCHESTRATION link",
            )

        if "reports/plans/<task_id>/" in agent_memory_text:
            report.add(
                "freshness",
                "ERROR",
                _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
                "Agent memory still documents the legacy reports/plans/<task_id>/ output layout",
            )

    ai_rules_readme_text = _read_doc(PROJECT_ROOT / AI_RULES_README_PATH)
    if not ai_rules_readme_text:
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / AI_RULES_README_PATH),
            "AI rules README missing",
        )
    elif (
        current_rules_version
        and f"(v{current_rules_version})" not in ai_rules_readme_text
    ):
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / AI_RULES_README_PATH),
            "AI rules README references an outdated RULES version "
            f"(expected v{current_rules_version})",
        )

    file_policy_text = _read_doc(PROJECT_ROOT / FILE_POLICY_PATH)
    if not file_policy_text:
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / FILE_POLICY_PATH),
            "File policy doc missing",
        )
        return

    update_dates = LAST_UPDATED_PATTERN.findall(file_policy_text)
    unique_dates = sorted(set(update_dates))
    if len(unique_dates) > 1:
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / FILE_POLICY_PATH),
            "File policy contains conflicting 'Последнее обновление' markers: "
            f"{unique_dates}",
        )
    elif len(update_dates) > 1:
        report.add(
            "freshness",
            "WARNING",
            _rel(PROJECT_ROOT / FILE_POLICY_PATH),
            "File policy contains duplicate freshness markers; keep a single active marker",
        )

    for relative_path in ACTIVE_NON_CANONICAL_EVIDENCE_SUMMARIES:
        _check_active_non_canonical_evidence_summary(report, relative_path)


def check_ai_surfaces(report: DriftReport, *, root: Path | None = None) -> None:
    """Verify AI runtime control points keep required policy links and no stale refs."""
    project_root = root or PROJECT_ROOT
    run_repo_global_surface_checks = (
        root is None or project_root.resolve() == PROJECT_ROOT.resolve()
    )

    for relative_path, required_tokens in AI_SURFACE_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )

    for (
        relative_path,
        required_tokens,
    ) in AI_WRITE_CAPABLE_SKILL_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )

    for relative_path, required_tokens in AI_ROLE_PROFILE_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )

    for (
        relative_path,
        required_tokens,
    ) in AI_ROLE_MEMORY_COVERAGE_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )

    for relative_path, required_tokens in AI_MIRROR_NOTICE_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )

    for relative_path in (
        *AI_SURFACE_REQUIRED_TOKENS,
        *AI_ROLE_PROFILE_REQUIRED_TOKENS,
    ):
        _check_ai_surface_stale_refs(
            report,
            project_root=project_root,
            relative_path=relative_path,
        )

    for relative_path, forbidden_patterns in AI_SURFACE_FORBIDDEN_PATTERNS.items():
        _check_ai_surface_forbidden_patterns(
            report,
            project_root=project_root,
            relative_path=relative_path,
            forbidden_patterns=forbidden_patterns,
        )

    if run_repo_global_surface_checks:
        _check_runtime_skill_entrypoints(report, project_root=project_root)
        _check_cursor_rule_entrypoints(report, project_root=project_root)
        _check_docs_mirror_skill_entrypoints(report, project_root=project_root)
        _check_windsurf_rule_entrypoints(report, project_root=project_root)
        _check_ai_rules_mirrors(report, project_root=project_root)
        _check_unverified_gemini_runtime_claims(report, project_root=project_root)
        _check_stale_rules_version_literals(report, project_root=project_root)
    _check_ai_docs_runtime_mirror_headers(report, project_root=project_root)


def _check_stale_rules_version_literals(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    """Flag hardcoded RULES.md version literals that drift from the canonical header."""
    rules_text = _read_doc(project_root / RULES_DOC_TOKEN)
    current_rules_version = _extract_rules_version(rules_text)
    if not current_rules_version:
        return

    for relative_path in AI_SURFACES_WITH_RULES_VERSION_LITERAL_GUARD:
        path = project_root / relative_path
        text = _read_doc(path)
        if not text:
            continue
        for match in RULES_VERSION_LITERAL_PATTERN.finditer(text):
            found_version = match.group(1)
            if found_version != current_rules_version:
                report.add(
                    "ai-surfaces",
                    "ERROR",
                    _display_relative_path(relative_path),
                    "Stale RULES.md version literal "
                    f"(expected v{current_rules_version}, found v{found_version})",
                )


def _check_ai_surface_required_tokens(
    report: DriftReport,
    *,
    project_root: Path,
    relative_path: Path,
    required_tokens: tuple[str, ...],
) -> None:
    path = project_root / relative_path
    text = _read_doc(path)
    if not text:
        report.add(
            "ai-surfaces",
            "ERROR",
            _display_relative_path(relative_path),
            AI_SURFACE_FILE_MISSING_MESSAGE,
        )
        return

    for token in required_tokens:
        if token not in text:
            report.add(
                "ai-surfaces",
                "ERROR",
                _display_relative_path(relative_path),
                f"Missing required AI policy/runtime token: {token}",
            )


def _check_ai_surface_stale_refs(
    report: DriftReport,
    *,
    project_root: Path,
    relative_path: Path,
) -> None:
    path = project_root / relative_path
    text = _read_doc(path)
    if not text:
        return

    for pattern in AI_SURFACE_STALE_PATTERNS:
        match = pattern.search(text)
        if match is not None:
            report.add(
                "ai-surfaces",
                "ERROR",
                _display_relative_path(relative_path),
                f"Stale AI runtime path detected: {match.group(0)}",
            )


def _check_ai_surface_forbidden_patterns(
    report: DriftReport,
    *,
    project_root: Path,
    relative_path: Path,
    forbidden_patterns: tuple[re.Pattern[str], ...],
) -> None:
    path = project_root / relative_path
    text = _read_doc(path)
    if not text:
        report.add(
            "ai-surfaces",
            "ERROR",
            _display_relative_path(relative_path),
            AI_SURFACE_FILE_MISSING_MESSAGE,
        )
        return

    for pattern in forbidden_patterns:
        match = pattern.search(text)
        if match is not None:
            report.add(
                "ai-surfaces",
                "ERROR",
                _display_relative_path(relative_path),
                f"Forbidden legacy runtime dependency detected: {match.group(0)}",
            )


def _agent_docs_mirror_targets(project_root: Path) -> list[AIDocsMirrorTarget]:
    agents_root = project_root / "docs" / "00-project" / "ai" / "agents" / "agents"
    targets: list[AIDocsMirrorTarget] = []
    for path in sorted(agents_root.glob("*.md")):
        if path.name == README_FILENAME:
            continue
        canonical_sources = tuple(
            candidate
            for candidate in (
                Path(".codex/agents") / path.name,
                Path(".gemini/agents") / path.name,
            )
            if (project_root / candidate).exists()
        )
        if not canonical_sources:
            continue
        targets.append(
            AIDocsMirrorTarget(
                relative_path=path.relative_to(project_root),
                canonical_sources=canonical_sources,
            )
        )
    return targets


def _skill_docs_mirror_targets(
    project_root: Path,
    *,
    docs_subdir: str,
    canonical_root: str,
    skip_system_parts: bool = False,
) -> list[AIDocsMirrorTarget]:
    skills_root = project_root / "docs" / "00-project" / "ai" / "skills" / docs_subdir
    targets: list[AIDocsMirrorTarget] = []
    for path in sorted(skills_root.rglob(SKILL_FILE_NAME)):
        if skip_system_parts and ".system" in path.parts:
            continue
        relative_skill_path = path.parent.relative_to(skills_root)
        canonical = Path(canonical_root) / relative_skill_path / SKILL_FILE_NAME
        if not (project_root / canonical).exists():
            continue
        targets.append(
            AIDocsMirrorTarget(
                relative_path=path.relative_to(project_root),
                canonical_sources=(canonical,),
            )
        )
    return targets


def _iter_ai_docs_runtime_mirror_targets(
    project_root: Path,
) -> tuple[AIDocsMirrorTarget, ...]:
    return (
        *_agent_docs_mirror_targets(project_root),
        *_skill_docs_mirror_targets(
            project_root,
            docs_subdir="local",
            canonical_root=".codex/skills",
        ),
        *_skill_docs_mirror_targets(
            project_root,
            docs_subdir="global",
            canonical_root=".gemini/skills",
            skip_system_parts=True,
        ),
    )


def _check_ai_docs_runtime_mirror_headers(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    for target in _iter_ai_docs_runtime_mirror_targets(project_root):
        path = project_root / target.relative_path
        text = _read_doc(path)
        if not text:
            report.add(
                "ai-surfaces",
                "ERROR",
                _display_relative_path(target.relative_path),
                AI_SURFACE_FILE_MISSING_MESSAGE,
            )
            continue

        target_report_path = _display_relative_path(target.relative_path)
        header_text = "\n".join(
            text.splitlines()[:AI_DOCS_RUNTIME_MIRROR_HEADER_LINE_LIMIT]
        )
        for token in AI_DOCS_RUNTIME_MIRROR_REQUIRED_TOKENS:
            if token not in header_text:
                report.add(
                    "ai-surfaces",
                    "ERROR",
                    target_report_path,
                    f"AI docs mirror header missing required token in first section: {token}",
                )
        for source in target.canonical_sources:
            source_text = _display_relative_path(source)
            if source_text not in header_text:
                report.add(
                    "ai-surfaces",
                    "ERROR",
                    target_report_path,
                    "AI docs mirror header missing canonical runtime source: "
                    f"{source_text}",
                )


def _iter_runtime_skill_entrypoints(project_root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for runtime_root in (Path(".codex/skills"), Path(".devin/skills")):
        root = project_root / runtime_root
        if not root.exists():
            continue
        for path in sorted(root.rglob(SKILL_FILE_NAME)):
            paths.append(path.relative_to(project_root))
    return tuple(paths)


def _required_runtime_skill_tokens(
    project_root: Path, relative_path: Path
) -> tuple[str, ...]:
    skill_file = relative_path
    skill_dir = skill_file.parent
    return (
        _relative_token(skill_dir, project_root / AGENTS_DOC_TOKEN),
        _relative_token(skill_dir, project_root / RULES_DOC_TOKEN),
        _relative_token(skill_dir, project_root / REQUIREMENTS_DOC_TOKEN),
        _relative_token(skill_dir, project_root / ADR_DIR_DOC_TOKEN),
    )


def _required_docs_mirror_skill_tokens(
    project_root: Path, relative_path: Path
) -> tuple[str, ...]:
    skill_file = relative_path
    skill_dir = skill_file.parent
    return (
        _relative_token(skill_dir, project_root / NORMATIVE_SOURCES_DOC_TOKEN),
        _relative_token(skill_dir, project_root / AGENTS_DOC_TOKEN),
        _relative_token(skill_dir, project_root / RULES_DOC_TOKEN),
        _relative_token(skill_dir, project_root / REQUIREMENTS_DOC_TOKEN),
        _relative_token(skill_dir, project_root / ADR_DIR_DOC_TOKEN),
    )


def _check_runtime_skill_entrypoints(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    for relative_path in _iter_runtime_skill_entrypoints(project_root):
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=_required_runtime_skill_tokens(project_root, relative_path),
        )


def _iter_cursor_rule_entrypoints(project_root: Path) -> tuple[Path, ...]:
    paths: list[Path] = []
    for rules_root in (CURSOR_RULES_DIR, CURSOR_RULE_DOCS_DIR):
        root = project_root / rules_root
        if not root.exists():
            continue
        for path in sorted(root.glob("*.mdc")):
            if path.name in CURSOR_RULE_EXCLUDED_FILENAMES:
                continue
            paths.append(path.relative_to(project_root))
    return tuple(paths)


def _check_cursor_rule_entrypoints(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    required_tokens = (
        AGENTS_DOC_TOKEN,
        NORMATIVE_SOURCES_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    )
    for relative_path in _iter_cursor_rule_entrypoints(project_root):
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )


def _iter_windsurf_rule_entrypoints(project_root: Path) -> tuple[Path, ...]:
    root = project_root / WINDSURF_RULE_DOCS_DIR
    if not root.exists():
        return ()
    return tuple(path.relative_to(project_root) for path in sorted(root.glob("*.md")))


def _iter_windsurf_workflow_entrypoints(project_root: Path) -> tuple[Path, ...]:
    root = project_root / WINDSURF_WORKFLOW_DOCS_DIR
    if not root.exists():
        return ()
    return tuple(path.relative_to(project_root) for path in sorted(root.glob("*.md")))


def _iter_docs_mirror_skill_entrypoints(project_root: Path) -> tuple[Path, ...]:
    root = project_root / DOCS_MIRROR_SKILLS_DIR
    if not root.exists():
        return ()
    return tuple(
        path.relative_to(project_root) for path in sorted(root.glob("*/SKILL.md"))
    )


def _check_docs_mirror_skill_entrypoints(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    for relative_path in _iter_docs_mirror_skill_entrypoints(project_root):
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=_required_docs_mirror_skill_tokens(
                project_root,
                relative_path,
            ),
        )


def _check_windsurf_rule_entrypoints(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    required_tokens = (
        AGENTS_DOC_TOKEN,
        RULES_DOC_TOKEN,
        REQUIREMENTS_DOC_TOKEN,
        ADR_DIR_DOC_TOKEN,
    )
    for relative_path in (
        *_iter_windsurf_rule_entrypoints(project_root),
        *_iter_windsurf_workflow_entrypoints(project_root),
    ):
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )


def _check_ai_rules_mirrors(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    for relative_path, required_tokens in AI_RULES_MIRROR_REQUIRED_TOKENS.items():
        _check_ai_surface_required_tokens(
            report,
            project_root=project_root,
            relative_path=relative_path,
            required_tokens=required_tokens,
        )


def _check_unverified_gemini_runtime_claims(
    report: DriftReport,
    *,
    project_root: Path,
) -> None:
    for relative_path in AI_GEMINI_RUNTIME_CLAIM_GUARD_PATHS:
        path = project_root / relative_path
        text = _read_doc(path)
        if not text:
            if relative_path in AI_OPTIONAL_LOCAL_RUNTIME_CLAIM_GUARD_PATHS:
                continue
            report.add(
                "ai-surfaces",
                "ERROR",
                _display_relative_path(relative_path),
                AI_SURFACE_FILE_MISSING_MESSAGE,
            )
            continue
        for pattern in AI_GEMINI_RUNTIME_CLAIM_FORBIDDEN_PATTERNS:
            match = pattern.search(text)
            if match is not None:
                report.add(
                    "ai-surfaces",
                    "ERROR",
                    _display_relative_path(relative_path),
                    f"Unverified Gemini runtime-tree claim detected: {match.group(0)}",
                )


def print_report(report: DriftReport) -> None:
    """Print human-readable drift report."""
    by_category = _issues_by_category(report)

    print("Documentation Drift Report")
    print("=" * 60)

    if report.issues:
        for category in sorted(by_category):
            issues = by_category[category]
            print(f"\n[{category.upper()}] ({len(issues)} issues)")
            for issue in issues:
                marker = "ERROR" if issue.severity == "ERROR" else "WARN "
                print(f"  {marker}  {issue.doc_file}")
                print(f"         {issue.detail}")
    else:
        print("No drift detected. Documentation is in sync with code.")

    print()
    print(f"Summary: {report.error_count} errors, {report.warning_count} warnings")


def _issues_by_category(report: DriftReport) -> dict[str, list[DriftIssue]]:
    by_category: dict[str, list[DriftIssue]] = {}
    for issue in report.issues:
        by_category.setdefault(issue.category, []).append(issue)
    return by_category


def _run_checks(
    report: DriftReport, *, args: argparse.Namespace, run_all: bool
) -> None:
    selected_checks = [
        (run_all or args.ports, check_ports),
        (run_all or args.classes, check_classes),
        (run_all or args.modules, check_modules),
        (run_all or args.runtime_mirrors, check_runtime_mirrors),
        (run_all or args.freshness, check_freshness),
        (run_all or args.ai_surfaces, check_ai_surfaces),
    ]

    for enabled, checker in selected_checks:
        if enabled:
            checker(report)
    if run_all:
        check_providers(report)
        check_glossary(report)


def main(argv: list[str] | None = None) -> int:
    """Run documentation drift detection."""
    parser = argparse.ArgumentParser(
        description="Detect documentation drift in BioETL",
    )
    parser.add_argument("--ports", action="store_true", help="Check port drift only")
    parser.add_argument("--classes", action="store_true", help="Check class drift only")
    parser.add_argument(
        "--modules", action="store_true", help="Check module path drift only"
    )
    parser.add_argument(
        "--runtime-mirrors",
        action="store_true",
        help="Check published runtime docs mirrors against canonical .codex docs",
    )
    parser.add_argument(
        "--freshness",
        action="store_true",
        help="Check freshness/version markers in active runtime/governance docs",
    )
    parser.add_argument(
        "--ai-surfaces",
        action="store_true",
        help="Check AI runtime control points for policy links and legacy refs",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output machine-readable JSON",
    )
    args = parser.parse_args(argv)

    report = DriftReport()

    run_all = not (
        args.ports
        or args.classes
        or args.modules
        or args.runtime_mirrors
        or args.freshness
        or args.ai_surfaces
    )

    _run_checks(report, args=args, run_all=run_all)

    if args.json_output:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        print()
    else:
        print_report(report)

    return 1 if report.error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
