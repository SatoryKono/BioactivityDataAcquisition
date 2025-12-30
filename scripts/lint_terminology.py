#!/usr/bin/env python3
"""Terminology linter for BioETL Ubiquitous Language.

Validates that code uses canonical terminology as defined in docs/glossary.md.
This script is part of the code quality CI pipeline.

Usage:
    python scripts/lint_terminology.py src/bioetl/
    python scripts/lint_terminology.py --strict src/bioetl/domain/

Exit codes:
    0: No violations found
    1: Violations found or error occurred
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TermViolation:
    """Represents a terminology violation."""

    file: Path
    line_num: int
    deprecated_term: str
    canonical_term: str
    context: str


# Deprecated terms and their canonical replacements
# Format: {pattern: (canonical_term, description)}
# Based on docs/glossary.md "Deprecated Terms" section
DEPRECATED_TERMS: dict[str, tuple[str, str]] = {
    # Generic technical names (class definitions)
    r"class\s+\w*Loader\b": ("Adapter/Writer", "Use Adapter for input, Writer for output"),
    r"class\s+\w*Handler\b": ("Manager/Service", "Use specific names like Manager or Service"),
    # ETL process terms
    r"\bworkflow\b": ("pipeline", "Use 'pipeline' for data processing sequences"),
    r"\bjob\b": ("run", "Use 'run' for pipeline execution instances"),
    r"\bchunk\b": ("batch", "Use 'batch' for collections of records processed together"),
    # Data terms (when used as class/variable names, not in strings/comments)
    r"\bdata_point\b": ("record", "Use 'record' for data items"),
    # Domain terms (per glossary.md)
    r"class\s+\w*Workflow\b": ("Pipeline", "Use Pipeline for data processing sequences"),
}

# Context-sensitive deprecated terms (only in certain files/contexts)
CONTEXT_SENSITIVE_TERMS: dict[str, tuple[str, str, list[str]]] = {
    # measurement is OK in activity_values.py and backward-compat measurements.py
    r"\bmeasurement\b": (
        "activity",
        "Use 'activity' for bioactivity data (ChEMBL terminology)",
        ["activity_values.py", "measurements.py"],  # Allowed files
    ),
}

# Files to skip
SKIP_FILES = {
    "__pycache__",
    ".pyc",
    ".pyo",
    "test_",  # Don't lint test files for now
    "_test.py",
}

# Paths to skip (relative to search root)
SKIP_PATHS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
}


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    # Skip based on path components
    for part in filepath.parts:
        if part in SKIP_PATHS:
            return True

    # Skip based on file name patterns
    for pattern in SKIP_FILES:
        if pattern in filepath.name:
            return True

    return False


def check_file(filepath: Path, strict: bool = False) -> list[TermViolation]:
    """Check a file for terminology violations.

    Args:
        filepath: Path to the Python file to check.
        strict: If True, check context-sensitive terms too.

    Returns:
        List of TermViolation objects.
    """
    violations = []

    try:
        content = filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)
        return []

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        # Skip comments and docstrings (simple heuristic)
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        # Check deprecated terms
        for pattern, (canonical, desc) in DEPRECATED_TERMS.items():
            matches = list(re.finditer(pattern, line, re.IGNORECASE))
            for match in matches:
                violations.append(
                    TermViolation(
                        file=filepath,
                        line_num=line_num,
                        deprecated_term=match.group(),
                        canonical_term=canonical,
                        context=line.strip()[:80],
                    )
                )

        # Check context-sensitive terms in strict mode
        if strict:
            for pattern, (canonical, desc, allowed_files) in CONTEXT_SENSITIVE_TERMS.items():
                # Skip if file is in allowed list
                if any(allowed in filepath.name for allowed in allowed_files):
                    continue

                matches = list(re.finditer(pattern, line, re.IGNORECASE))
                for match in matches:
                    violations.append(
                        TermViolation(
                            file=filepath,
                            line_num=line_num,
                            deprecated_term=match.group(),
                            canonical_term=canonical,
                            context=line.strip()[:80],
                        )
                    )

    return violations


def lint_directory(
    path: Path, strict: bool = False, verbose: bool = False
) -> list[TermViolation]:
    """Lint all Python files in a directory.

    Args:
        path: Directory to search.
        strict: If True, enable strict checking.
        verbose: If True, print progress.

    Returns:
        List of all violations found.
    """
    all_violations = []

    if path.is_file():
        if path.suffix == ".py" and not should_skip_file(path):
            return check_file(path, strict)
        return []

    for py_file in path.rglob("*.py"):
        if should_skip_file(py_file):
            continue

        if verbose:
            print(f"Checking {py_file}...", file=sys.stderr)

        violations = check_file(py_file, strict)
        all_violations.extend(violations)

    return all_violations


def format_violations(violations: list[TermViolation]) -> str:
    """Format violations for output.

    Args:
        violations: List of violations to format.

    Returns:
        Formatted string with all violations.
    """
    if not violations:
        return "No terminology violations found."

    lines = [f"Found {len(violations)} terminology violation(s):", ""]

    for v in violations:
        lines.append(f"{v.file}:{v.line_num}: Use '{v.canonical_term}' instead of '{v.deprecated_term}'")
        lines.append(f"    {v.context}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for violations found).
    """
    parser = argparse.ArgumentParser(
        description="Check BioETL code for terminology violations.",
        epilog="See docs/glossary.md for canonical terminology.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Files or directories to check",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (check context-sensitive terms)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show files being checked",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output violations as JSON",
    )

    args = parser.parse_args()

    all_violations = []

    for path in args.paths:
        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            return 1

        violations = lint_directory(path, args.strict, args.verbose)
        all_violations.extend(violations)

    if args.json:
        import json

        output = [
            {
                "file": str(v.file),
                "line": v.line_num,
                "deprecated": v.deprecated_term,
                "canonical": v.canonical_term,
                "context": v.context,
            }
            for v in all_violations
        ]
        print(json.dumps(output, indent=2))
    else:
        print(format_violations(all_violations))

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
