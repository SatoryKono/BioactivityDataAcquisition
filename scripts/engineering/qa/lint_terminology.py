#!/usr/bin/env python3
"""Terminology linter for BioETL Ubiquitous Language.

Validates that code uses canonical terminology as defined in docs/glossary.md.
This script is part of the code quality CI pipeline.

Usage:
    python -m scripts.engineering.qa check-terminology src/bioetl/
    python -m scripts.engineering.qa check-terminology --strict src/bioetl/domain/
    python -m scripts.engineering.qa check-terminology --check

Exit codes:
    0: No violations found
    1: Violations found or error occurred
"""

from __future__ import annotations

import argparse
import ast
import io
import re
import sys
import tokenize
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
    r"class\s+\w*Loader\b": (
        "Adapter/Writer",
        "Use Adapter for input, Writer for output",
    ),
    r"class\s+\w*Handler\b": (
        "Manager/Service",
        "Use specific names like Manager or Service",
    ),
    # ETL process terms
    r"\bworkflow\b": ("pipeline", "Use 'pipeline' for data processing sequences"),
    r"\bjob\b": ("run", "Use 'run' for pipeline execution instances"),
    r"\bchunk\b": (
        "batch",
        "Use 'batch' for collections of records processed together",
    ),
    # Data terms (when used as class/variable names, not in strings/comments)
    r"\bdata_point\b": ("record", "Use 'record' for data items"),
    # Domain terms (per glossary.md)
    r"class\s+\w*Workflow\b": (
        "Pipeline",
        "Use Pipeline for data processing sequences",
    ),
}

# Rules that are intentionally enforced only in strict mode to reduce
# false positives in compatibility wrappers and legacy adapter names.
STRICT_ONLY_PATTERNS = {
    r"class\s+\w*Loader\b",
    r"class\s+\w*Handler\b",
}

# Pattern-specific path allow-list for external terminology contexts.
PATTERN_PATH_ALLOWLIST: dict[str, tuple[str, ...]] = {
    r"\bjob\b": (
        "src/bioetl/infrastructure/adapters/uniprot/",
        "src/bioetl/domain/ports/idmapping.py",
        "src/bioetl/infrastructure/observability/server.py",
    ),
    r"\bworkflow\b": (".github/workflows/",),
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

# Prefixes (POSIX style) to skip entirely from default lint scope.
SKIP_PATH_PREFIXES = ("docs/00-project/ai/",)


def should_skip_file(filepath: Path) -> bool:
    """Check if file should be skipped."""
    normalized = filepath.as_posix()

    # Skip based on path components
    for part in filepath.parts:
        if part in SKIP_PATHS:
            return True

    # Skip known non-product documentation/tooling subtrees.
    for prefix in SKIP_PATH_PREFIXES:
        if normalized.startswith(prefix) or f"/{prefix}" in normalized:
            return True

    # Skip based on file name patterns
    filename = filepath.name
    for pattern in SKIP_FILES:
        if pattern == "test_" and filename.startswith("test_"):
            return True
        if pattern == "_test.py" and filename.endswith("_test.py"):
            return True
        if pattern in {"__pycache__", ".pyc", ".pyo"} and pattern in filename:
            return True

    return False


def _is_skippable_line(line: str) -> bool:
    """Return True when terminology scanning should skip the line."""
    stripped = line.strip()
    if stripped.startswith("#"):
        return True
    if stripped.startswith('"""') or stripped.startswith("'''"):
        return True
    return False


def _mask_line_segment(line: str, start_col: int, end_col: int) -> str:
    """Replace a line slice with spaces while preserving positions."""
    if start_col < 0:
        start_col = 0
    if end_col < start_col:
        end_col = start_col
    return f"{line[:start_col]}{' ' * max(0, end_col - start_col)}{line[end_col:]}"


def _mask_non_code_segments(content: str) -> list[str]:
    """Mask string/comment token spans to reduce false-positive matches."""
    masked_lines = content.splitlines()
    if not masked_lines:
        return masked_lines

    try:
        token_stream = tokenize.generate_tokens(io.StringIO(content).readline)
    except tokenize.TokenError:
        return masked_lines

    for token in token_stream:
        if token.type not in (tokenize.STRING, tokenize.COMMENT):
            continue

        start_line, start_col = token.start
        end_line, end_col = token.end
        if start_line <= 0 or start_line > len(masked_lines):
            continue

        if start_line == end_line:
            idx = start_line - 1
            masked_lines[idx] = _mask_line_segment(
                masked_lines[idx], start_col, end_col
            )
            continue

        for line_no in range(start_line, min(end_line, len(masked_lines)) + 1):
            idx = line_no - 1
            line = masked_lines[idx]
            if line_no == start_line:
                masked_lines[idx] = _mask_line_segment(line, start_col, len(line))
            elif line_no == end_line:
                masked_lines[idx] = _mask_line_segment(line, 0, end_col)
            else:
                masked_lines[idx] = " " * len(line)

    return masked_lines


def _make_violation(
    *,
    filepath: Path,
    line_num: int,
    match_text: str,
    canonical_term: str,
    line: str,
) -> TermViolation:
    """Create a TermViolation with normalized context formatting."""
    return TermViolation(
        file=filepath,
        line_num=line_num,
        deprecated_term=match_text,
        canonical_term=canonical_term,
        context=line.strip()[:80],
    )


def _collect_deprecated_term_violations(
    *,
    filepath: Path,
    line_num: int,
    line: str,
    strict: bool,
) -> list[TermViolation]:
    """Collect violations for globally deprecated terminology."""
    violations: list[TermViolation] = []
    normalized_path = filepath.as_posix()
    for pattern, (canonical, _desc) in DEPRECATED_TERMS.items():
        if not strict and pattern in STRICT_ONLY_PATTERNS:
            continue

        allowlist = PATTERN_PATH_ALLOWLIST.get(pattern, ())
        if allowlist and any(fragment in normalized_path for fragment in allowlist):
            continue

        for match in re.finditer(pattern, line, re.IGNORECASE):
            violations.append(
                _make_violation(
                    filepath=filepath,
                    line_num=line_num,
                    match_text=match.group(),
                    canonical_term=canonical,
                    line=line,
                )
            )
    return violations


def _collect_docstring_line_numbers(content: str) -> set[int]:
    """Collect line numbers occupied by module/class/function docstrings."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return set()

    docstring_lines: set[int] = set()

    def _mark_docstring(node: ast.AST) -> None:
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            return
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            start = first.lineno
            end = getattr(first, "end_lineno", start)
            docstring_lines.update(range(start, end + 1))

    def _walk(node: ast.AST) -> None:
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            _mark_docstring(node)
        for child in ast.iter_child_nodes(node):
            _walk(child)

    _walk(tree)
    return docstring_lines


def _allowed_context_file(filepath: Path, allowed_files: list[str]) -> bool:
    """Return True when context-sensitive pattern is allowed in the file."""
    return any(allowed in filepath.name for allowed in allowed_files)


def _collect_context_sensitive_violations(
    *,
    filepath: Path,
    line_num: int,
    line: str,
) -> list[TermViolation]:
    """Collect strict-mode violations with per-file allow-list handling."""
    violations: list[TermViolation] = []
    for pattern, (canonical, _desc, allowed_files) in CONTEXT_SENSITIVE_TERMS.items():
        if _allowed_context_file(filepath, allowed_files):
            continue

        for match in re.finditer(pattern, line, re.IGNORECASE):
            violations.append(
                _make_violation(
                    filepath=filepath,
                    line_num=line_num,
                    match_text=match.group(),
                    canonical_term=canonical,
                    line=line,
                )
            )
    return violations


def _read_file_content(filepath: Path) -> str | None:
    """Read file content while preserving stderr warning behavior."""
    try:
        return filepath.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Warning: Could not read {filepath}: {exc}", file=sys.stderr)
        return None


def _line_should_be_checked(
    *,
    line_num: int,
    line: str,
    docstring_lines: set[int],
) -> bool:
    """Return True when terminology scan should inspect the line."""
    return line_num not in docstring_lines and not _is_skippable_line(line)


def _line_violations(
    *,
    filepath: Path,
    line_num: int,
    line: str,
    strict: bool,
) -> list[TermViolation]:
    """Collect terminology violations for one normalized line."""
    violations = _collect_deprecated_term_violations(
        filepath=filepath,
        line_num=line_num,
        line=line,
        strict=strict,
    )
    if not strict:
        return violations
    violations.extend(
        _collect_context_sensitive_violations(
            filepath=filepath,
            line_num=line_num,
            line=line,
        )
    )
    return violations


def check_file(filepath: Path, strict: bool = False) -> list[TermViolation]:
    """Check a file for terminology violations.

    Args:
        filepath: Path to the Python file to check.
        strict: If True, check context-sensitive terms too.

    Returns:
        List of TermViolation objects.
    """
    violations: list[TermViolation] = []

    content = _read_file_content(filepath)
    if content is None:
        return []

    lines = _mask_non_code_segments(content)
    docstring_lines = _collect_docstring_line_numbers(content)

    for line_num, line in enumerate(lines, start=1):
        if not _line_should_be_checked(
            line_num=line_num,
            line=line,
            docstring_lines=docstring_lines,
        ):
            continue
        violations.extend(
            _line_violations(
                filepath=filepath,
                line_num=line_num,
                line=line,
                strict=strict,
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
    if path.is_file():
        if path.suffix == ".py" and not should_skip_file(path):
            return check_file(path, strict)
        return []

    all_violations = []
    for py_file in path.rglob("*.py"):
        if should_skip_file(py_file):
            continue

        if verbose:
            print(f"Checking {py_file}...", file=sys.stderr)

        violations = check_file(py_file, strict)
        all_violations.extend(violations)

    return all_violations


def _json_payload(violations: list[TermViolation]) -> list[dict[str, object]]:
    """Return JSON-serializable payload for terminology violations."""
    return [
        {
            "file": str(v.file),
            "line": v.line_num,
            "deprecated": v.deprecated_term,
            "canonical": v.canonical_term,
            "context": v.context,
        }
        for v in violations
    ]


def resolve_default_paths() -> list[Path]:
    """Return default lint scope when no explicit paths are provided."""
    candidates = [Path("src/bioetl"), Path("docs")]
    existing = [path for path in candidates if path.exists()]
    return existing if existing else [Path(".")]


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
        lines.append(
            f"{v.file}:{v.line_num}: Use '{v.canonical_term}' instead of '{v.deprecated_term}'"
        )
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
        nargs="*",
        type=Path,
        help="Files or directories to check (defaults to src/bioetl and docs)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (check context-sensitive terms)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Compatibility alias for check mode (default behavior).",
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
    target_paths = args.paths or resolve_default_paths()

    for path in target_paths:
        if not path.exists():
            print(f"Error: Path does not exist: {path}", file=sys.stderr)
            return 1

        violations = lint_directory(path, args.strict, args.verbose)
        all_violations.extend(violations)

    if args.json:
        import json

        print(json.dumps(_json_payload(all_violations), indent=2))
    else:
        print(format_violations(all_violations))

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
