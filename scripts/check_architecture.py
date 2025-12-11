#!/usr/bin/env python3
"""Check architectural boundaries in BioETL infrastructure layer.

This script verifies that the infrastructure layer follows the architectural
rules defined in src/bioetl/infrastructure/ARCHITECTURE.md:

1. Infrastructure must not import from application layer
2. Infrastructure must not import forbidden domain modules at module level
3. Infrastructure must only import from allowed domain modules

Usage:
    python scripts/check_architecture.py
    python scripts/check_architecture.py --format json
    python scripts/check_architecture.py --fix  # Show fix suggestions

Exit codes:
    0: All checks passed
    1: Violations detected
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass, field
import json
from pathlib import Path
import sys
from typing import Iterator, NamedTuple

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

INFRASTRUCTURE_ROOT = Path(__file__).parent.parent / "src" / "bioetl" / "infrastructure"
INFRASTRUCTURE_MODULE = "bioetl.infrastructure"
APPLICATION_MODULE = "bioetl.application"
DOMAIN_MODULE = "bioetl.domain"

# Forbidden imports from infrastructure layer with reasons
# Format: {module_prefix: reason}
FORBIDDEN_IMPORTS = {
    "bioetl.domain.schemas.chembl.raw_models": (
        "Use application layer mappers or TYPE_CHECKING imports"
    ),
    "bioetl.domain.schemas.pipeline_contracts": (
        "Use SchemaContractProviderABC port instead"
    ),
    "bioetl.application": "Infrastructure must not import application layer",
}

# Allowed domain imports - infrastructure layer can only import from these
ALLOWED_DOMAIN_IMPORTS = frozenset(
    {
        # Ports and contracts
        "bioetl.domain.ports",
        "bioetl.domain.configs",
        "bioetl.domain.errors",
        "bioetl.domain.observability",
        "bioetl.domain.clients.base.contracts",
        "bioetl.domain.clients.contracts",
        "bioetl.domain.validation",
        "bioetl.domain.models",
        # Transform utilities (allowed for infrastructure)
        "bioetl.domain.transform.contracts",
        "bioetl.domain.transform.merge",
        "bioetl.domain.transform.normalizers",
        "bioetl.domain.transform.serializers",
        # Pipeline contracts
        "bioetl.domain.pipelines.contracts",
        # Provider registry
        "bioetl.domain.provider_registry",
        "bioetl.domain.providers",
        # Other allowed domain modules
        "bioetl.domain.types",
        "bioetl.domain.enums",
        "bioetl.domain.services",
        "bioetl.domain.transform",
        "bioetl.domain.clients",
        "bioetl.domain.pipelines",
        "bioetl.domain.record_source",
        # Data structures and value objects
        "bioetl.domain.data",
        "bioetl.domain.value_objects",
        # Schema utilities (field specs, NOT raw_models)
        "bioetl.domain.schemas",
        "bioetl.domain.schemas.field_specs",
    }
)

# Files that are allowed to violate rules (documented exceptions)
# Format: relative path from project root -> set of allowed forbidden imports
ALLOWED_EXCEPTIONS: dict[str, set[str]] = {
    # Deprecated shim re-exporting from application for backward compatibility
    "src/bioetl/infrastructure/files/csv_record_source.py": {
        "bioetl.application",
    },
    # EntityModelRegistry needs runtime access to domain models for registration
    # This is an intentional coupling point - registry pattern requires model access
    "src/bioetl/infrastructure/chembl/model_registry.py": {
        "bioetl.domain.schemas.chembl.raw_models",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# Data Structures
# ─────────────────────────────────────────────────────────────────────────────


class ImportInfo(NamedTuple):
    """Information about a single import statement."""

    module: str
    lineno: int
    in_type_checking: bool
    is_lazy: bool  # Import inside function/method body


@dataclass
class Violation:
    """A single architectural violation."""

    file: Path
    line: int
    message: str
    import_path: str
    fix_suggestion: str | None = None


@dataclass
class ArchitectureReport:
    """Complete architecture analysis report."""

    violations: list[Violation] = field(default_factory=list)
    modules_analyzed: int = 0
    total_imports: int = 0
    parse_errors: list[dict] = field(default_factory=list)

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)


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


def find_python_files(root: Path) -> Iterator[Path]:
    """Recursively find all Python files under root."""
    for path in root.rglob("*.py"):
        yield path


def analyze_file(path: Path) -> tuple[list[ImportInfo], str | None]:
    """Analyze a single Python file for imports."""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except SyntaxError as e:
        return [], f"SyntaxError: {e}"
    except Exception as e:
        return [], str(e)

    visitor = ImportVisitor()
    visitor.visit(tree)
    return visitor.imports, None


def _is_forbidden_import(module: str) -> tuple[bool, str | None]:
    """Check if an import is explicitly forbidden. Returns (is_forbidden, reason)."""
    for forbidden, reason in FORBIDDEN_IMPORTS.items():
        if module == forbidden or module.startswith(forbidden + "."):
            return True, reason
    return False, None


def _is_domain_import_allowed(module: str) -> bool:
    """Check if a domain import is in the allowed list."""
    # Check exact match
    if module in ALLOWED_DOMAIN_IMPORTS:
        return True

    # Check if it's a submodule of an allowed import
    for allowed in ALLOWED_DOMAIN_IMPORTS:
        if module.startswith(allowed + "."):
            return True

    return False


def _get_fix_suggestion(module: str) -> str | None:
    """Get fix suggestion for a violation."""
    if module.startswith("bioetl.domain.schemas.chembl.raw_models"):
        return "Move import into TYPE_CHECKING block or use lazy import inside function"
    if module.startswith("bioetl.domain.schemas.pipeline_contracts"):
        return "Use SchemaContractProviderABC port via dependency injection"
    if module.startswith("bioetl.application"):
        return "Remove application layer dependency; use ports/contracts instead"
    if module.startswith("bioetl.domain.schemas"):
        return "Consider using TYPE_CHECKING block or add to ALLOWED_DOMAIN_IMPORTS"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Violation Detection
# ─────────────────────────────────────────────────────────────────────────────


def _is_exception_allowed(relative_path: str, module: str) -> bool:
    """Check if this import is in the allowed exceptions list."""
    allowed_modules = ALLOWED_EXCEPTIONS.get(relative_path, set())
    for allowed in allowed_modules:
        if module == allowed or module.startswith(allowed + "."):
            return True
    return False


def check_file(path: Path, src_root: Path) -> list[Violation]:
    """Check a single file for architectural violations."""
    violations: list[Violation] = []
    imports, error = analyze_file(path)

    if error:
        # Skip files with parse errors (will be reported separately)
        return violations

    relative_path = path.relative_to(src_root)
    relative_path_str = str(relative_path).replace("\\", "/")  # Normalize for Windows

    for imp in imports:
        # Skip TYPE_CHECKING imports (always allowed)
        if imp.in_type_checking:
            continue

        # Skip lazy imports inside functions (allowed for backward compatibility)
        if imp.is_lazy:
            continue

        # Check if this import is in allowed exceptions (deprecated shims)
        if _is_exception_allowed(relative_path_str, imp.module):
            continue

        # Check forbidden imports (application layer, specific domain modules)
        is_forbidden, reason = _is_forbidden_import(imp.module)
        if is_forbidden:
            violations.append(
                Violation(
                    file=path,
                    line=imp.lineno,
                    message=f"Forbidden import: {reason}",
                    import_path=imp.module,
                    fix_suggestion=_get_fix_suggestion(imp.module),
                )
            )
            continue

        # Check domain imports are in allowed list
        if imp.module.startswith(DOMAIN_MODULE):
            if not _is_domain_import_allowed(imp.module):
                violations.append(
                    Violation(
                        file=path,
                        line=imp.lineno,
                        message="Domain import not in allowed list",
                        import_path=imp.module,
                        fix_suggestion=_get_fix_suggestion(imp.module),
                    )
                )

    return violations


# ─────────────────────────────────────────────────────────────────────────────
# Report Generation
# ─────────────────────────────────────────────────────────────────────────────


def generate_report() -> ArchitectureReport:
    """Generate a complete architecture analysis report."""
    report = ArchitectureReport()

    if not INFRASTRUCTURE_ROOT.exists():
        print(f"Error: Infrastructure root not found: {INFRASTRUCTURE_ROOT}")
        return report

    src_root = INFRASTRUCTURE_ROOT.parent.parent.parent

    for path in find_python_files(INFRASTRUCTURE_ROOT):
        report.modules_analyzed += 1

        imports, error = analyze_file(path)
        report.total_imports += len(imports)

        if error:
            relative_path = path.relative_to(src_root)
            report.parse_errors.append({"file": str(relative_path), "error": error})
            continue

        violations = check_file(path, src_root)
        report.violations.extend(violations)

    return report


def format_json_report(report: ArchitectureReport) -> dict:
    """Format report as JSON-serializable dict."""
    src_root = INFRASTRUCTURE_ROOT.parent.parent.parent

    violations_json = [
        {
            "file": str(v.file.relative_to(src_root)),
            "line": v.line,
            "message": v.message,
            "import": v.import_path,
            "fix": v.fix_suggestion,
        }
        for v in report.violations
    ]

    return {
        "status": "ok" if not report.has_violations else "error",
        "violations": violations_json,
        "metadata": {
            "modules_analyzed": report.modules_analyzed,
            "total_imports": report.total_imports,
            "parse_errors": report.parse_errors,
        },
    }


def print_text_report(report: ArchitectureReport, show_fix: bool = False) -> None:
    """Print a human-readable text report."""
    print("=" * 70)
    print("INFRASTRUCTURE LAYER ARCHITECTURE CHECK")
    print("=" * 70)

    print(f"\nModules analyzed: {report.modules_analyzed}")
    print(f"Total imports: {report.total_imports}")

    # Parse errors
    if report.parse_errors:
        print(f"\n[!] Parse Errors ({len(report.parse_errors)}):")
        for err in report.parse_errors:
            print(f"  - {err['file']}: {err['error']}")

    src_root = INFRASTRUCTURE_ROOT.parent.parent.parent

    # Violations
    if report.violations:
        print(f"\n[X] VIOLATIONS FOUND ({len(report.violations)}):\n")
        for v in report.violations:
            relative_path = v.file.relative_to(src_root)
            print(f"  {relative_path}:{v.line}")
            print(f"    Import: {v.import_path}")
            print(f"    Reason: {v.message}")
            if show_fix and v.fix_suggestion:
                print(f"    Fix: {v.fix_suggestion}")
            print()
    else:
        print("\n[OK] No architectural violations found")

    print("=" * 70)
    if report.has_violations:
        print("RESULT: [X] FAIL - Violations detected")
    else:
        print("RESULT: [OK] PASS - All checks passed")
    print("=" * 70)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check architectural boundaries in BioETL infrastructure layer"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Show fix suggestions for violations",
    )
    args = parser.parse_args()

    report = generate_report()

    if args.format == "json":
        print(json.dumps(format_json_report(report), indent=2))
    else:
        print_text_report(report, show_fix=args.fix)

    return 1 if report.has_violations else 0


if __name__ == "__main__":
    sys.exit(main())
