from __future__ import annotations

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
            {"id": "S1", "name": "Domain", "paths": ["src/bioetl/domain"]},
            {"id": "S2", "name": "Application", "paths": ["src/bioetl/application"]},
            {
                "id": "S3",
                "name": "Infrastructure",
                "paths": ["src/bioetl/infrastructure"],
            },
            {
                "id": "S4",
                "name": "Composition + Interfaces",
                "paths": ["src/bioetl/composition", "src/bioetl/interfaces"],
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
            match = re.search(r"RULES\.md.*\(v([^)]+)\)", readme)
            if match:
                return match.group(1)
        return "unknown"

    def count_files_and_loc(
        self, paths: list[str], file_exts: set[str]
    ) -> tuple[int, int, list[Path]]:
        total_files = 0
        total_loc = 0
        file_paths = []
        ignore_dirs = {
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

        for p in paths:
            base_path = self._resolve_path(p)
            if not base_path.exists():
                continue
            if base_path.is_file():
                if base_path.suffix in file_exts:
                    file_paths.append(base_path)
                    try:
                        loc = sum(1 for _ in open(base_path, "r", encoding="utf-8"))
                        total_loc += loc
                        total_files += 1
                    except OSError:
                        continue
                continue

            for root, dirs, files in os.walk(base_path):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                for file in files:
                    file_path = Path(root) / file
                    if file_path.suffix in file_exts:
                        file_paths.append(file_path)
                        try:
                            loc = sum(1 for _ in open(file_path, encoding="utf-8"))
                            total_loc += loc
                            total_files += 1
                        except OSError:
                            continue
        return total_files, total_loc, file_paths

    def determine_subsectors(
        self, sector_id: str, _paths: list[str]
    ) -> list[dict[str, Any]]:
        # Hardcoded subsectors matching the issue description for simplicity
        if sector_id == "S1":
            covered_domain_paths = set(
                self._existing_paths(
                    "src/bioetl/domain/ports",
                    "src/bioetl/domain/contracts",
                    "src/bioetl/domain/entities",
                    "src/bioetl/domain/value_objects",
                    "src/bioetl/domain/schemas",
                    "src/bioetl/domain/services",
                    "src/bioetl/domain/filtering",
                    "src/bioetl/domain/mapping",
                    "src/bioetl/domain/config",
                    "src/bioetl/domain/composite",
                    "src/bioetl/domain/aggregates",
                    "src/bioetl/domain/registry",
                    "src/bioetl/domain/models",
                    "src/bioetl/domain/exceptions",
                )
            )
            return [
                {
                    "id": "S1.1",
                    "name": "Ports+Contracts",
                    "paths": self._existing_paths(
                        "src/bioetl/domain/ports", "src/bioetl/domain/contracts"
                    ),
                },
                {
                    "id": "S1.2",
                    "name": "Entities+VOs",
                    "paths": self._existing_paths(
                        "src/bioetl/domain/entities",
                        "src/bioetl/domain/value_objects",
                    ),
                },
                {
                    "id": "S1.3",
                    "name": "Schemas",
                    "paths": self._existing_paths("src/bioetl/domain/schemas"),
                },
                {
                    "id": "S1.4",
                    "name": "Services+Filters+Map",
                    "paths": self._existing_paths(
                        "src/bioetl/domain/services",
                        "src/bioetl/domain/filtering",
                        "src/bioetl/domain/mapping",
                    ),
                },
                {
                    "id": "S1.5",
                    "name": "Other",
                    "paths": self._dedupe_paths(
                        self._existing_paths(
                            "src/bioetl/domain/config",
                            "src/bioetl/domain/composite",
                            "src/bioetl/domain/aggregates",
                            "src/bioetl/domain/registry",
                            "src/bioetl/domain/models",
                            "src/bioetl/domain/exceptions",
                        )
                        + self._remaining_subdirs(
                            "src/bioetl/domain", covered_domain_paths
                        )
                    ),
                },
            ]
        elif sector_id == "S2":
            return [
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
            ]
        elif sector_id == "S3":
            return [
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
            ]
        elif sector_id == "S4":
            return [
                {
                    "id": "S4.1",
                    "name": "Composition",
                    "paths": ["src/bioetl/composition"],
                },
                {
                    "id": "S4.2",
                    "name": "Interfaces",
                    "paths": ["src/bioetl/interfaces"],
                },
            ]
        elif sector_id == "S5":
            return [
                {"id": "S5.1", "name": "Cross Domain", "paths": ["src/bioetl/domain"]},
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
                    "paths": ["src/bioetl/composition", "src/bioetl/interfaces"],
                },
            ]
        elif sector_id == "S7":
            covered_config_paths = set(
                self._existing_paths(
                    "configs/entities",
                    "configs/composites",
                    "configs/contracts",
                    "configs/providers",
                    "configs/base",
                    "configs/quality",
                    "configs/_schema",
                    "configs/enums",
                )
            )
            return [
                {"id": "S7.1", "name": "Entities", "paths": ["configs/entities"]},
                {
                    "id": "S7.2",
                    "name": "Composites+Contracts+Providers",
                    "paths": self._existing_paths(
                        "configs/composites",
                        "configs/contracts",
                        "configs/providers",
                    ),
                },
                {
                    "id": "S7.3",
                    "name": "Other Configs",
                    "paths": self._dedupe_paths(
                        self._existing_paths(
                            "configs/base",
                            "configs/quality",
                            "configs/_schema",
                            "configs/enums",
                        )
                        + self._remaining_subdirs("configs", covered_config_paths)
                    ),
                },
            ]
        elif sector_id == "S6":
            return [
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
            ]
        elif sector_id == "S8":
            covered_doc_paths = set(
                self._existing_paths(
                    "docs/00-project",
                    "docs/01-requirements",
                    "docs/02-architecture",
                    "docs/04-reference",
                )
            )
            return [
                {
                    "id": "S8.1",
                    "name": "Project+Reqs",
                    "paths": self._existing_paths(
                        "docs/00-project", "docs/01-requirements"
                    ),
                },
                {
                    "id": "S8.2",
                    "name": "Architecture",
                    "paths": self._existing_paths("docs/02-architecture"),
                },
                {
                    "id": "S8.3",
                    "name": "Reference",
                    "paths": self._existing_paths("docs/04-reference"),
                },
                {
                    "id": "S8.4",
                    "name": "Guides+Other Docs",
                    "paths": self._dedupe_paths(
                        self._existing_paths(
                            "docs/03-guides",
                            "docs/05-operations",
                        )
                        + self._remaining_subdirs("docs", covered_doc_paths)
                    ),
                },
            ]
        return []

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

        # Check EXC-005 (Large Files with Delegation) - crude heuristic
        is_large_file_ok = False
        if len(content.splitlines()) > 500:
            delegations = len(set(re.findall(r"self\._[a-z_]*\.", content)))
            if delegations > 5:
                is_large_file_ok = True

        allowed_constructors = {
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

        for node in ast.walk(tree):
            # AP-001 / DI-001: Hard-coded Constructor
            if isinstance(node, ast.FunctionDef) and node.name == "__init__":
                for stmt in node.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                if isinstance(stmt.value, ast.Call) and isinstance(
                                    stmt.value.func, ast.Name
                                ):
                                    func_name = stmt.value.func.id
                                    if (
                                        func_name[0].isupper()
                                        and func_name not in allowed_constructors
                                    ):
                                        issues.append(
                                            Issue(
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
                                        )

            # AP-002: Direct structlog import
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "structlog":
                        # allow in infrastructure/observability and tests (EXC-014)
                        if (
                            "infrastructure/observability" not in str(relative_path)
                            and "tests/" not in relative_path
                        ):
                            issues.append(
                                Issue(
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
                            )
            elif isinstance(node, ast.ImportFrom):
                if node.module == "structlog":
                    if (
                        "infrastructure/observability" not in str(relative_path)
                        and "tests/" not in relative_path
                    ):
                        issues.append(
                            Issue(
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
                        )

            # ARCH-001: Import Boundary Violation
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for module in self._iter_import_modules(node):
                    if self._is_type_checking_guarded(node, parent_map):
                        continue
                    if relative_path.startswith(
                        "src/bioetl/domain/"
                    ) and module.startswith("bioetl.infrastructure"):
                        issues.append(
                            Issue(
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
                        )
                    if relative_path.startswith(
                        "src/bioetl/application/"
                    ) and module.startswith("bioetl.infrastructure"):
                        issues.append(
                            Issue(
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
                        )

            # ARCH-003: Port Protocol Naming
            if isinstance(node, ast.ClassDef):
                if "Protocol" in [getattr(b, "id", "") for b in node.bases]:
                    if "domain/ports" in str(file_path):
                        if not node.name.endswith("Port"):
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

            # ARCH-008: Single Source of Imports
            if isinstance(node, ast.ImportFrom):
                if (
                    node.module
                    and node.module.startswith("bioetl.domain.ports.")
                    and not node.module == "bioetl.domain.ports"
                ):
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

            # AP-006: Print Statements
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                if "interfaces/cli" not in str(file_path):
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

            # DI-003: Service Locator
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "ServiceLocator"
                    and node.func.attr == "get"
                ) or (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "Container"
                    and node.func.attr in ("resolve", "get")
                ):
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

            # TYPE-001: Public Function Annotations
            if (
                isinstance(node, ast.FunctionDef)
                and not node.name.startswith("_")
                and node.name not in ("__init__", "__main__")
            ):
                if getattr(node, "returns", None) is None:
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

            # TYPE-002: Any Usage
            if isinstance(node, ast.Name) and node.id == "Any":
                # Check if there is a comment explaining it (Crude check by line)
                line_str = content.splitlines()[node.lineno - 1]
                if "#" not in line_str or "Any" not in line_str.split("#")[1]:
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

        # Check hardcoded secrets (AP-005)
        for i, line in enumerate(content.splitlines()):
            if re.search(
                r"(password|api_key|secret)\s*=\s*[\"\']", line, re.IGNORECASE
            ):
                if "tests/" not in str(file_path):
                    issues.append(
                        Issue(
                            rule_id="AP-005",
                            rule_name="Hardcoded Secrets",
                            severity="CRITICAL",
                            file_path=relative_path,
                            line=i + 1,
                            description="Potential hardcoded secret found.",
                            code_snippet=line.strip(),
                            suggested_fix="Use os.environ.",
                            verification="make security",
                            category="Anti-Patterns",
                        )
                    )

        return issues

    def calculate_score(self, issues: list[Issue]) -> tuple[float, dict[str, float]]:
        deductions = {"CRITICAL": -2.0, "HIGH": -1.0, "MEDIUM": -0.5, "LOW": -0.25}
        weights = {
            "Architecture": 0.30,
            "Anti-Patterns": 0.25,
            "DI Violations": 0.20,
            "Naming": 0.10,
            "Types": 0.10,
            "Testing": 0.05,
            "Configs": 0.05,
            "Documentation": 0.05,
        }

        category_issues: dict[str, list[Issue]] = {}
        for issue in issues:
            cat = issue.category
            if cat not in category_issues:
                category_issues[cat] = []
            category_issues[cat].append(issue)

        final_score = 0.0
        cat_scores: dict[str, float] = {}

        for cat, weight in weights.items():
            if cat not in category_issues:
                cat_scores[cat] = 10.0
                final_score += 10.0 * weight
                continue

            deduction_sum = sum(
                (deductions.get(i.severity, 0.0) for i in category_issues[cat]),
                0.0,
            )
            cat_score = max(0.0, 10.0 + deduction_sum)
            cat_scores[cat] = cat_score
            final_score += cat_score * weight

        # Ensure max 10.0
        final_score = min(10.0, max(0.0, final_score))
        return final_score, cat_scores

    def get_status(self, score: float) -> str:
        if score >= 8.0:
            return "PASS"
        elif score >= 6.0:
            return "WARN"
        return "FAIL"

    def write_worker_report(self, result: SectorResult) -> None:
        score, _ = self.calculate_score(result.issues)
        status = self.get_status(score)

        crit_count = sum(1 for i in result.issues if i.severity == "CRITICAL")
        high_count = sum(1 for i in result.issues if i.severity == "HIGH")

        report = f"# Code Review Report — {result.sector_id}: {result.sector_name}\n\n"
        report += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
        report += f"**Scope**: {', '.join(result.scope_paths)}\n"
        report += f"**Files reviewed**: {result.files_reviewed}\n"
        report += f"**Total LOC**: {result.total_loc}\n"
        report += f"**Status**: {status}\n"
        report += f"**Score**: {score:.1f}/10.0\n\n"
        report += "---\n\n## Summary\n"
        report += "| Category | Issues | CRIT | HIGH | MED | LOW | Score |\n"
        report += "|----------|--------|------|------|-----|-----|-------|\n"

        cat_stats: dict[str, dict[str, int]] = {}
        for issue in result.issues:
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

        _, cat_scores = self.calculate_score(result.issues)

        for cat in cat_stats:
            stats = cat_stats[cat]
            report += (
                f"| {cat} | {stats['total']} | {stats['CRITICAL']} | "
                f"{stats['HIGH']} | {stats['MEDIUM']} | {stats['LOW']} | "
                f"{cat_scores.get(cat, 10.0):.1f} |\n"
            )

        report += "\n## Critical Issues (MUST fix before merge)\n"
        for issue in [i for i in result.issues if i.severity == "CRITICAL"]:
            report += f"### {issue.rule_id}: {issue.rule_name}\n"
            report += f"- **Rule**: {issue.rule_id} ({issue.rule_name})\n"
            report += f"- **Severity**: {issue.severity}\n"
            report += f"- **File**: `{issue.file_path}:{issue.line}`\n"
            report += f"- **Description**: {issue.description}\n"
            report += "- **Code**:\n  ```python\n"
            report += f"  {issue.code_snippet}\n  ```\n"
            report += f"- **Fix**: {issue.suggested_fix}\n"
            report += f"- **Verification**: `{issue.verification}`\n\n"

        report += "\n## High Issues\n"
        for issue in [i for i in result.issues if i.severity == "HIGH"]:
            report += f"### {issue.rule_id}: {issue.rule_name}\n"
            report += f"- **Rule**: {issue.rule_id} ({issue.rule_name})\n"
            report += f"- **Severity**: {issue.severity}\n"
            report += f"- **File**: `{issue.file_path}:{issue.line}`\n"
            report += f"- **Description**: {issue.description}\n"
            report += "- **Code**:\n  ```python\n"
            report += f"  {issue.code_snippet}\n  ```\n"
            report += f"- **Fix**: {issue.suggested_fix}\n"
            report += f"- **Verification**: `{issue.verification}`\n\n"

        report += "\n## Medium Issues\n"
        for issue in [i for i in result.issues if i.severity == "MEDIUM"]:
            report += f"### {issue.rule_id}: {issue.rule_name}\n"
            report += f"- **File**: `{issue.file_path}:{issue.line}`\n"
            report += f"- **Description**: {issue.description}\n\n"

        report += "\n## Positive Observations\n"
        if result.positive_observations:
            for obs in result.positive_observations:
                report += f"- {obs}\n"
        else:
            report += "- No specific positive observations noted.\n"

        report += "\n## Scoring Calculation\n"
        report += "| Category | Raw Score | Deductions | Weighted |\n"
        report += "|----------|-----------|------------|----------|\n"
        for cat, val in cat_scores.items():
            report += f"| {cat} | 10 | - | {val:.1f} |\n"

        report_path = (
            self.reports_dir
            / f"{result.sector_id}-{result.sector_name.replace('+', '_').replace(' ', '_')}.md"
        )
        report_path.write_text(report, encoding="utf-8")

    def write_orchestrator_report(self, result: SectorResult) -> None:
        if not result.sub_results:
            return

        total_files = sum(s.files_reviewed for s in result.sub_results)
        weighted_score_sum = 0.0

        sub_reports_lines: list[str] = []
        all_crit: list[Issue] = []
        all_high: list[Issue] = []

        for sub in result.sub_results:
            score, _ = self.calculate_score(sub.issues)
            status = self.get_status(score)
            weight = sub.files_reviewed / max(1, total_files)
            weighted_score_sum += weight * score

            crit_c = sum(1 for i in sub.issues if i.severity == "CRITICAL")
            high_c = sum(1 for i in sub.issues if i.severity == "HIGH")

            sub_reports_lines.append(
                f"| {sub.sector_id} — {sub.sector_name} | {sub.files_reviewed} | "
                f"{score:.1f} | {status} | {crit_c} | {high_c} |"
            )

            all_crit.extend([i for i in sub.issues if i.severity == "CRITICAL"])
            all_high.extend([i for i in sub.issues if i.severity == "HIGH"])

        overall_status = self.get_status(weighted_score_sum)

        report = f"# Consolidated Review — {result.sector_id}: {result.sector_name}\n\n"
        report += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
        report += f"**Sub-reviews**: {len(result.sub_results)} agents\n"
        report += f"**Status**: {overall_status}\n"
        report += f"**Consolidated Score**: {weighted_score_sum:.1f}\n\n"
        report += "## Sub-review Summary\n"
        report += "| Sub-sector | Files | Score | Status | CRIT | HIGH |\n"
        report += "|------------|-------|-------|--------|------|------|\n"
        report += "\n".join(sub_reports_lines) + "\n\n"

        report += "## Aggregated Issues\n### Critical (MUST fix)\n"
        for i, issue in enumerate(all_crit[:20]):  # Limit to 20 for brevity
            report += f"{i + 1}. **{issue.rule_id}** in `{issue.file_path}:{issue.line}` - {issue.description}\n"
        report += "\n### High Issues\n"
        for i, issue in enumerate(all_high[:20]):
            report += f"{i + 1}. **{issue.rule_id}** in `{issue.file_path}:{issue.line}` - {issue.description}\n"

        report += "\n## Cross-subzone Observations\n"
        report += "- Needs manual review of sub-reports to identify cross-subzone patterns.\n"
        report += "\n## Top Recommendations\n"
        report += "1. Address CRITICAL issues in sub-reports immediately.\n"

        report_path = (
            self.reports_dir
            / f"{result.sector_id}-{result.sector_name.replace('+', '_').replace(' ', '_')}.md"
        )
        report_path.write_text(report, encoding="utf-8")

    def write_final_report(self, results: list[SectorResult]) -> None:
        total_files = sum(r.files_reviewed for r in results)
        total_loc = sum(r.total_loc for r in results)

        sector_weights = {
            "S1": 0.20,
            "S2": 0.20,
            "S3": 0.20,
            "S4": 0.10,
            "S5": 0.10,
            "S6": 0.08,
            "S7": 0.05,
            "S8": 0.07,
        }

        final_score = 0.0
        all_issues: list[Issue] = []
        sector_lines: list[str] = []

        for r in results:
            if r.is_orchestrator:
                total_f = sum(s.files_reviewed for s in r.sub_results)
                score = sum(
                    (s.files_reviewed / max(1, total_f))
                    * self.calculate_score(s.issues)[0]
                    for s in r.sub_results
                )
                all_issues.extend(r.all_issues)
            else:
                score, _ = self.calculate_score(r.issues)
                all_issues.extend(r.issues)

            status = self.get_status(score)
            weight = sector_weights.get(r.sector_id, 0.0)
            final_score += score * weight

            paths_str = ", ".join(r.scope_paths)
            sector_lines.append(
                f"| {r.sector_id} {r.sector_name} | {paths_str} | "
                f"{r.files_reviewed} | {r.total_loc} | {score:.1f} | {status} |"
            )

        overall_status = self.get_status(final_score)

        crit_issues = [i for i in all_issues if i.severity == "CRITICAL"]
        high_issues = [i for i in all_issues if i.severity == "HIGH"]
        med_issues = [i for i in all_issues if i.severity == "MEDIUM"]
        low_issues = [i for i in all_issues if i.severity == "LOW"]

        report = "# BioETL — Full Project Review Report\n\n"
        report += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
        report += f"**RULES.md Version**: {self._detect_rules_version()}\n"
        report += "**Project Version**: 1.0.0\n"
        report += f"**Total files reviewed**: {total_files}\n"
        report += f"**Total LOC reviewed**: {total_loc}\n\n"
        report += "---\n\n## Executive Summary\n"
        report += f"**Overall Status**: {overall_status}\n"
        report += f"**Overall Score**: {final_score:.1f}/10.0\n\n"
        report += "### Key Metrics\n"
        report += "| Metric | Value |\n|--------|-------|\n"
        report += f"| Total issues found | {len(all_issues)} |\n"
        report += f"| Critical issues | {len(crit_issues)} |\n"
        report += f"| High issues | {len(high_issues)} |\n"
        report += f"| Medium issues | {len(med_issues)} |\n"
        report += f"| Low issues | {len(low_issues)} |\n"
        report += f"| Sectors reviewed | {len(results)} |\n\n"

        report += "---\n\n## Sector Scores\n"
        report += "| Sector | Scope | Files | LOC | Score | Status |\n"
        report += "|--------|-------|-------|-----|-------|--------|\n"
        report += "\n".join(sector_lines) + "\n\n"

        report += "---\n\n## Critical Issues (блокируют merge/release)\n"
        for i, issue in enumerate(crit_issues[:50]):
            report += f"- **{issue.rule_id}**: {issue.file_path}:{issue.line} - {issue.description}\n"
        report += "\n---\n\n## High Issues\n"
        for i, issue in enumerate(high_issues[:20]):
            report += f"- **{issue.rule_id}**: {issue.file_path}:{issue.line} - {issue.description}\n"

        report += "\n---\n\n## Cross-cutting Analysis\n"
        report += "### Повторяющиеся паттерны\n"
        report += "Необходимо проанализировать индивидуальные отчеты для выявления паттернов.\n"

        report += "\n---\n\n## Recommendations (приоритизированные)\n"
        report += "### P1 — Немедленно (блокеры)\n"
        report += "1. Исправить все CRITICAL issues указанные выше.\n"

        report += "\n---\n\n## Positive Highlights\n"
        report += "Процесс ревью успешно автоматизирован.\n"

        report += "\n---\n\n## Verification Commands\n"
        report += "```bash\n"
        report += "pytest tests/architecture/ -v\n"
        report += "mypy src/bioetl/ --strict\n"
        report += "pytest --cov=src/bioetl --cov-fail-under=85\n"
        report += "make lint\n"
        report += "```\n"

        report_path = self.reports_dir / "FINAL-REVIEW.md"
        report_path.write_text(report, encoding="utf-8")

    def review_sector(
        self, sector: dict[str, Any], is_l3: bool = False
    ) -> SectorResult:
        sector_id = sector["id"]
        sector_name = sector["name"]
        paths = sector["paths"]

        file_exts = {".py"}
        if sector_id.startswith("S7"):
            file_exts = {".yaml", ".yml"}
        elif sector_id.startswith("S8"):
            file_exts = {".md"}

        total_files, total_loc, file_paths = self.count_files_and_loc(paths, file_exts)

        # Scaling threshold check
        threshold_files = 40
        if sector_id.startswith("S7"):
            threshold_files = 20
        elif sector_id.startswith("S8"):
            threshold_files = 30

        needs_delegation = not is_l3 and (
            total_files > threshold_files or total_loc > LOC_THRESHOLD
        )

        result = SectorResult(
            sector_id=sector_id,
            sector_name=sector_name,
            scope_paths=paths,
            files_reviewed=total_files,
            total_loc=total_loc,
        )

        if needs_delegation:
            # L2 Orchestrator mode
            subsectors = self.determine_subsectors(sector_id, paths)
            for sub in subsectors:
                sub_result = self.review_sector(sub, is_l3=True)
                result.sub_results.append(sub_result)
            self.write_orchestrator_report(result)
        else:
            # Worker mode
            for filepath in file_paths:
                if filepath.suffix == ".py":
                    issues = self.analyze_python_file(filepath, sector_id)
                    result.issues.extend(issues)
                elif filepath.suffix in (".yaml", ".yml"):
                    issues = self.analyze_yaml_file(filepath, sector_id)
                    result.issues.extend(issues)
                elif filepath.suffix == ".md":
                    issues = self.analyze_markdown_file(filepath, sector_id)
                    result.issues.extend(issues)
            self.write_worker_report(result)

        return result

    def run(self) -> None:
        print("Starting hierarchical code review...")
        final_results: list[SectorResult] = []
        for sector in self.sectors:
            print(f"Reviewing sector {sector['id']} ({sector['name']})...")
            res = self.review_sector(sector)
            final_results.append(res)
        self.write_final_report(final_results)
        print("Review complete. Reports generated in reports/review/")


if __name__ == "__main__":
    orchestrator = ReviewOrchestrator()
    orchestrator.run()
