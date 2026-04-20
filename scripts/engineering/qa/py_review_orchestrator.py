from __future__ import annotations

import argparse
import ast
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Constants
FILE_THRESHOLD = 40
LOC_THRESHOLD = 3000
SCORE_DEDUCTIONS = {"CRITICAL": -2.0, "HIGH": -1.0, "MEDIUM": -0.5, "LOW": -0.25}
SECTOR_WEIGHTS = {
    "S1": 0.20,
    "S2": 0.20,
    "S3": 0.20,
    "S4": 0.10,
    "S5": 0.10,
    "S6": 0.08,
    "S7": 0.05,
    "S8": 0.07,
}
SCORE_WEIGHTS = {
    "Architecture": 0.30,
    "Anti-Patterns": 0.25,
    "DI Violations": 0.20,
    "Naming": 0.10,
    "Types": 0.10,
    "Testing": 0.05,
    "Configs": 0.05,
    "Documentation": 0.05,
}
DOMAIN_ROOT = "src/bioetl/domain"
COMPOSITION_ROOT = "src/bioetl/composition"
INTERFACES_ROOT = "src/bioetl/interfaces"
IGNORED_REVIEW_DIRS = {
    ".venv",
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "__pycache__",
    ".claude",
    ".codex",
    "playwright",
    "reports",
    "grafana",
}
STATIC_SUBSECTOR_DEFS: dict[str, list[dict[str, Any]]] = {
    "S2": [
        {
            "id": "S2.1",
            "name": "Pipelines(ChEMBL+Common)",
            "paths": [
                "src/bioetl/application/pipelines/chembl",
                "src/bioetl/application/pipelines/common",
            ],
        },
        {
            "id": "S2.2",
            "name": "Pipelines(PubMed+CrossRef+OpenAlex)",
            "paths": [
                "src/bioetl/application/pipelines/pubmed",
                "src/bioetl/application/pipelines/crossref",
                "src/bioetl/application/pipelines/openalex",
            ],
        },
        {
            "id": "S2.3",
            "name": "Pipelines(PubChem+SemanticScholar+UniProt)",
            "paths": [
                "src/bioetl/application/pipelines/pubchem",
                "src/bioetl/application/pipelines/semanticscholar",
                "src/bioetl/application/pipelines/uniprot",
            ],
        },
        {
            "id": "S2.4",
            "name": "Core",
            "paths": ["src/bioetl/application/core"],
        },
        {
            "id": "S2.5",
            "name": "Composite+Services+Obs",
            "paths": [
                "src/bioetl/application/composite",
                "src/bioetl/application/services",
                "src/bioetl/application/observability",
            ],
        },
    ],
    "S3": [
        {
            "id": "S3.1",
            "name": "Adapters 1",
            "paths": [
                "src/bioetl/infrastructure/adapters/chembl",
                "src/bioetl/infrastructure/adapters/pubmed",
                "src/bioetl/infrastructure/adapters/crossref",
            ],
        },
        {
            "id": "S3.2",
            "name": "Adapters 2",
            "paths": [
                "src/bioetl/infrastructure/adapters/pubchem",
                "src/bioetl/infrastructure/adapters/openalex",
                "src/bioetl/infrastructure/adapters/semanticscholar",
                "src/bioetl/infrastructure/adapters/uniprot",
            ],
        },
        {
            "id": "S3.3",
            "name": "Adapters Base",
            "paths": [
                "src/bioetl/infrastructure/adapters/base",
                "src/bioetl/infrastructure/adapters/http",
                "src/bioetl/infrastructure/adapters/common",
                "src/bioetl/infrastructure/adapters/decorators",
                "src/bioetl/infrastructure/adapters/input",
            ],
        },
        {
            "id": "S3.4",
            "name": "Storage+Config+Schemas",
            "paths": [
                "src/bioetl/infrastructure/storage",
                "src/bioetl/infrastructure/config",
                "src/bioetl/infrastructure/schemas",
            ],
        },
        {
            "id": "S3.5",
            "name": "Observability+Other",
            "paths": ["src/bioetl/infrastructure/observability"],
        },
    ],
    "S4": [
        {
            "id": "S4.1",
            "name": "Composition",
            "paths": [COMPOSITION_ROOT],
        },
        {
            "id": "S4.2",
            "name": "Interfaces",
            "paths": [INTERFACES_ROOT],
        },
    ],
    "S5": [
        {"id": "S5.1", "name": "Cross Domain", "paths": [DOMAIN_ROOT]},
        {
            "id": "S5.2",
            "name": "Cross Application",
            "paths": ["src/bioetl/application"],
        },
        {
            "id": "S5.3",
            "name": "Cross Infrastructure",
            "paths": ["src/bioetl/infrastructure"],
        },
        {
            "id": "S5.4",
            "name": "Cross Other",
            "paths": [COMPOSITION_ROOT, INTERFACES_ROOT],
        },
    ],
    "S6": [
        {"id": "S6.1", "name": "Architecture", "paths": ["tests/architecture"]},
        {"id": "S6.2", "name": "Unit Domain", "paths": ["tests/unit/domain"]},
        {
            "id": "S6.3",
            "name": "Unit Application",
            "paths": ["tests/unit/application"],
        },
        {
            "id": "S6.4",
            "name": "Unit Infrastructure",
            "paths": ["tests/unit/infrastructure"],
        },
        {
            "id": "S6.5",
            "name": "Unit Comp+Ifaces",
            "paths": [
                "tests/unit/composition",
                "tests/unit/interfaces",
                "tests/unit/cli",
                "tests/unit/contracts",
                "tests/unit/pipelines",
            ],
        },
        {
            "id": "S6.6",
            "name": "Integration+Other",
            "paths": [
                "tests/integration",
                "tests/e2e",
                "tests/contract",
                "tests/security",
                "tests/smoke",
                "tests/performance",
                "tests/benchmarks",
            ],
        },
    ],
}
DOMAIN_COVERED_PATH_GROUPS = (
    ("src/bioetl/domain/ports", "src/bioetl/domain/contracts"),
    ("src/bioetl/domain/entities", "src/bioetl/domain/value_objects"),
    ("src/bioetl/domain/schemas",),
    (
        "src/bioetl/domain/services",
        "src/bioetl/domain/filtering",
        "src/bioetl/domain/mapping",
    ),
    (
        "src/bioetl/domain/config",
        "src/bioetl/domain/composite",
        "src/bioetl/domain/aggregates",
        "src/bioetl/domain/registry",
        "src/bioetl/domain/models",
        "src/bioetl/domain/exceptions",
    ),
)
DOMAIN_SUBSECTOR_DEFS = (
    ("S1.1", "Ports+Contracts", ("src/bioetl/domain/ports", "src/bioetl/domain/contracts")),
    ("S1.2", "Entities+VOs", ("src/bioetl/domain/entities", "src/bioetl/domain/value_objects")),
    ("S1.3", "Schemas", ("src/bioetl/domain/schemas",)),
    (
        "S1.4",
        "Services+Filters+Map",
        (
            "src/bioetl/domain/services",
            "src/bioetl/domain/filtering",
            "src/bioetl/domain/mapping",
        ),
    ),
)
DOMAIN_OTHER_PATHS = (
    "src/bioetl/domain/config",
    "src/bioetl/domain/composite",
    "src/bioetl/domain/aggregates",
    "src/bioetl/domain/registry",
    "src/bioetl/domain/models",
    "src/bioetl/domain/exceptions",
)
CONFIG_COVERED_PATH_GROUPS = (
    ("configs/entities",),
    ("configs/composites", "configs/contracts", "configs/providers"),
    ("configs/base", "configs/quality", "configs/_schema", "configs/enums"),
)
CONFIG_SUBSECTOR_DEFS = (
    ("S7.1", "Entities", ("configs/entities",)),
    ("S7.2", "Composites+Contracts+Providers", ("configs/composites", "configs/contracts", "configs/providers")),
)
CONFIG_OTHER_PATHS = (
    "configs/base",
    "configs/quality",
    "configs/_schema",
    "configs/enums",
)
DOC_COVERED_PATH_GROUPS = (
    ("docs/00-project", "docs/01-requirements"),
    ("docs/02-architecture",),
    ("docs/04-reference",),
    ("docs/03-guides", "docs/05-operations"),
)
DOC_SUBSECTOR_DEFS = (
    ("S8.1", "Project+Reqs", ("docs/00-project", "docs/01-requirements")),
    ("S8.2", "Architecture", ("docs/02-architecture",)),
    ("S8.3", "Reference", ("docs/04-reference",)),
)
DOC_OTHER_PATHS = ("docs/03-guides", "docs/05-operations")
ALLOWED_CONSTRUCTORS = {
    "Path",
    "dict",
    "list",
    "set",
    "tuple",
    "frozenset",
    "str",
    "int",
    "float",
    "bool",
    "bytes",
    "bytearray",
    "complex",
    "range",
    "memoryview",
    "type",
    "object",
    "Exception",
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
    "AttributeError",
    "RuntimeError",
    "NotImplementedError",
    "NameError",
    "SyntaxError",
    "SystemError",
    "EnvironmentError",
    "IOError",
    "OSError",
    "ConnectionError",
    "TimeoutError",
    "PermissionError",
    "IsADirectoryError",
    "NotADirectoryError",
    "FileExistsError",
    "FileNotFoundError",
    "ProcessLookupError",
    "InterruptedError",
    "ChildProcessError",
    "MagicMock",
    "Mock",
    "PropertyMock",
    "AsyncMock",
    "NonCallableMock",
    "ANY",
    "SimpleNamespace",
    "Counter",
    "deque",
    "defaultdict",
    "namedtuple",
    "OrderedDict",
    "ChainMap",
    "UserDict",
    "UserList",
    "UserString",
    "timedelta",
    "date",
    "datetime",
    "time",
    "tzinfo",
    "timezone",
    "Decimal",
    "Fraction",
    "Pattern",
    "Match",
    "UUID",
    "Enum",
    "IntEnum",
    "Flag",
    "IntFlag",
    "auto",
    "Lock",
    "RLock",
    "Semaphore",
    "BoundedSemaphore",
    "Event",
    "Condition",
    "Barrier",
    "Thread",
    "Timer",
    "Process",
    "Pool",
    "Queue",
    "Pipe",
    "Manager",
    "Value",
    "Array",
    "ctypes",
    "Struct",
    "Union",
    "BytesIO",
    "StringIO",
    "TextIOWrapper",
    "FileIO",
    "BufferedReader",
    "BufferedWriter",
    "BufferedRandom",
    "BufferedRWPair",
    "ConfigParser",
    "RawConfigParser",
    "SafeConfigParser",
}


@dataclass
class Issue:
    rule_id: str
    rule_name: str
    severity: str
    file_path: str
    line: int
    description: str
    code_snippet: str
    suggested_fix: str
    verification: str
    category: str


@dataclass
class SectorResult:
    sector_id: str
    sector_name: str
    scope_paths: list[str]
    files_reviewed: int = 0
    total_loc: int = 0
    issues: list[Issue] = field(default_factory=list)
    positive_observations: list[str] = field(default_factory=list)
    sub_results: list[SectorResult] = field(default_factory=list)

    @property
    def is_orchestrator(self) -> bool:
        return bool(self.sub_results)

    @property
    def all_issues(self) -> list[Issue]:
        if not self.is_orchestrator:
            return self.issues
        all_iss = []
        for sub in self.sub_results:
            all_iss.extend(sub.all_issues)
        return all_iss


class ReviewOrchestrator:
    def __init__(
        self, repo_root: Path | None = None, reports_dir: Path | None = None
    ) -> None:
        self.repo_root = repo_root or Path.cwd()
        self.reports_dir = reports_dir or self.repo_root / "reports" / "review"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.sectors = [
            {"id": "S1", "name": "Domain", "paths": [DOMAIN_ROOT]},
            {"id": "S2", "name": "Application", "paths": ["src/bioetl/application"]},
            {
                "id": "S3",
                "name": "Infrastructure",
                "paths": ["src/bioetl/infrastructure"],
            },
            {
                "id": "S4",
                "name": "Composition + Interfaces",
                "paths": [COMPOSITION_ROOT, INTERFACES_ROOT],
            },
            {"id": "S6", "name": "Tests", "paths": ["tests"]},
            {"id": "S7", "name": "Configs", "paths": ["configs"]},
            {"id": "S8", "name": "Documentation", "paths": ["docs"]},
            # S5 Cross-cutting is handled separately or over the whole src/
            {"id": "S5", "name": "Cross-cutting", "paths": ["src/bioetl"]},
        ]

    def _resolve_path(self, path: str) -> Path:
        return self.repo_root / path

    def _existing_paths(self, *paths: str) -> list[str]:
        return [path for path in paths if self._resolve_path(path).exists()]

    def _remaining_subdirs(self, base: str, covered_paths: set[str]) -> list[str]:
        base_path = self._resolve_path(base)
        if not base_path.exists():
            return []
        remaining: list[str] = []
        for child in sorted(base_path.iterdir(), key=lambda entry: entry.name):
            if (
                not child.is_dir()
                or child.name.startswith(".")
                or child.name == "__pycache__"
            ):
                continue
            rel_path = f"{base}/{child.name}"
            if rel_path not in covered_paths:
                remaining.append(rel_path)
        return remaining

    def _dedupe_paths(self, paths: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for path in paths:
            if path not in seen:
                deduped.append(path)
                seen.add(path)
        return deduped

    def _relative_path(self, file_path: Path) -> str:
        try:
            return file_path.relative_to(self.repo_root).as_posix()
        except ValueError:
            return file_path.as_posix()

    def _build_parent_map(self, tree: ast.AST) -> dict[int, ast.AST]:
        parent_map: dict[int, ast.AST] = {}
        for parent in ast.walk(tree):
            for child in ast.iter_child_nodes(parent):
                parent_map[id(child)] = parent
        return parent_map

    def _is_type_checking_expr(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Name):
            return node.id == "TYPE_CHECKING"
        if isinstance(node, ast.Attribute):
            return (
                isinstance(node.value, ast.Name)
                and node.value.id == "typing"
                and node.attr == "TYPE_CHECKING"
            )
        if isinstance(node, ast.BoolOp):
            return any(self._is_type_checking_expr(value) for value in node.values)
        return False

    def _is_type_checking_guarded(
        self, node: ast.AST, parent_map: dict[int, ast.AST]
    ) -> bool:
        current = parent_map.get(id(node))
        while current is not None:
            if isinstance(current, ast.If) and self._is_type_checking_expr(
                current.test
            ):
                return True
            current = parent_map.get(id(current))
        return False

    def _iter_import_modules(self, node: ast.Import | ast.ImportFrom) -> list[str]:
        if isinstance(node, ast.ImportFrom):
            return [node.module or ""]
        return [alias.name for alias in node.names]

    def _detect_rules_version(self) -> str:
        readme_path = self.repo_root / "README.md"
        if readme_path.exists():
            readme = readme_path.read_text(encoding="utf-8")
            for line in readme.splitlines():
                if "RULES.md" not in line or "(v" not in line:
                    continue
                _, _, version_part = line.partition("(v")
                version, separator, _ = version_part.partition(")")
                if separator and version:
                    return version
        return "unknown"

    def _today(self) -> str:
        return datetime.now().strftime("%Y-%m-%d")

    def _sector_report_path(self, result: SectorResult) -> Path:
        safe_name = result.sector_name.replace("+", "_").replace(" ", "_")
        return self.reports_dir / f"{result.sector_id}-{safe_name}.md"

    def _category_stats(
        self, issues: list[Issue]
    ) -> tuple[dict[str, dict[str, int]], dict[str, float]]:
        cat_stats: dict[str, dict[str, int]] = {}
        for issue in issues:
            cat = issue.category
            if cat not in cat_stats:
                cat_stats[cat] = {
                    "total": 0,
                    "CRITICAL": 0,
                    "HIGH": 0,
                    "MEDIUM": 0,
                    "LOW": 0,
                }
            cat_stats[cat]["total"] += 1
            cat_stats[cat][issue.severity] += 1
        _, cat_scores = self.calculate_score(issues)
        return cat_stats, cat_scores

    def _severity_partition(
        self, issues: list[Issue]
    ) -> tuple[list[Issue], list[Issue], list[Issue], list[Issue]]:
        critical = [issue for issue in issues if issue.severity == "CRITICAL"]
        high = [issue for issue in issues if issue.severity == "HIGH"]
        medium = [issue for issue in issues if issue.severity == "MEDIUM"]
        low = [issue for issue in issues if issue.severity == "LOW"]
        return critical, high, medium, low

    def _static_subsectors(self, sector_id: str) -> list[dict[str, Any]]:
        return [dict(item) for item in STATIC_SUBSECTOR_DEFS.get(sector_id, [])]

    def _covered_paths(self, path_groups: tuple[tuple[str, ...], ...]) -> set[str]:
        return set(self._existing_paths(*(path for group in path_groups for path in group)))

    def _configured_subsectors(
        self,
        definitions: tuple[tuple[str, str, tuple[str, ...]], ...],
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": subsector_id,
                "name": name,
                "paths": self._existing_paths(*paths),
            }
            for subsector_id, name, paths in definitions
        ]

    def _other_subsector(
        self,
        *,
        subsector_id: str,
        name: str,
        explicit_paths: tuple[str, ...],
        root: str,
        covered_paths: set[str],
    ) -> dict[str, Any]:
        return {
            "id": subsector_id,
            "name": name,
            "paths": self._dedupe_paths(
                self._existing_paths(*explicit_paths)
                + self._remaining_subdirs(root, covered_paths)
            ),
        }

    def _domain_subsectors(self) -> list[dict[str, Any]]:
        covered_domain_paths = self._covered_paths(DOMAIN_COVERED_PATH_GROUPS)
        return [
            *self._configured_subsectors(DOMAIN_SUBSECTOR_DEFS),
            self._other_subsector(
                subsector_id="S1.5",
                name="Other",
                explicit_paths=DOMAIN_OTHER_PATHS,
                root="src/bioetl/domain",
                covered_paths=covered_domain_paths,
            ),
        ]

    def _config_subsectors(self) -> list[dict[str, Any]]:
        covered_config_paths = self._covered_paths(CONFIG_COVERED_PATH_GROUPS)
        return [
            *self._configured_subsectors(CONFIG_SUBSECTOR_DEFS),
            self._other_subsector(
                subsector_id="S7.3",
                name="Other Configs",
                explicit_paths=CONFIG_OTHER_PATHS,
                root="configs",
                covered_paths=covered_config_paths,
            ),
        ]

    def _docs_subsectors(self) -> list[dict[str, Any]]:
        covered_doc_paths = self._covered_paths(DOC_COVERED_PATH_GROUPS)
        return [
            *self._configured_subsectors(DOC_SUBSECTOR_DEFS),
            self._other_subsector(
                subsector_id="S8.4",
                name="Guides+Other Docs",
                explicit_paths=DOC_OTHER_PATHS,
                root="docs",
                covered_paths=covered_doc_paths,
            ),
        ]

    def count_files_and_loc(
        self, paths: list[str], file_exts: set[str]
    ) -> tuple[int, int, list[Path]]:
        total_files = 0
        total_loc = 0
        file_paths: list[Path] = []

        for p in paths:
            base_path = self._resolve_path(p)
            if not base_path.exists():
                continue
            if base_path.is_file():
                total_files, total_loc = self._accumulate_review_file(
                    base_path,
                    file_exts,
                    file_paths,
                    total_files,
                    total_loc,
                )
                continue

            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if d not in IGNORED_REVIEW_DIRS]
                for file in files:
                    file_path = Path(root) / file
                    total_files, total_loc = self._accumulate_review_file(
                        file_path,
                        file_exts,
                        file_paths,
                        total_files,
                        total_loc,
                    )
        return total_files, total_loc, file_paths

    def _accumulate_review_file(
        self,
        file_path: Path,
        file_exts: set[str],
        file_paths: list[Path],
        total_files: int,
        total_loc: int,
    ) -> tuple[int, int]:
        if file_path.suffix not in file_exts:
            return total_files, total_loc
        file_paths.append(file_path)
        loc = self._safe_loc(file_path)
        if loc is None:
            return total_files, total_loc
        return total_files + 1, total_loc + loc

    def _safe_loc(self, file_path: Path) -> int | None:
        try:
            with file_path.open(encoding="utf-8") as handle:
                return sum(1 for _ in handle)
        except OSError:
            return None

    def determine_subsectors(
        self, sector_id: str, _paths: list[str]
    ) -> list[dict[str, Any]]:
        subsector_builders = {
            "S1": self._domain_subsectors,
            "S2": lambda: self._static_subsectors("S2"),
            "S3": lambda: self._static_subsectors("S3"),
            "S4": lambda: self._static_subsectors("S4"),
            "S5": lambda: self._static_subsectors("S5"),
            "S6": lambda: self._static_subsectors("S6"),
            "S7": self._config_subsectors,
            "S8": self._docs_subsectors,
        }
        builder = subsector_builders.get(sector_id)
        if builder is None:
            return []
        return builder()

    def analyze_yaml_file(self, file_path: Path, _sector_id: str) -> list[Issue]:
        issues: list[Issue] = []
        relative_path = self._relative_path(file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return issues

        if relative_path.startswith("configs/"):
            # Very basic checks for S7 (Configs)
            if "sort_by:" not in content and "silver" in content.lower():
                issues.append(
                    Issue(
                        rule_id="ADR-014",
                        rule_name="Sort by in Silver",
                        severity="MEDIUM",
                        file_path=relative_path,
                        line=0,
                        description="Missing sort_by configuration for Silver sink.",
                        code_snippet="",
                        suggested_fix="Add sort_by field.",
                        verification="manual",
                        category="Configs",
                    )
                )
            if "soft_fail" in content and "inline_thresholds" in content:
                issues.append(
                    Issue(
                        rule_id="ADR-027",
                        rule_name="No inline DQ thresholds",
                        severity="MEDIUM",
                        file_path=relative_path,
                        line=0,
                        description="Found inline DQ thresholds.",
                        code_snippet="",
                        suggested_fix="Move to DQ config.",
                        verification="manual",
                        category="Configs",
                    )
                )

        return issues

    def analyze_markdown_file(self, file_path: Path, _sector_id: str) -> list[Issue]:
        issues: list[Issue] = []
        relative_path = self._relative_path(file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return issues

        if "docs/02-architecture/decisions" in relative_path:
            if "Status:" not in content:
                issues.append(
                    Issue(
                        rule_id="DOC-001",
                        rule_name="ADR Status missing",
                        severity="LOW",
                        file_path=relative_path,
                        line=0,
                        description="ADR is missing 'Status' field.",
                        code_snippet="",
                        suggested_fix="Add Status: Accepted/Superseded",
                        verification="manual",
                        category="Documentation",
                    )
                )
        return issues

    def analyze_python_file(self, file_path: Path, _sector_id: str) -> list[Issue]:
        issues: list[Issue] = []
        relative_path = self._relative_path(file_path)
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception:
            return issues

        try:
            tree = ast.parse(content)
        except SyntaxError:
            return issues
        parent_map = self._build_parent_map(tree)

        for node in ast.walk(tree):
            self._collect_python_ast_issues(
                issues,
                node,
                relative_path,
                file_path,
                content,
                parent_map,
            )

        self._collect_hardcoded_secret_issues(issues, content, relative_path, file_path)

        return issues

    def _collect_python_ast_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
        file_path: Path,
        content: str,
        parent_map: dict[ast.AST, ast.AST],
    ) -> None:
        self._collect_constructor_issues(issues, node, relative_path)
        self._collect_structlog_import_issues(issues, node, relative_path)
        self._collect_import_boundary_issues(issues, node, relative_path, parent_map)
        self._collect_protocol_naming_issues(issues, node, relative_path, file_path)
        self._collect_port_facade_import_issues(issues, node, relative_path)
        self._collect_print_issues(issues, node, relative_path, file_path)
        self._collect_service_locator_issues(issues, node, relative_path)
        self._collect_public_annotation_issues(issues, node, relative_path)
        self._collect_any_usage_issues(issues, node, relative_path, content)

    def _collect_constructor_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
    ) -> None:
        if not isinstance(node, ast.FunctionDef) or node.name != "__init__":
            return
        for stmt in node.body:
            issue = self._constructor_issue(stmt, relative_path)
            if issue is not None:
                issues.append(issue)

    def _constructor_issue(self, stmt: ast.stmt, relative_path: str) -> Issue | None:
        if not isinstance(stmt, ast.Assign):
            return None
        for target in stmt.targets:
            if not (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                continue
            if not (isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name)):
                continue
            func_name = stmt.value.func.id
            if not (func_name[0].isupper() and func_name not in ALLOWED_CONSTRUCTORS):
                continue
            return Issue(
                rule_id="AP-001",
                rule_name="DI Violation - Hard-coded Constructor",
                severity="CRITICAL",
                file_path=relative_path,
                line=stmt.lineno,
                description=f"Hard-coded dependency instantiation: {func_name}()",
                code_snippet=ast.unparse(stmt),
                suggested_fix="Inject dependency via constructor.",
                verification="Check DI configuration.",
                category="Anti-Patterns",
            )
        return None

    def _collect_structlog_import_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
    ) -> None:
        if "infrastructure/observability" in relative_path or "tests/" in relative_path:
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "structlog":
                    issues.append(self._direct_structlog_issue(node, relative_path))
        elif isinstance(node, ast.ImportFrom) and node.module == "structlog":
            issues.append(self._direct_structlog_issue(node, relative_path))

    def _direct_structlog_issue(self, node: ast.AST, relative_path: str) -> Issue:
        return Issue(
            rule_id="AP-002",
            rule_name="Direct structlog Import",
            severity="HIGH",
            file_path=relative_path,
            line=node.lineno,
            description="Direct import of structlog outside infrastructure.",
            code_snippet=ast.unparse(node),
            suggested_fix="Use LoggerPort.",
            verification="Check imports.",
            category="Anti-Patterns",
        )

    def _collect_import_boundary_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
        parent_map: dict[ast.AST, ast.AST],
    ) -> None:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            return
        for module in self._iter_import_modules(node):
            if self._is_type_checking_guarded(node, parent_map):
                continue
            issue = self._import_boundary_issue(node, relative_path, module)
            if issue is not None:
                issues.append(issue)

    def _import_boundary_issue(
        self,
        node: ast.AST,
        relative_path: str,
        module: str,
    ) -> Issue | None:
        if relative_path.startswith("src/bioetl/domain/") and module.startswith("bioetl.infrastructure"):
            return Issue(
                rule_id="ARCH-001",
                rule_name="Import Boundary Violation",
                severity="CRITICAL",
                file_path=relative_path,
                line=node.lineno,
                description="Domain layer importing from Infrastructure layer.",
                code_snippet=ast.unparse(node),
                suggested_fix="Remove dependency.",
                verification="importlinter",
                category="Architecture",
            )
        if relative_path.startswith("src/bioetl/application/") and module.startswith("bioetl.infrastructure"):
            return Issue(
                rule_id="ARCH-001",
                rule_name="Import Boundary Violation",
                severity="CRITICAL",
                file_path=relative_path,
                line=node.lineno,
                description="Application layer importing from Infrastructure layer.",
                code_snippet=ast.unparse(node),
                suggested_fix="Use Ports.",
                verification="importlinter",
                category="Architecture",
            )
        return None

    def _collect_protocol_naming_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
        file_path: Path,
    ) -> None:
        if not isinstance(node, ast.ClassDef):
            return
        if "domain/ports" not in str(file_path):
            return
        if "Protocol" not in [getattr(b, "id", "") for b in node.bases]:
            return
        if node.name.endswith("Port"):
            return
        issues.append(
            Issue(
                rule_id="ARCH-003",
                rule_name="Port Protocol Naming",
                severity="HIGH",
                file_path=relative_path,
                line=node.lineno,
                description=f"Protocol {node.name} in domain/ports must end with 'Port'.",
                code_snippet=f"class {node.name}(Protocol):",
                suggested_fix=f"Rename to {node.name}Port.",
                verification="pytest tests/architecture/",
                category="Architecture",
            )
        )

    def _collect_port_facade_import_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
    ) -> None:
        if not isinstance(node, ast.ImportFrom):
            return
        if not (
            node.module
            and node.module.startswith("bioetl.domain.ports.")
            and node.module != "bioetl.domain.ports"
        ):
            return
        issues.append(
            Issue(
                rule_id="ARCH-008",
                rule_name="Single Source of Imports",
                severity="MEDIUM",
                file_path=relative_path,
                line=node.lineno,
                description="Ports must be imported from bioetl.domain.ports facade.",
                code_snippet=ast.unparse(node),
                suggested_fix="from bioetl.domain.ports import ...",
                verification="pytest tests/architecture/",
                category="Architecture",
            )
        )

    def _collect_print_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
        file_path: Path,
    ) -> None:
        if "interfaces/cli" in str(file_path):
            return
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
        ):
            return
        issues.append(
            Issue(
                rule_id="AP-006",
                rule_name="Print Statements",
                severity="MEDIUM",
                file_path=relative_path,
                line=node.lineno,
                description="Use of print() outside CLI.",
                code_snippet=ast.unparse(node),
                suggested_fix="Use structured logging.",
                verification="grep -rn print src/bioetl/",
                category="Anti-Patterns",
            )
        )

    def _collect_service_locator_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
    ) -> None:
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
            return
        if not (
            (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "ServiceLocator"
                and node.func.attr == "get"
            )
            or (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "Container"
                and node.func.attr in ("resolve", "get")
            )
        ):
            return
        issues.append(
            Issue(
                rule_id="DI-003",
                rule_name="Service Locator",
                severity="CRITICAL",
                file_path=relative_path,
                line=node.lineno,
                description="Use of Service Locator pattern.",
                code_snippet=ast.unparse(node),
                suggested_fix="Use Constructor Injection.",
                verification="grep -rn ServiceLocator",
                category="DI Violations",
            )
        )

    def _collect_public_annotation_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
    ) -> None:
        if not (
            isinstance(node, ast.FunctionDef)
            and not node.name.startswith("_")
            and node.name not in ("__init__", "__main__")
            and getattr(node, "returns", None) is None
        ):
            return
        issues.append(
            Issue(
                rule_id="TYPE-001",
                rule_name="Public Function Annotations",
                severity="HIGH",
                file_path=relative_path,
                line=node.lineno,
                description=f"Public function '{node.name}' lacks return type annotation.",
                code_snippet=f"def {node.name}(...):",
                suggested_fix="Add -> Type:",
                verification="mypy --strict",
                category="Types",
            )
        )

    def _collect_any_usage_issues(
        self,
        issues: list[Issue],
        node: ast.AST,
        relative_path: str,
        content: str,
    ) -> None:
        if not (isinstance(node, ast.Name) and node.id == "Any"):
            return
        line_str = content.splitlines()[node.lineno - 1]
        if "#" in line_str and "Any" in line_str.split("#")[1]:
            return
        issues.append(
            Issue(
                rule_id="TYPE-002",
                rule_name="Any Usage",
                severity="HIGH",
                file_path=relative_path,
                line=node.lineno,
                description="Usage of Any without comment justification.",
                code_snippet=line_str.strip(),
                suggested_fix="Add comment like # Any: reason",
                verification="mypy --strict",
                category="Types",
            )
        )

    def _collect_hardcoded_secret_issues(
        self,
        issues: list[Issue],
        content: str,
        relative_path: str,
        file_path: Path,
    ) -> None:
        if "tests/" in str(file_path):
            return
        for i, line in enumerate(content.splitlines(), start=1):
            if re.search(r"(password|api_key|secret)\s*=\s*[\"\']", line, re.IGNORECASE):
                issues.append(
                    Issue(
                        rule_id="AP-005",
                        rule_name="Hardcoded Secrets",
                        severity="CRITICAL",
                        file_path=relative_path,
                        line=i,
                        description="Potential hardcoded secret found.",
                        code_snippet=line.strip(),
                        suggested_fix="Use os.environ.",
                        verification="make security",
                        category="Anti-Patterns",
                    )
                )

    def calculate_score(self, issues: list[Issue]) -> tuple[float, dict[str, float]]:
        category_issues = self._issues_by_category(issues)

        final_score = 0.0
        cat_scores: dict[str, float] = {}

        for cat, weight in SCORE_WEIGHTS.items():
            if cat not in category_issues:
                cat_scores[cat] = 10.0
                final_score += 10.0 * weight
                continue

            deduction_sum = sum(
                (SCORE_DEDUCTIONS.get(i.severity, 0.0) for i in category_issues[cat]),
                0.0,
            )
            cat_score = max(0.0, 10.0 + deduction_sum)
            cat_scores[cat] = cat_score
            final_score += cat_score * weight

        final_score = min(10.0, max(0.0, final_score))
        return final_score, cat_scores

    def _issues_by_category(self, issues: list[Issue]) -> dict[str, list[Issue]]:
        category_issues: dict[str, list[Issue]] = {}
        for issue in issues:
            category_issues.setdefault(issue.category, []).append(issue)
        return category_issues

    def get_status(self, score: float) -> str:
        if score >= 8.0:
            return "PASS"
        elif score >= 6.0:
            return "WARN"
        return "FAIL"

    def write_worker_report(self, result: SectorResult) -> None:
        score, _ = self.calculate_score(result.issues)
        status = self.get_status(score)

        report = f"# Code Review Report — {result.sector_id}: {result.sector_name}\n\n"
        report += f"**Date**: {self._today()}\n"
        report += f"**Scope**: {', '.join(result.scope_paths)}\n"
        report += f"**Files reviewed**: {result.files_reviewed}\n"
        report += f"**Total LOC**: {result.total_loc}\n"
        report += f"**Status**: {status}\n"
        report += f"**Score**: {score:.1f}/10.0\n\n"
        report += "---\n\n## Summary\n"
        report += "| Category | Issues | CRIT | HIGH | MED | LOW | Score |\n"
        report += "|----------|--------|------|------|-----|-----|-------|\n"

        cat_stats, cat_scores = self._category_stats(result.issues)

        report += "".join(self._worker_category_rows(cat_stats, cat_scores))

        report += "\n## Critical Issues (MUST fix before merge)\n"
        report += "".join(
            self._worker_critical_issue_block(issue)
            for issue in result.issues
            if issue.severity == "CRITICAL"
        )

        self._sector_report_path(result).write_text(report, encoding="utf-8")

    def _worker_category_rows(
        self,
        cat_stats: dict[str, dict[str, int]],
        cat_scores: dict[str, float],
    ) -> list[str]:
        rows: list[str] = []
        for cat, stats in cat_stats.items():
            rows.append(
                f"| {cat} | {stats['total']} | {stats['CRITICAL']} | "
                f"{stats['HIGH']} | {stats['MEDIUM']} | {stats['LOW']} | "
                f"{cat_scores.get(cat, 10.0):.1f} |\n"
            )
        return rows

    def _worker_critical_issue_block(self, issue: Issue) -> str:
        return (
            f"### {issue.rule_id}: {issue.rule_name}\n"
            f"- **Rule**: {issue.rule_id} ({issue.rule_name})\n"
            f"- **Severity**: {issue.severity}\n"
            f"- **File**: `{issue.file_path}:{issue.line}`\n"
            f"- **Description**: {issue.description}\n"
            "- **Code**:\n  ```python\n"
            f"  {issue.code_snippet}\n  ```\n"
            f"- **Fix**: {issue.suggested_fix}\n"
            f"- **Verification**: `{issue.verification}`\n\n"
        )

    def write_orchestrator_report(self, result: SectorResult) -> None:
        if not result.sub_results:
            return

        total_files = sum(s.files_reviewed for s in result.sub_results)
        weighted_score_sum = 0.0

        sub_reports_lines: list[str] = []
        all_crit: list[Issue] = []
        all_high: list[Issue] = []

        for sub in result.sub_results:
            weighted_score_sum += self._orchestrator_subreport(
                sub,
                total_files,
                sub_reports_lines,
                all_crit,
                all_high,
            )

        overall_status = self.get_status(weighted_score_sum)

        report = f"# Consolidated Review — {result.sector_id}: {result.sector_name}\n\n"
        report += f"**Date**: {self._today()}\n"
        report += f"**Sub-reviews**: {len(result.sub_results)} agents\n"
        report += f"**Status**: {overall_status}\n"
        report += f"**Consolidated Score**: {weighted_score_sum:.1f}\n\n"
        report += "## Sub-review Summary\n"
        report += "| Sub-sector | Files | Score | Status | CRIT | HIGH |\n"
        report += "|------------|-------|-------|--------|------|------|\n"
        report += "\n".join(sub_reports_lines) + "\n\n"

        report += "## Aggregated Issues\n### Critical (MUST fix)\n"
        report += "".join(self._aggregated_issue_lines(all_crit[:20]))

        self._sector_report_path(result).write_text(report, encoding="utf-8")

    def _orchestrator_subreport(
        self,
        sub: SectorResult,
        total_files: int,
        sub_reports_lines: list[str],
        all_crit: list[Issue],
        all_high: list[Issue],
    ) -> float:
        score, _ = self.calculate_score(sub.issues)
        status = self.get_status(score)
        crit_c = sum(1 for i in sub.issues if i.severity == "CRITICAL")
        high_c = sum(1 for i in sub.issues if i.severity == "HIGH")
        sub_reports_lines.append(
            f"| {sub.sector_id} — {sub.sector_name} | {sub.files_reviewed} | "
            f"{score:.1f} | {status} | {crit_c} | {high_c} |"
        )
        all_crit.extend(i for i in sub.issues if i.severity == "CRITICAL")
        all_high.extend(i for i in sub.issues if i.severity == "HIGH")
        return (sub.files_reviewed / max(1, total_files)) * score

    def _aggregated_issue_lines(self, issues: list[Issue]) -> list[str]:
        return [
            f"{index}. **{issue.rule_id}** in `{issue.file_path}:{issue.line}` - {issue.description}\n"
            for index, issue in enumerate(issues, start=1)
        ]

    def write_final_report(self, results: list[SectorResult]) -> None:
        total_files = sum(r.files_reviewed for r in results)
        total_loc = sum(r.total_loc for r in results)

        final_score = 0.0
        all_issues: list[Issue] = []
        sector_lines: list[str] = []

        for r in results:
            score = self._sector_score(r)
            all_issues.extend(r.all_issues if r.is_orchestrator else r.issues)
            status = self.get_status(score)
            final_score += score * SECTOR_WEIGHTS.get(r.sector_id, 0.0)
            sector_lines.append(self._final_sector_row(r, score, status))

        overall_status = self.get_status(final_score)

        crit_issues, high_issues, med_issues, low_issues = self._severity_partition(
            all_issues
        )

        report = "# BioETL — Full Project Review Report\n\n"
        report += f"**Date**: {self._today()}\n"
        report += f"**RULES.md Version**: {self._detect_rules_version()}\n"
        report += "**Project Version**: 1.0.0\n"
        report += f"**Total files reviewed**: {total_files}\n"
        report += f"**Total LOC reviewed**: {total_loc}\n\n"
        report += "---\n\n## Executive Summary\n"
        report += f"**Overall Status**: {overall_status}\n"
        report += f"**Overall Score**: {final_score:.1f}/10.0\n\n"
        report += "### Key Metrics\n"
        report += "| Metric | Value |\n|--------|-------|\n"
        report += "".join(
            self._final_metric_rows(
                all_issues=all_issues,
                crit_issues=crit_issues,
                high_issues=high_issues,
                med_issues=med_issues,
                low_issues=low_issues,
                results=results,
            )
        )
        report += "\n"

        report += "---\n\n## Sector Scores\n"
        report += "| Sector | Scope | Files | LOC | Score | Status |\n"
        report += "|--------|-------|-------|-----|-------|--------|\n"
        report += "\n".join(sector_lines) + "\n\n"

        report += "---\n\n## Critical Issues (блокируют merge/release)\n"
        report += "".join(
            f"- **{issue.rule_id}**: {issue.file_path}:{issue.line} - {issue.description}\n"
            for issue in crit_issues[:50]
        )

        report_path = self.reports_dir / "FINAL-REVIEW.md"
        report_path.write_text(report, encoding="utf-8")

    def _final_metric_rows(
        self,
        *,
        all_issues: list[Issue],
        crit_issues: list[Issue],
        high_issues: list[Issue],
        med_issues: list[Issue],
        low_issues: list[Issue],
        results: list[SectorResult],
    ) -> list[str]:
        return [
            f"| Total issues found | {len(all_issues)} |\n",
            f"| Critical issues | {len(crit_issues)} |\n",
            f"| High issues | {len(high_issues)} |\n",
            f"| Medium issues | {len(med_issues)} |\n",
            f"| Low issues | {len(low_issues)} |\n",
            f"| Sectors reviewed | {len(results)} |\n",
        ]

    def _sector_score(self, result: SectorResult) -> float:
        if not result.is_orchestrator:
            return self.calculate_score(result.issues)[0]
        total_f = sum(s.files_reviewed for s in result.sub_results)
        return sum(
            (s.files_reviewed / max(1, total_f)) * self.calculate_score(s.issues)[0]
            for s in result.sub_results
        )

    def _final_sector_row(self, result: SectorResult, score: float, status: str) -> str:
        paths_str = ", ".join(result.scope_paths)
        return (
            f"| {result.sector_id} {result.sector_name} | {paths_str} | "
            f"{result.files_reviewed} | {result.total_loc} | {score:.1f} | {status} |"
        )

    def review_sector(
        self, sector: dict[str, Any], is_l3: bool = False
    ) -> SectorResult:
        sector_id = sector["id"]
        sector_name = sector["name"]
        paths = sector["paths"]

        file_exts = self._sector_file_extensions(sector_id)

        total_files, total_loc, file_paths = self.count_files_and_loc(paths, file_exts)

        needs_delegation = self._needs_sector_delegation(
            sector_id,
            total_files,
            total_loc,
            is_l3=is_l3,
        )

        result = SectorResult(
            sector_id=sector_id,
            sector_name=sector_name,
            scope_paths=paths,
            files_reviewed=total_files,
            total_loc=total_loc,
        )

        if needs_delegation:
            subsectors = self.determine_subsectors(sector_id, paths)
            for sub in subsectors:
                sub_result = self.review_sector(sub, is_l3=True)
                result.sub_results.append(sub_result)
            self.write_orchestrator_report(result)
        else:
            for filepath in file_paths:
                result.issues.extend(self._analyze_sector_file(filepath, sector_id))
            self.write_worker_report(result)

        return result

    def _sector_file_extensions(self, sector_id: str) -> set[str]:
        if sector_id.startswith("S7"):
            return {".yaml", ".yml"}
        if sector_id.startswith("S8"):
            return {".md"}
        return {".py"}

    def _needs_sector_delegation(
        self,
        sector_id: str,
        total_files: int,
        total_loc: int,
        *,
        is_l3: bool,
    ) -> bool:
        if is_l3:
            return False
        threshold_files = 40
        if sector_id.startswith("S7"):
            threshold_files = 20
        elif sector_id.startswith("S8"):
            threshold_files = 30
        return total_files > threshold_files or total_loc > LOC_THRESHOLD

    def _analyze_sector_file(self, filepath: Path, sector_id: str) -> list[Issue]:
        if filepath.suffix == ".py":
            return self.analyze_python_file(filepath, sector_id)
        if filepath.suffix in (".yaml", ".yml"):
            return self.analyze_yaml_file(filepath, sector_id)
        if filepath.suffix == ".md":
            return self.analyze_markdown_file(filepath, sector_id)
        return []

    def run(self) -> None:
        print("Starting hierarchical code review...")
        final_results: list[SectorResult] = []
        for sector in self.sectors:
            print(f"Reviewing sector {sector['id']} ({sector['name']})...")
            res = self.review_sector(sector)
            final_results.append(res)
        self.write_final_report(final_results)
        print("Review complete. Reports generated in reports/review/")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run hierarchical BioETL code review orchestration.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root to analyze.",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        help="Optional directory for generated review reports.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    orchestrator = ReviewOrchestrator(
        repo_root=args.repo_root,
        reports_dir=args.reports_dir,
    )
    orchestrator.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
