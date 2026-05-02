#!/usr/bin/env python3
"""check_doc_drift.py - Detect documentation drift between code and docs.

Verifies that key entities referenced in architecture documentation still
exist in the codebase.  Catches common drift scenarios:

  1. Port protocols renamed/removed but docs still reference old names
  2. Class names changed but architecture docs not updated
  3. Module paths moved but docs still point to old locations
  4. Provider/entity lists changed but reference docs are stale
  5. Factory/registry changes not reflected in composition docs
  6. Active runtime docs mirrors drift from canonical `.gemini/agents/` sources
  7. Freshness/version markers in active docs disagree with canonical runtime docs

Usage:
    python scripts/check_doc_drift.py              # Full drift check
    python scripts/check_doc_drift.py --ports       # Only port drift
    python scripts/check_doc_drift.py --classes     # Only class drift
    python scripts/check_doc_drift.py --modules     # Only module path drift
    python scripts/check_doc_drift.py --runtime-mirrors
    python scripts/check_doc_drift.py --freshness
    python scripts/check_doc_drift.py --json        # Machine-readable JSON output

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
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _bootstrap import DOCS_DIR, PROJECT_ROOT
else:
    from scripts.docs.checks._bootstrap import DOCS_DIR, PROJECT_ROOT

SRC_DIR = PROJECT_ROOT / "src" / "bioetl"


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


RUNTIME_VERSION_PATTERN = re.compile(r"(?m)^\*Версия:\s*(\d+(?:\.\d+)*)")
AGENT_MEMORY_SYNC_PATTERN = re.compile(
    r"Синхронизировано с ORCHESTRATION\.md v(\d+(?:\.\d+)*)"
)
LAST_UPDATED_PATTERN = re.compile(r"Последнее обновление:\s*(\d{4}-\d{2}-\d{2})")

RUNTIME_MIRROR_RULES: tuple[RuntimeMirrorRule, ...] = (
    RuntimeMirrorRule(
        name="orchestration",
        canonical=Path(".codex/agents/ORCHESTRATION.md"),
        mirror=Path("docs/00-project/ai/agents/agents/ORCHESTRATION.md"),
        sections=(
            "## 1. Обзор",
            "## 2. Стандартный workflow задачи",
            "## 4. Структура артефактов",
        ),
        compare_version=True,
    ),
    RuntimeMirrorRule(
        name="py-audit-bot",
        canonical=Path(".gemini/agents/py-audit-bot.md"),
        mirror=Path("docs/00-project/ai/agents/agents/py-audit-bot.md"),
        sections=("## Выходы",),
    ),
    RuntimeMirrorRule(
        name="py-config-bot",
        canonical=Path(".gemini/agents/py-config-bot.md"),
        mirror=Path("docs/00-project/ai/agents/agents/py-config-bot.md"),
        sections=("## Выходы", "## Обязательные правила", "## Иерархия конфигураций"),
    ),
)

AGENT_MEMORY_PATH = Path("docs/00-project/ai/memory/agent-memory.md")
FILE_POLICY_PATH = Path("docs/00-project/governance/03-file-policy.md")
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
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
        ".codex/agents/CODEX-RUNTIME.md",
        ".gemini/agents/GEMINI-RUNTIME.md",
    ),
    Path("GEMINI.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
        "docs/00-project/ai/memory/agent-memory.md",
    ),
    Path(".github/copilot-instructions.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/CODEX-RUNTIME.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/GEMINI-RUNTIME.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/README.md"): (
        "AGENTS.md",
        ".codex/agents/CODEX-RUNTIME.md",
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/README.md"): (
        "AGENTS.md",
        ".gemini/agents/GEMINI-RUNTIME.md",
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path("docs/00-project/ai/agents/guides/CODEX.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
    ),
    Path("docs/00-project/ai/agents/guides/AGENT.md"): (
        "MEMORY_USAGE.md",
        "../policy/POST_CHANGE_VALIDATION.md",
        "../memory/agent-memory.md",
    ),
}
AI_WRITE_CAPABLE_SKILL_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path(".codex/skills/create-pr/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/repo-config/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/grafana-dashboard-extension/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/prometheus-alert-rule-editor/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/prometheus-metric-discovery/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/prometheus-query-debugger/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/prometheus-rule-testing/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/technical-designer-mermaid/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/skills/vcr-record/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/create-pr/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/repo-config/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/grafana-dashboard-extension/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/prometheus-alert-rule-editor/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/prometheus-metric-discovery/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/prometheus-query-debugger/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/prometheus-rule-testing/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/technical-designer-mermaid/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/vcr-record/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/skills/documentation-audit/SKILL.md"): (
        "AGENTS.md",
        "MEMORY_USAGE.md",
        "POST_CHANGE_VALIDATION.md",
    ),
}
AI_ROLE_PROFILE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path(".codex/agents/py-audit-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-audit-bot.md",
    ),
    Path(".codex/agents/py-plan-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-plan-bot.md",
    ),
    Path(".codex/agents/py-config-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-config-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-debug-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-debug-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-doc-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-doc-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-test-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-test-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-architecture-debt-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-architecture-debt-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-review-orchestrator.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-review-orchestrator.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".codex/agents/py-test-swarm.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-test-swarm.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-audit-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-audit-bot.md",
    ),
    Path(".gemini/agents/py-plan-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-plan-bot.md",
    ),
    Path(".gemini/agents/py-config-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-config-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-debug-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-debug-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-doc-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-doc-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-test-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-test-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-architecture-debt-bot.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-architecture-debt-bot.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-review-orchestrator.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-review-orchestrator.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
    Path(".gemini/agents/py-test-swarm.md"): (
        "docs/00-project/ai/agents/guides/MEMORY_USAGE.md",
        "docs/00-project/ai/memory/agent-memory.md",
        "docs/00-project/ai/memory/memory-py-test-swarm.md",
        "docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md",
    ),
}
AI_ROLE_MEMORY_COVERAGE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path("docs/00-project/ai/memory/README.md"): (
        "memory-py-architecture-debt-bot.md",
        "memory-py-review-orchestrator.md",
        "memory-py-test-swarm.md",
    ),
    Path("docs/00-project/ai/memory/agent-memory.md"): (
        "memory-py-architecture-debt-bot.md",
        "memory-py-review-orchestrator.md",
        "memory-py-test-swarm.md",
    ),
}
AI_MIRROR_NOTICE_REQUIRED_TOKENS: dict[Path, tuple[str, ...]] = {
    Path("docs/00-project/ai/skills/README.md"): (
        "Non-Canonical Mirror Notice",
        "docs/00-project/ai/skills/**",
        ".codex/skills/**",
        ".gemini/skills/**",
    ),
    Path("docs/00-project/ai/agents/agents/README.md"): (
        "Non-Canonical Mirror Notice",
        "docs/00-project/ai/agents/agents/**",
        ".codex/agents/**",
        ".gemini/agents/**",
    ),
}
AI_DOCS_RUNTIME_MIRROR_HEADER_LINE_LIMIT = 40
AI_DOCS_RUNTIME_MIRROR_REQUIRED_TOKENS = (
    "Mirror status:",
    "not a canonical runtime surface",
    "AI_RUNTIME_MIRROR_OWNERSHIP.md",
)
AI_SURFACE_STALE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"docs/00-project/ai/agents/runtime/agent-memory\.md"),
    re.compile(r"(?<!\.)runtime/agent-memory\.md"),
)
AI_SURFACE_FORBIDDEN_PATTERNS: dict[Path, tuple[re.Pattern[str], ...]] = {
    Path(".codex/agents/CODEX-RUNTIME.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/agents/GEMINI-RUNTIME.md"): (re.compile(r"\.claude/"),),
    Path(".codex/agents/py-audit-bot.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/agents/py-audit-bot.md"): (re.compile(r"\.claude/"),),
    Path(".codex/agents/py-review-orchestrator.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/agents/py-review-orchestrator.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/new-pipeline/SKILL.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/verify-architecture/SKILL.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/vcr-record/SKILL.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/py-review-orchestrator/SKILL.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/py-test-swarm/SKILL.md"): (re.compile(r"\.claude/"),),
    Path(".gemini/skills/documentation-cascade-audit/SKILL.md"): (
        re.compile(r"\.claude/"),
    ),
    Path(".gemini/skills/py-architecture-debt-bot/SKILL.md"): (
        re.compile(r"\.claude/"),
    ),
    Path(".gemini/skills/capability-discovery/SKILL.md"): (re.compile(r"\.claude/"),),
}


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
                "LockCoordinator",
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


def check_modules(report: DriftReport) -> None:
    """Verify module paths referenced in architecture docs resolve."""
    all_modules = _collect_modules(SRC_DIR)

    arch_dir = DOCS_DIR / "02-architecture"
    if not arch_dir.exists():
        return

    module_pattern = re.compile(r"`(bioetl\.[a-z_.]+)`")

    for md_file in sorted(arch_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        for match in module_pattern.finditer(text):
            mod_path = match.group(1)
            if not any(
                module == mod_path or module.startswith(mod_path + ".")
                for module in all_modules
            ):
                report.add(
                    "modules",
                    "ERROR",
                    str(md_file.relative_to(PROJECT_ROOT)),
                    f"Module path `{mod_path}` referenced but not found in src/",
                )


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

    readme = providers_doc / "README.md"
    if not readme.exists():
        return

    doc_text = readme.read_text(encoding="utf-8")

    for provider in sorted(actual_providers):
        if provider not in doc_text and provider.replace("_", "-") not in doc_text:
            report.add(
                "providers",
                "WARNING",
                "docs/04-reference/providers/README.md",
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
        freshness_window_days = int(metadata["freshness_window_days"])
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
    canonical_orchestration = PROJECT_ROOT / ".codex" / "agents" / "ORCHESTRATION.md"
    orchestration_text = _read_doc(canonical_orchestration)
    current_orchestration_version = _extract_runtime_version(orchestration_text)

    agent_memory_text = _read_doc(PROJECT_ROOT / AGENT_MEMORY_PATH)
    if not agent_memory_text:
        report.add(
            "freshness",
            "ERROR",
            _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
            "Agent memory doc missing",
        )
    else:
        sync_match = AGENT_MEMORY_SYNC_PATTERN.search(agent_memory_text)
        if sync_match is None:
            report.add(
                "freshness",
                "ERROR",
                _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
                "Agent memory is missing the ORCHESTRATION sync marker",
            )
        elif (
            current_orchestration_version
            and sync_match.group(1) != current_orchestration_version
        ):
            report.add(
                "freshness",
                "ERROR",
                _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
                "Agent memory references an outdated ORCHESTRATION version "
                f"(expected v{current_orchestration_version}, found v{sync_match.group(1)})",
            )

        if "reports/plans/<task_id>/" in agent_memory_text:
            report.add(
                "freshness",
                "ERROR",
                _rel(PROJECT_ROOT / AGENT_MEMORY_PATH),
                "Agent memory still documents the legacy reports/plans/<task_id>/ output layout",
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

    _check_ai_docs_runtime_mirror_headers(report, project_root=project_root)


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
            "AI surface file missing",
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
            "AI surface file missing",
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


def _iter_ai_docs_runtime_mirror_targets(
    project_root: Path,
) -> tuple[AIDocsMirrorTarget, ...]:
    targets: list[AIDocsMirrorTarget] = []

    agents_root = project_root / "docs" / "00-project" / "ai" / "agents" / "agents"
    for path in sorted(agents_root.glob("*.md")):
        if path.name == "README.md":
            continue
        canonical_sources = tuple(
            candidate
            for candidate in (
                Path(".codex/agents") / path.name,
                Path(".gemini/agents") / path.name,
            )
            if (project_root / candidate).exists()
        )
        if canonical_sources:
            targets.append(
                AIDocsMirrorTarget(
                    relative_path=path.relative_to(project_root),
                    canonical_sources=canonical_sources,
                )
            )

    local_skills_root = project_root / "docs" / "00-project" / "ai" / "skills" / "local"
    for path in sorted(local_skills_root.rglob("SKILL.md")):
        relative_skill_path = path.parent.relative_to(local_skills_root)
        canonical = Path(".codex/skills") / relative_skill_path / "SKILL.md"
        if (project_root / canonical).exists():
            targets.append(
                AIDocsMirrorTarget(
                    relative_path=path.relative_to(project_root),
                    canonical_sources=(canonical,),
                )
            )

    global_skills_root = (
        project_root / "docs" / "00-project" / "ai" / "skills" / "global"
    )
    for path in sorted(global_skills_root.rglob("SKILL.md")):
        if ".system" in path.parts:
            continue
        relative_skill_path = path.parent.relative_to(global_skills_root)
        canonical = Path(".gemini/skills") / relative_skill_path / "SKILL.md"
        if (project_root / canonical).exists():
            targets.append(
                AIDocsMirrorTarget(
                    relative_path=path.relative_to(project_root),
                    canonical_sources=(canonical,),
                )
            )

    return tuple(targets)


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
                "AI surface file missing",
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


def print_report(report: DriftReport) -> None:
    """Print human-readable drift report."""
    print("Documentation Drift Report")
    print("=" * 60)

    if not report.issues:
        print("No drift detected. Documentation is in sync with code.")
        return

    by_category: dict[str, list[DriftIssue]] = {}
    for issue in report.issues:
        by_category.setdefault(issue.category, []).append(issue)

    for category in sorted(by_category):
        issues = by_category[category]
        print(f"\n[{category.upper()}] ({len(issues)} issues)")
        for issue in issues:
            marker = "ERROR" if issue.severity == "ERROR" else "WARN "
            print(f"  {marker}  {issue.doc_file}")
            print(f"         {issue.detail}")

    print()
    print(f"Summary: {report.error_count} errors, {report.warning_count} warnings")


def main() -> int:
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
    args = parser.parse_args()

    report = DriftReport()

    run_all = not (
        args.ports
        or args.classes
        or args.modules
        or args.runtime_mirrors
        or args.freshness
        or args.ai_surfaces
    )

    if run_all or args.ports:
        check_ports(report)
    if run_all or args.classes:
        check_classes(report)
    if run_all or args.modules:
        check_modules(report)
    if run_all or args.runtime_mirrors:
        check_runtime_mirrors(report)
    if run_all or args.freshness:
        check_freshness(report)
    if run_all or args.ai_surfaces:
        check_ai_surfaces(report)
    if run_all:
        check_providers(report)
        check_glossary(report)

    if args.json_output:
        json.dump(report.to_dict(), sys.stdout, indent=2)
        print()
    else:
        print_report(report)

    return 1 if report.error_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
