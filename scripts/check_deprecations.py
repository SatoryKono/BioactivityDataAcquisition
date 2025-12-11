#!/usr/bin/env python3
"""Scan codebase for usage of deprecated imports.

This script scans Python source files for imports of deprecated names
from the bioetl.domain layer and generates a migration report.

Usage:
    python scripts/check_deprecations.py [--path PATH] [--format FORMAT] [--strict]

Options:
    --path PATH      Root directory to scan (default: src/)
    --format FORMAT  Output format: text, json, markdown (default: text)
    --strict         Exit with code 1 if any deprecated usages found
    --exclude GLOB   Glob pattern for files to exclude (can be repeated)
    --include-tests  Include test files in the scan

Examples:
    # Basic scan of source directory
    python scripts/check_deprecations.py

    # Scan with markdown report
    python scripts/check_deprecations.py --format markdown

    # Strict mode for CI
    python scripts/check_deprecations.py --strict

    # Include tests
    python scripts/check_deprecations.py --include-tests --path .
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

# Add src to path for importing deprecations registry
SRC_PATH = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC_PATH))

# Import directly from _deprecations to avoid loading full domain (which requires pydantic)
# We use importlib to import just this module without triggering bioetl.domain.__init__
import importlib.util

_deprecations_path = SRC_PATH / "bioetl" / "domain" / "_deprecations.py"
spec = importlib.util.spec_from_file_location("_deprecations", _deprecations_path)
_deprecations = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(_deprecations)  # type: ignore[union-attr]

DEPRECATED_ALIASES: dict[str, "DeprecatedAlias"] = _deprecations.DEPRECATED_ALIASES
DeprecatedAlias = _deprecations.DeprecatedAlias


@dataclass
class DeprecatedUsage:
    """Record of a deprecated name usage."""

    file_path: Path
    line_number: int
    deprecated_name: str
    import_statement: str
    alias: DeprecatedAlias

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "file": str(self.file_path),
            "line": self.line_number,
            "name": self.deprecated_name,
            "statement": self.import_statement,
            "replacement": self.alias.new_name,
            "new_module": self.alias.new_module,
            "category": self.alias.category,
        }


@dataclass
class ScanResult:
    """Result of scanning the codebase."""

    usages: list[DeprecatedUsage] = field(default_factory=list)
    files_scanned: int = 0
    files_with_issues: set[Path] = field(default_factory=set)

    @property
    def total_usages(self) -> int:
        return len(self.usages)

    @property
    def files_affected(self) -> int:
        return len(self.files_with_issues)

    def by_deprecated_name(self) -> dict[str, list[DeprecatedUsage]]:
        """Group usages by deprecated name."""
        result: dict[str, list[DeprecatedUsage]] = defaultdict(list)
        for usage in self.usages:
            result[usage.deprecated_name].append(usage)
        return dict(result)

    def by_file(self) -> dict[Path, list[DeprecatedUsage]]:
        """Group usages by file."""
        result: dict[Path, list[DeprecatedUsage]] = defaultdict(list)
        for usage in self.usages:
            result[usage.file_path].append(usage)
        return dict(result)


class DeprecationScanner:
    """Scanner for deprecated import usages."""

    # Modules that export deprecated names
    DEPRECATED_MODULES = {
        "bioetl.domain.types",
        "bioetl.domain.ports",
        "bioetl.domain.ports.extraction",
        "bioetl.domain.record_source",
        "bioetl.domain",
    }

    def __init__(
        self,
        root_path: Path,
        exclude_patterns: list[str] | None = None,
        include_tests: bool = False,
    ):
        self.root_path = root_path
        self.exclude_patterns = exclude_patterns or []
        self.include_tests = include_tests

    def iter_python_files(self) -> Iterator[Path]:
        """Iterate over Python files to scan."""
        for path in self.root_path.rglob("*.py"):
            # Skip __pycache__ and .git
            if "__pycache__" in path.parts or ".git" in path.parts:
                continue

            # Skip test files unless explicitly included
            if not self.include_tests and "test" in path.parts:
                continue

            # Skip _deprecations.py itself and this script
            if path.name == "_deprecations.py":
                continue
            if path.name == "check_deprecations.py":
                continue

            # Apply exclude patterns
            path_str = str(path)
            if any(pattern in path_str for pattern in self.exclude_patterns):
                continue

            yield path

    def scan_file(self, file_path: Path) -> list[DeprecatedUsage]:
        """Scan a single file for deprecated imports."""
        usages: list[DeprecatedUsage] = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError) as e:
            print(f"Warning: Could not parse {file_path}: {e}", file=sys.stderr)
            return usages

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                usages.extend(self._check_import_from(node, file_path, source))
            elif isinstance(node, ast.Import):
                usages.extend(self._check_import(node, file_path, source))

        return usages

    # Names that are NOT deprecated when imported from these canonical modules
    CANONICAL_LOCATIONS = {
        "RecordBatch": {"bioetl.domain.data"},
        "SourceRecordModel": {"bioetl.domain.record_source"},
        "RecordSourceABC": {"bioetl.domain.record_source"},
        "ApiPayload": {"bioetl.domain.types"},
    }

    def _check_import_from(
        self, node: ast.ImportFrom, file_path: Path, source: str
    ) -> list[DeprecatedUsage]:
        """Check 'from X import Y' statements."""
        usages: list[DeprecatedUsage] = []

        if node.module is None:
            return usages

        # Check if importing from a module that has deprecated exports
        module = node.module
        if not any(module.startswith(m) for m in self.DEPRECATED_MODULES):
            return usages

        for alias in node.names:
            name = alias.name
            if name in DEPRECATED_ALIASES:
                # Skip if importing from canonical location
                canonical_modules = self.CANONICAL_LOCATIONS.get(name, set())
                if module in canonical_modules:
                    continue

                # Get the source line
                lines = source.splitlines()
                line_text = lines[node.lineno - 1] if node.lineno <= len(lines) else ""

                usages.append(
                    DeprecatedUsage(
                        file_path=file_path,
                        line_number=node.lineno,
                        deprecated_name=name,
                        import_statement=line_text.strip(),
                        alias=DEPRECATED_ALIASES[name],
                    )
                )

        return usages

    def _check_import(
        self, node: ast.Import, file_path: Path, source: str
    ) -> list[DeprecatedUsage]:
        """Check 'import X' statements.

        This is less common for deprecated names but included for completeness.
        """
        # Direct imports of deprecated names are rare in this codebase
        return []

    def scan(self) -> ScanResult:
        """Scan all files and return results."""
        result = ScanResult()

        for file_path in self.iter_python_files():
            result.files_scanned += 1
            usages = self.scan_file(file_path)
            if usages:
                result.usages.extend(usages)
                result.files_with_issues.add(file_path)

        return result


def _make_relative(path: Path) -> Path:
    """Make path relative to cwd if possible, otherwise return as-is."""
    cwd = Path.cwd()
    try:
        return path.relative_to(cwd)
    except ValueError:
        return path


def format_text(result: ScanResult) -> str:
    """Format results as plain text."""
    lines: list[str] = []

    lines.append("=" * 70)
    lines.append("DEPRECATED IMPORTS SCAN REPORT")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"Files scanned:     {result.files_scanned}")
    lines.append(f"Files with issues: {result.files_affected}")
    lines.append(f"Total usages:      {result.total_usages}")
    lines.append("")

    if not result.usages:
        lines.append("No deprecated imports found!")
        return "\n".join(lines)

    # Group by deprecated name
    lines.append("-" * 70)
    lines.append("USAGES BY DEPRECATED NAME")
    lines.append("-" * 70)

    for name, usages in sorted(result.by_deprecated_name().items()):
        alias = DEPRECATED_ALIASES[name]
        lines.append("")
        lines.append(f"  {name} ({len(usages)} occurrences)")
        lines.append(f"    → Replace with: {alias.new_name}")
        lines.append(f"    → From module:  {alias.new_module}")
        lines.append("")
        for usage in usages:
            rel_path = _make_relative(usage.file_path)
            lines.append(f"      {rel_path}:{usage.line_number}")
            lines.append(f"        {usage.import_statement}")

    # Summary by file
    lines.append("")
    lines.append("-" * 70)
    lines.append("AFFECTED FILES")
    lines.append("-" * 70)
    lines.append("")

    for file_path, usages in sorted(result.by_file().items()):
        rel_path = _make_relative(file_path)
        names = sorted(set(u.deprecated_name for u in usages))
        lines.append(f"  {rel_path}")
        lines.append(f"    Uses: {', '.join(names)}")

    return "\n".join(lines)


def format_markdown(result: ScanResult) -> str:
    """Format results as Markdown."""
    lines: list[str] = []

    lines.append("# Deprecated Imports Scan Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Files scanned:** {result.files_scanned}")
    lines.append(f"- **Files with issues:** {result.files_affected}")
    lines.append(f"- **Total usages:** {result.total_usages}")
    lines.append("")

    if not result.usages:
        lines.append("**No deprecated imports found!**")
        return "\n".join(lines)

    # Table of deprecated names
    lines.append("## Deprecated Names Found")
    lines.append("")
    lines.append("| Deprecated | Occurrences | Replacement | New Module |")
    lines.append("|------------|-------------|-------------|------------|")

    for name, usages in sorted(result.by_deprecated_name().items()):
        alias = DEPRECATED_ALIASES[name]
        lines.append(
            f"| `{name}` | {len(usages)} | `{alias.new_name}` | `{alias.new_module}` |"
        )

    lines.append("")
    lines.append("## Detailed Locations")
    lines.append("")

    for name, usages in sorted(result.by_deprecated_name().items()):
        alias = DEPRECATED_ALIASES[name]
        lines.append(f"### `{name}`")
        lines.append("")
        lines.append(f"**Replace with:** `{alias.new_name}` from `{alias.new_module}`")
        lines.append("")

        for usage in usages:
            rel_path = _make_relative(usage.file_path)
            lines.append(f"- `{rel_path}:{usage.line_number}`")
            lines.append(f"  ```python")
            lines.append(f"  {usage.import_statement}")
            lines.append(f"  ```")

        lines.append("")

    return "\n".join(lines)


def format_json(result: ScanResult) -> str:
    """Format results as JSON."""
    data = {
        "summary": {
            "files_scanned": result.files_scanned,
            "files_with_issues": result.files_affected,
            "total_usages": result.total_usages,
        },
        "usages": [u.to_dict() for u in result.usages],
        "by_name": {
            name: [u.to_dict() for u in usages]
            for name, usages in result.by_deprecated_name().items()
        },
    }
    return json.dumps(data, indent=2)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Scan codebase for deprecated import usages."
    )
    parser.add_argument(
        "--path",
        type=lambda p: Path(p).resolve(),
        default=Path("src").resolve(),
        help="Root directory to scan (default: src/)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if deprecated usages found",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        dest="exclude_patterns",
        help="Patterns to exclude (can be repeated)",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files in the scan",
    )

    args = parser.parse_args()

    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        return 1

    # Run scanner
    scanner = DeprecationScanner(
        root_path=args.path,
        exclude_patterns=args.exclude_patterns,
        include_tests=args.include_tests,
    )
    result = scanner.scan()

    # Format output
    if args.format == "json":
        output = format_json(result)
    elif args.format == "markdown":
        output = format_markdown(result)
    else:
        output = format_text(result)

    print(output)

    # Return code for CI
    if args.strict and result.total_usages > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
