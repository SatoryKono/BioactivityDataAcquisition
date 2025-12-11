#!/usr/bin/env python3
"""
Dependency graph validator for bioetl.application layer.

This script analyzes imports within the application layer to:
1. Build a dependency graph between submodules
2. Detect cyclic dependencies (via topological sort)
3. Verify no module-level imports from infrastructure (only TYPE_CHECKING allowed)
4. Output a detailed JSON report

Usage:
    python scripts/check_application_deps.py [--json] [--mermaid] [--strict]

Exit codes:
    0: All checks passed
    1: Dependency violations detected
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, NamedTuple


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

APPLICATION_ROOT = Path(__file__).parent.parent / "src" / "bioetl" / "application"
APPLICATION_MODULE = "bioetl.application"
INFRASTRUCTURE_MODULE = "bioetl.infrastructure"

# Top-level submodules in application layer
SUBMODULES = frozenset(
    {
        "bootstrap",
        "config",
        "container",
        "contracts",
        "executor",
        "factories",
        "files",
        "helpers",
        "mappers",
        "memory_registry",
        "orchestrator",
        "pipelines",
        "providers",
        "services",
        "sources",
        "transform",
        "use_cases",
    }
)

# Known exceptions for infrastructure imports (documented in .importlinter)
# These are legacy exceptions that should be tracked and eventually removed
ALLOWED_INFRASTRUCTURE_IMPORTS: set[tuple[str, str]] = {
    # Format: (source_module, infrastructure_module)
    # Add exceptions here only if they are documented and approved
}


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────


class ImportInfo(NamedTuple):
    """Information about a single import statement."""

    module: str
    lineno: int
    in_type_checking: bool
    is_lazy: bool  # Import inside function/method body


@dataclass
class ModuleAnalysis:
    """Analysis result for a single Python module."""

    path: Path
    relative_path: str
    submodule: str
    imports: list[ImportInfo] = field(default_factory=list)
    infrastructure_imports: list[ImportInfo] = field(default_factory=list)
    application_imports: list[ImportInfo] = field(default_factory=list)
    parse_error: str | None = None


@dataclass
class DependencyReport:
    """Complete dependency analysis report."""

    # Graph data
    submodule_graph: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    all_edges: list[tuple[str, str, str]] = field(default_factory=list)  # (from, to, file)

    # Violations
    cycles: list[list[str]] = field(default_factory=list)
    infrastructure_violations: list[dict] = field(default_factory=list)

    # Metadata
    modules_analyzed: int = 0
    total_imports: int = 0
    parse_errors: list[dict] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return bool(self.cycles or self.infrastructure_violations)


# ─────────────────────────────────────────────────────────────────────────────
# AST Analysis
# ─────────────────────────────────────────────────────────────────────────────


class ImportVisitor(ast.NodeVisitor):
    """AST visitor that extracts import information."""

    def __init__(self) -> None:
        self.imports: list[ImportInfo] = []
        self._in_type_checking = False
        self._in_function = False

    def visit_If(self, node: ast.If) -> None:
        """Detect TYPE_CHECKING blocks."""
        is_type_checking = self._is_type_checking_block(node)
        if is_type_checking:
            old_state = self._in_type_checking
            self._in_type_checking = True
            self.generic_visit(node)
            self._in_type_checking = old_state
        else:
            self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Track function scope for lazy imports."""
        old_state = self._in_function
        self._in_function = True
        self.generic_visit(node)
        self._in_function = old_state

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import x' statements."""
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    lineno=node.lineno,
                    in_type_checking=self._in_type_checking,
                    is_lazy=self._in_function,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from x import y' statements."""
        if node.module:
            self.imports.append(
                ImportInfo(
                    module=node.module,
                    lineno=node.lineno,
                    in_type_checking=self._in_type_checking,
                    is_lazy=self._in_function,
                )
            )

    @staticmethod
    def _is_type_checking_block(node: ast.If) -> bool:
        """Check if this is an 'if TYPE_CHECKING:' block."""
        test = node.test
        # Direct: if TYPE_CHECKING:
        if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
            return True
        # Attribute: if typing.TYPE_CHECKING:
        if (
            isinstance(test, ast.Attribute)
            and test.attr == "TYPE_CHECKING"
            and isinstance(test.value, ast.Name)
        ):
            return True
        return False


def analyze_module(path: Path) -> ModuleAnalysis:
    """Analyze a single Python module for imports."""
    relative = path.relative_to(APPLICATION_ROOT.parent.parent.parent)
    submodule = _get_submodule(path)

    analysis = ModuleAnalysis(
        path=path,
        relative_path=str(relative),
        submodule=submodule,
    )

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as e:
        analysis.parse_error = f"SyntaxError: {e}"
        return analysis
    except Exception as e:
        analysis.parse_error = str(e)
        return analysis

    visitor = ImportVisitor()
    visitor.visit(tree)
    analysis.imports = visitor.imports

    # Categorize imports
    for imp in analysis.imports:
        if imp.module.startswith(INFRASTRUCTURE_MODULE):
            analysis.infrastructure_imports.append(imp)
        elif imp.module.startswith(APPLICATION_MODULE):
            analysis.application_imports.append(imp)

    return analysis


def _get_submodule(path: Path) -> str:
    """Extract the top-level submodule name from a file path."""
    try:
        rel = path.relative_to(APPLICATION_ROOT)
        parts = rel.parts
        if not parts:
            return "__init__"
        first = parts[0]
        # Handle .py files at root
        if first.endswith(".py"):
            return first[:-3]
        return first
    except ValueError:
        return "unknown"


def _extract_target_submodule(import_module: str) -> str | None:
    """Extract the target submodule from an import path."""
    if not import_module.startswith(APPLICATION_MODULE):
        return None
    rest = import_module[len(APPLICATION_MODULE) :]
    if not rest:
        return "__init__"
    if rest.startswith("."):
        rest = rest[1:]
    parts = rest.split(".")
    if not parts or not parts[0]:
        return "__init__"
    return parts[0]


# ─────────────────────────────────────────────────────────────────────────────
# Graph Analysis
# ─────────────────────────────────────────────────────────────────────────────


def find_python_files(root: Path) -> Iterator[Path]:
    """Recursively find all Python files under root."""
    for path in root.rglob("*.py"):
        yield path


def build_dependency_graph(analyses: list[ModuleAnalysis]) -> dict[str, set[str]]:
    """Build a dependency graph from module analyses."""
    graph: dict[str, set[str]] = defaultdict(set)

    # Initialize all known submodules
    for submodule in SUBMODULES:
        graph[submodule]  # noqa: B018 - intentional access to create key

    for analysis in analyses:
        source = analysis.submodule
        for imp in analysis.application_imports:
            target = _extract_target_submodule(imp.module)
            if target and target != source and target in SUBMODULES:
                graph[source].add(target)

    return dict(graph)


def detect_cycles(graph: dict[str, set[str]]) -> list[list[str]]:
    """Detect cycles in the dependency graph using DFS."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {node: WHITE for node in graph}
    path: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node: str) -> None:
        color[node] = GRAY
        path.append(node)

        for neighbor in graph.get(node, set()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Found a cycle - extract it from path
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:] + [neighbor]
                cycles.append(cycle)
            elif color[neighbor] == WHITE:
                dfs(neighbor)

        path.pop()
        color[node] = BLACK

    for node in graph:
        if color[node] == WHITE:
            dfs(node)

    return cycles


def topological_sort(graph: dict[str, set[str]]) -> list[str] | None:
    """
    Perform topological sort on the graph.

    Returns sorted list if no cycles, None otherwise.
    """
    in_degree: dict[str, int] = {node: 0 for node in graph}

    for node in graph:
        for neighbor in graph[node]:
            if neighbor in in_degree:
                in_degree[neighbor] += 1

    queue = [node for node, degree in in_degree.items() if degree == 0]
    result: list[str] = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for neighbor in graph.get(node, set()):
            if neighbor in in_degree:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

    if len(result) != len(graph):
        return None  # Cycle detected
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Violation Detection
# ─────────────────────────────────────────────────────────────────────────────


def check_infrastructure_imports(
    analyses: list[ModuleAnalysis], strict: bool = False
) -> list[dict]:
    """Check for forbidden infrastructure imports at module level."""
    violations: list[dict] = []

    for analysis in analyses:
        for imp in analysis.infrastructure_imports:
            # Skip TYPE_CHECKING imports
            if imp.in_type_checking:
                continue

            # Skip lazy imports (inside functions)
            if imp.is_lazy:
                continue

            # Check if this is an allowed exception
            exception_key = (analysis.relative_path, imp.module)
            if not strict and exception_key in ALLOWED_INFRASTRUCTURE_IMPORTS:
                continue

            violations.append(
                {
                    "file": analysis.relative_path,
                    "line": imp.lineno,
                    "import": imp.module,
                    "submodule": analysis.submodule,
                    "reason": "Module-level import from infrastructure "
                    "(should use TYPE_CHECKING or lazy import)",
                }
            )

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Report Generation
# ─────────────────────────────────────────────────────────────────────────────


def generate_report(strict: bool = False) -> DependencyReport:
    """Generate a complete dependency analysis report."""
    report = DependencyReport()

    # Find and analyze all modules
    analyses: list[ModuleAnalysis] = []
    for path in find_python_files(APPLICATION_ROOT):
        analysis = analyze_module(path)
        analyses.append(analysis)

        if analysis.parse_error:
            report.parse_errors.append(
                {"file": analysis.relative_path, "error": analysis.parse_error}
            )

        report.total_imports += len(analysis.imports)

    report.modules_analyzed = len(analyses)

    # Build dependency graph
    report.submodule_graph = build_dependency_graph(analyses)

    # Collect all edges with file info
    for analysis in analyses:
        source = analysis.submodule
        for imp in analysis.application_imports:
            target = _extract_target_submodule(imp.module)
            if target and target != source and target in SUBMODULES:
                report.all_edges.append((source, target, analysis.relative_path))

    # Detect cycles
    report.cycles = detect_cycles(dict(report.submodule_graph))

    # Check infrastructure imports
    report.infrastructure_violations = check_infrastructure_imports(analyses, strict)

    return report


def format_json_report(report: DependencyReport) -> dict:
    """Format report as JSON-serializable dict."""
    # Convert sets to sorted lists for JSON
    graph_json = {k: sorted(v) for k, v in report.submodule_graph.items()}

    return {
        "status": "FAIL" if report.has_violations else "PASS",
        "summary": {
            "modules_analyzed": report.modules_analyzed,
            "total_imports": report.total_imports,
            "submodules": len(report.submodule_graph),
            "cycle_count": len(report.cycles),
            "infrastructure_violation_count": len(report.infrastructure_violations),
            "parse_error_count": len(report.parse_errors),
        },
        "dependency_graph": graph_json,
        "cycles": report.cycles,
        "infrastructure_violations": report.infrastructure_violations,
        "parse_errors": report.parse_errors,
        "topological_order": topological_sort(dict(report.submodule_graph)),
    }


def generate_mermaid(report: DependencyReport) -> str:
    """Generate a Mermaid flowchart from the dependency graph."""
    lines = ["flowchart TD"]

    # Collect all edges
    edges: set[tuple[str, str]] = set()
    for source, targets in report.submodule_graph.items():
        for target in targets:
            edges.add((source, target))

    # Sort for consistent output
    for source, target in sorted(edges):
        lines.append(f"    {source} --> {target}")

    # Add styling for special modules
    lines.append("")
    lines.append("    %% Core modules")
    lines.append("    style container fill:#f9f,stroke:#333")
    lines.append("    style orchestrator fill:#bbf,stroke:#333")
    lines.append("    style bootstrap fill:#bfb,stroke:#333")

    return "\n".join(lines)


def print_text_report(report: DependencyReport) -> None:
    """Print a human-readable text report."""
    print("=" * 70)
    print("APPLICATION LAYER DEPENDENCY ANALYSIS")
    print("=" * 70)

    print(f"\nModules analyzed: {report.modules_analyzed}")
    print(f"Total imports: {report.total_imports}")
    print(f"Submodules: {len(report.submodule_graph)}")

    # Parse errors
    if report.parse_errors:
        print(f"\n⚠️  Parse Errors ({len(report.parse_errors)}):")
        for err in report.parse_errors:
            print(f"  - {err['file']}: {err['error']}")

    # Cycles
    if report.cycles:
        print(f"\n❌ CYCLES DETECTED ({len(report.cycles)}):")
        for cycle in report.cycles:
            print(f"  - {' -> '.join(cycle)}")
    else:
        print("\n✅ No cyclic dependencies detected")

    # Topological order
    topo_order = topological_sort(dict(report.submodule_graph))
    if topo_order:
        print(f"\nTopological order: {' -> '.join(topo_order)}")

    # Infrastructure violations
    if report.infrastructure_violations:
        print(f"\n❌ INFRASTRUCTURE IMPORT VIOLATIONS ({len(report.infrastructure_violations)}):")
        for v in report.infrastructure_violations:
            print(f"  - {v['file']}:{v['line']}")
            print(f"    Import: {v['import']}")
            print(f"    Reason: {v['reason']}")
    else:
        print("\n✅ No forbidden infrastructure imports at module level")

    # Dependency graph
    print("\nDependency Graph (submodule -> dependencies):")
    for submodule in sorted(report.submodule_graph.keys()):
        deps = report.submodule_graph[submodule]
        if deps:
            print(f"  {submodule} -> {', '.join(sorted(deps))}")
        else:
            print(f"  {submodule} -> (none)")

    print("\n" + "=" * 70)
    if report.has_violations:
        print("RESULT: ❌ FAIL - Violations detected")
    else:
        print("RESULT: ✅ PASS - All checks passed")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check dependency graph for bioetl.application layer"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output report as JSON",
    )
    parser.add_argument(
        "--mermaid",
        action="store_true",
        help="Output Mermaid diagram only",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Strict mode: fail on any infrastructure import (ignore exceptions)",
    )
    args = parser.parse_args()

    report = generate_report(strict=args.strict)

    if args.mermaid:
        print(generate_mermaid(report))
        return 0

    if args.json:
        print(json.dumps(format_json_report(report), indent=2))
    else:
        print_text_report(report)

    return 1 if report.has_violations else 0


if __name__ == "__main__":
    sys.exit(main())
