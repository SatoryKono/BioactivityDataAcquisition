#!/usr/bin/env python3
"""
lint_terminology.py - Terminology linter for BioETL codebase.

Checks code and documentation for deprecated terms and enforces
the Ubiquitous Language defined in docs/glossary.md.

Checks performed:
- Deprecated class names (e.g., Loader → Adapter/Writer)
- Deprecated variable names (e.g., workflow → pipeline)
- Provider-specific term misuse (e.g., Compound for non-PubChem)
- Comment/docstring terminology

Usage:
    # Check entire project
    python src/tools/lint_terminology.py

    # Check specific file or directory
    python src/tools/lint_terminology.py src/bioetl/domain/

    # Auto-fix where possible
    python src/tools/lint_terminology.py --fix

    # Output JSON format
    python src/tools/lint_terminology.py --json

References:
    - docs/glossary.md: Ubiquitous Language definitions
    - RULES.md §2.4: Naming conventions

Aligned with RULES.md v5.10 (2026-01-06)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


# =============================================================================
# Terminology Rules (from docs/glossary.md)
# =============================================================================

# Deprecated terms and their canonical replacements
# Format: (deprecated_pattern, canonical_term, context_hint, is_fixable)
DEPRECATED_TERMS: list[tuple[str, str, str, bool]] = [
    # Class/type naming
    (
        r"\bclass\s+\w*Loader\b",
        "Adapter/Writer",
        "Use 'Adapter' for input, 'Writer' for output",
        False,
    ),
    (
        r"\bclass\s+\w*Handler\b",
        "Manager/Service",
        "Use specific name (e.g., Manager, Service)",
        False,
    ),
    # Variable/parameter naming
    (r"\bworkflow\b", "pipeline", "Use 'pipeline' instead of 'workflow'", True),
    (r"\bjob\b(?!\s*=|\s*:)", "run", "Use 'run' instead of 'job'", True),
    (r"\bchunk\b", "batch", "Use 'batch' instead of 'chunk'", True),
    (r"\bmeasurement\b", "activity", "Use 'activity' for bioactivity data", True),
    (r"\bdata_point\b", "record", "Use 'record' instead of 'data_point'", True),
    # CrossRef terminology
    (
        r"\bWork\b(?!s?\s+endpoint)",
        "Publication",
        "Use 'Publication' instead of CrossRef 'Work'",
        True,
    ),
    (r"\bWorkSchema\b", "PublicationSchema", "Use 'PublicationSchema'", True),
    (
        r"\bCrossRefWorkRecord\b",
        "CrossRefPublicationRecord",
        "Use 'CrossRefPublicationRecord'",
        True,
    ),
    # Data layer naming
    (r"\braw\b(?!_|\w)", "bronze", "Use 'bronze' for raw data layer", True),
    (r"\blanding\b", "bronze", "Use 'bronze' for raw data layer", True),
    (r"\bcleansed\b", "silver", "Use 'silver' for normalized layer", True),
    (r"\bcurated\b", "silver", "Use 'silver' for normalized layer", True),
    (r"\breporting\b(?!\s*server)", "gold", "Use 'gold' for analytics layer", True),
    (r"\bpresentation\b(?!\s*layer)", "gold", "Use 'gold' for analytics layer", True),
    # Operation terminology
    (
        r"\bping\b(?!\()",
        "health_check",
        "Use 'health_check' for availability verification",
        True,
    ),
    (r"\bstatus_check\b", "health_check", "Use 'health_check'", True),
    # Error handling
    (r"\bdead_letter\b", "quarantine", "Use 'quarantine' for failed records", True),
    (
        r"\berror_log\b(?!ger)",
        "quarantine",
        "Use 'quarantine' for failed records",
        True,
    ),
    # Identifier terminology
    (r"\bbusiness_key\b", "entity_id", "Use 'entity_id' for business identifier", True),
    (r"\bnatural_key\b", "entity_id", "Use 'entity_id' for business identifier", True),
    (
        r"\bchecksum\b(?!s?\s*=)",
        "content_hash",
        "Use 'content_hash' for deduplication hash",
        True,
    ),
    (r"\bexecution_id\b", "run_id", "Use 'run_id' for pipeline run identifier", True),
    (r"\bjob_id\b", "run_id", "Use 'run_id' for pipeline run identifier", True),
    (r"\bchunk_id\b", "batch_id", "Use 'batch_id' for batch identifier", True),
]

# File patterns to check
PYTHON_PATTERNS = ("*.py",)
MARKDOWN_PATTERNS = ("*.md",)
YAML_PATTERNS = ("*.yaml", "*.yml")

# Directories to skip
SKIP_DIRS = {
    ".venv",
    "venv",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "build",
    "dist",
    "site",
    ".benchmarks",
}

# Files to skip
SKIP_FILES = {
    "glossary.md",  # The glossary itself defines deprecated terms
    "lint_terminology.py",  # This tool mentions deprecated terms
}


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class TermViolation:
    """A terminology violation found in code."""

    file: Path
    line: int
    column: int
    deprecated: str
    canonical: str
    hint: str
    fixable: bool
    line_content: str

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "file": str(self.file.relative_to(PROJECT_ROOT)),
            "line": self.line,
            "column": self.column,
            "deprecated": self.deprecated,
            "canonical": self.canonical,
            "hint": self.hint,
            "fixable": self.fixable,
        }


@dataclass
class LintResult:
    """Result of terminology lint check."""

    violations: list[TermViolation] = field(default_factory=list)
    files_checked: int = 0
    fixed: int = 0

    @property
    def total_violations(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    @property
    def fixable_count(self) -> int:
        """Number of fixable violations."""
        return sum(1 for v in self.violations if v.fixable)


# =============================================================================
# Linting Functions
# =============================================================================


def _should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped."""
    # Skip by directory
    for part in file_path.parts:
        if part in SKIP_DIRS:
            return True

    # Skip by filename
    if file_path.name in SKIP_FILES:
        return True

    return False


def _check_file(file_path: Path) -> list[TermViolation]:
    """Check a single file for terminology violations.

    Args:
        file_path: Path to file to check.

    Returns:
        List of violations found.
    """
    violations: list[TermViolation] = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.debug("Could not read %s: %s", file_path, e)
        return violations

    lines = content.splitlines()

    for line_num, line in enumerate(lines, start=1):
        # Skip comments in Python (basic check)
        stripped = line.strip()
        is_comment = stripped.startswith("#") or stripped.startswith("//")

        for pattern, canonical, hint, fixable in DEPRECATED_TERMS:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                # Get the matched text
                deprecated_text = match.group(0)

                # Skip if in a string literal containing the canonical term
                # (likely documentation about the migration)
                if canonical.lower() in line.lower():
                    continue

                violations.append(
                    TermViolation(
                        file=file_path,
                        line=line_num,
                        column=match.start() + 1,
                        deprecated=deprecated_text,
                        canonical=canonical,
                        hint=hint,
                        fixable=fixable and not is_comment,
                        line_content=line,
                    )
                )

    return violations


def lint_path(path: Path, patterns: tuple[str, ...] = PYTHON_PATTERNS) -> LintResult:
    """Lint a file or directory for terminology violations.

    Args:
        path: File or directory to check.
        patterns: Glob patterns to match.

    Returns:
        LintResult with all violations found.
    """
    result = LintResult()

    if path.is_file():
        if not _should_skip_file(path):
            result.violations.extend(_check_file(path))
            result.files_checked = 1
    else:
        for pattern in patterns:
            for file_path in path.rglob(pattern):
                if _should_skip_file(file_path):
                    continue
                result.violations.extend(_check_file(file_path))
                result.files_checked += 1

    return result


def fix_violations(violations: list[TermViolation]) -> int:
    """Apply fixes for fixable violations.

    Args:
        violations: List of violations to fix.

    Returns:
        Number of fixes applied.
    """
    # Group violations by file
    by_file: dict[Path, list[TermViolation]] = {}
    for v in violations:
        if v.fixable:
            by_file.setdefault(v.file, []).append(v)

    fixed = 0

    for file_path, file_violations in by_file.items():
        try:
            content = file_path.read_text(encoding="utf-8")
            original = content

            # Sort violations by position (reverse order for safe replacement)
            file_violations.sort(key=lambda v: (v.line, v.column), reverse=True)

            lines = content.splitlines(keepends=True)

            for v in file_violations:
                line_idx = v.line - 1
                if line_idx < len(lines):
                    line = lines[line_idx]
                    # Simple case-preserving replacement
                    old_text = v.deprecated
                    new_text = v.canonical

                    # Try to preserve case
                    if old_text.isupper():
                        new_text = new_text.upper()
                    elif old_text[0].isupper():
                        new_text = new_text.capitalize()

                    lines[line_idx] = line.replace(old_text, new_text, 1)
                    fixed += 1

            new_content = "".join(lines)

            if new_content != original:
                file_path.write_text(new_content, encoding="utf-8")
                logger.info("  Fixed: %s", file_path.relative_to(PROJECT_ROOT))

        except Exception as e:
            logger.warning("  Failed to fix %s: %s", file_path, e)

    return fixed


# =============================================================================
# CLI Interface
# =============================================================================


def log_report_text(result: LintResult) -> None:
    """Log text report of violations."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Terminology Lint Report")
    logger.info("=" * 70)
    logger.info("")

    if not result.violations:
        logger.info("No terminology violations found.")
        logger.info("")
        logger.info("Files checked: %d", result.files_checked)
        logger.info("=" * 70)
        return

    # Group by file
    by_file: dict[Path, list[TermViolation]] = {}
    for v in result.violations:
        by_file.setdefault(v.file, []).append(v)

    for file_path, violations in sorted(by_file.items()):
        rel_path = file_path.relative_to(PROJECT_ROOT)
        logger.info("## %s (%d violations)", rel_path, len(violations))
        logger.info("")

        for v in sorted(violations, key=lambda x: x.line):
            fix_marker = "[F]" if v.fixable else "[ ]"
            logger.info(
                "  %s L%d:%d: '%s' → '%s'",
                fix_marker,
                v.line,
                v.column,
                v.deprecated,
                v.canonical,
            )
            logger.info("     %s", v.hint)
            # Show context (trimmed)
            context = v.line_content.strip()[:60]
            if len(v.line_content.strip()) > 60:
                context += "..."
            logger.info("     | %s", context)
            logger.info("")

    logger.info("=" * 70)
    logger.info("Summary:")
    logger.info("  Files checked:    %d", result.files_checked)
    logger.info("  Total violations: %d", result.total_violations)
    logger.info("  Fixable:          %d", result.fixable_count)
    if result.fixed > 0:
        logger.info("  Fixed:            %d", result.fixed)
    logger.info("")
    logger.info("Legend: [F] = auto-fixable, [ ] = manual fix required")
    logger.info("=" * 70)


def log_report_json(result: LintResult) -> None:
    """Log JSON report of violations."""
    report = {
        "files_checked": result.files_checked,
        "total_violations": result.total_violations,
        "fixable_count": result.fixable_count,
        "fixed": result.fixed,
        "violations": [v.to_dict() for v in result.violations],
    }
    logger.info(json.dumps(report, indent=2))


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL Terminology Linter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=PROJECT_ROOT / "src" / "bioetl",
        help="File or directory to check (default: src/bioetl/)",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Auto-fix fixable violations",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--include-docs",
        action="store_true",
        help="Include markdown documentation",
    )
    parser.add_argument(
        "--include-configs",
        action="store_true",
        help="Include YAML configuration files",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()

    # Determine patterns to check
    patterns = list(PYTHON_PATTERNS)
    if args.include_docs:
        patterns.extend(MARKDOWN_PATTERNS)
    if args.include_configs:
        patterns.extend(YAML_PATTERNS)

    # Resolve path
    path = args.path
    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        logger.error("Path does not exist: %s", path)
        return 2

    # Run lint
    result = lint_path(path, tuple(patterns))

    # Apply fixes if requested
    if args.fix and result.fixable_count > 0:
        result.fixed = fix_violations(result.violations)
        # Re-run to get updated violations
        result = lint_path(path, tuple(patterns))
        result.fixed = result.fixed  # Preserve fix count

    # Output report
    if args.json:
        log_report_json(result)
    else:
        log_report_text(result)

    return 1 if result.total_violations > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
