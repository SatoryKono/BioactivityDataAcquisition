#!/usr/bin/env python3
"""
lint_diagrams.py - Diagram policy linter for BioETL project.

Validates .mermaid diagram files against the diagramming policy
defined in docs/02-architecture/diagrams/00-diagramming-policy.md.

Checks performed:
- Presence of structured metadata headers (Title, Covers, Updated, Components)
- Naming convention compliance (NN-topic.mermaid)
- No placeholder/stub content
- Staleness detection based on %% Updated: date
- File extension consistency (.mermaid only, no .mmd)

Usage:
    # Check all diagrams
    python scripts/lint_diagrams.py

    # Check specific directory
    python scripts/lint_diagrams.py docs/02-architecture/diagrams/

    # Output JSON format
    python scripts/lint_diagrams.py --json

    # Set staleness threshold (days)
    python scripts/lint_diagrams.py --stale-days 90

References:
    - docs/02-architecture/diagrams/00-diagramming-policy.md
    - RULES.md §1 (Architecture)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

DIAGRAM_DIR = Path("docs/02-architecture/diagrams")
NAMING_PATTERN = re.compile(r"^\d{2}-[a-z0-9]+(?:-[a-z0-9]+)*\.mermaid$")
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180


@dataclass
class Issue:
    file: str
    severity: str  # ERROR, WARNING, INFO
    rule: str
    message: str


@dataclass
class LintResult:
    issues: list[Issue] = field(default_factory=list)
    files_checked: int = 0
    files_passed: int = 0

    @property
    def files_failed(self) -> int:
        failed_files = {i.file for i in self.issues if i.severity == "ERROR"}
        return len(failed_files)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata headers: Title, Covers, Updated, Components."""
    issues: list[Issue] = []
    fname = str(path)

    header_lines = [
        line for line in lines if line.startswith("%% ") and ": " in line
    ]
    headers_found = {
        line.split(": ", 1)[0].replace("%% ", "") for line in header_lines
    }

    required = {"Title", "Covers", "Updated", "Components"}
    missing = required - headers_found

    for h in sorted(missing):
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="META-001",
                message=f"Missing required metadata header: %% {h}:",
            )
        )

    return issues


def check_naming_convention(path: Path) -> list[Issue]:
    """Check file follows NN-topic.mermaid naming convention."""
    issues: list[Issue] = []
    fname = str(path)

    if not NAMING_PATTERN.match(path.name):
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="NAME-001",
                message=(
                    f"File name '{path.name}' does not follow "
                    f"NN-topic.mermaid convention"
                ),
            )
        )

    return issues


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    """Check for placeholder/stub content."""
    issues: list[Issue] = []
    fname = str(path)
    content = "\n".join(lines).lower()

    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in content:
            issues.append(
                Issue(
                    file=fname,
                    severity="ERROR",
                    rule="CONTENT-001",
                    message=f"Contains placeholder marker: '{marker}'",
                )
            )
            break

    # Check for files that are too short to be real diagrams
    non_comment_lines = [
        line
        for line in lines
        if line.strip() and not line.strip().startswith("%%")
    ]
    if len(non_comment_lines) < 3:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="CONTENT-002",
                message=(
                    f"Diagram has only {len(non_comment_lines)} "
                    f"non-comment lines (minimum 3)"
                ),
            )
        )

    return issues


def check_staleness(
    path: Path,
    lines: list[str],
    stale_days: int,
) -> list[Issue]:
    """Check if diagram is stale based on %% Updated: date."""
    issues: list[Issue] = []
    fname = str(path)

    updated_line = None
    for line in lines:
        if line.startswith("%% Updated:"):
            updated_line = line
            break

    if updated_line is None:
        return issues  # Already caught by META-001

    date_str = updated_line.replace("%% Updated:", "").strip()
    try:
        updated_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="META-002",
                message=f"Invalid date format in %% Updated: '{date_str}' (expected YYYY-MM-DD)",
            )
        )
        return issues

    now = datetime.now()
    age = now - updated_date

    if age > timedelta(days=WARNING_STALE_DAYS):
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="STALE-001",
                message=f"Diagram is {age.days} days old (>{WARNING_STALE_DAYS}d threshold)",
            )
        )
    elif age > timedelta(days=stale_days):
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="STALE-002",
                message=f"Diagram is {age.days} days old (>{stale_days}d threshold)",
            )
        )

    return issues


def check_extension_consistency(diagram_dir: Path) -> list[Issue]:
    """Check for .mmd files that should be .mermaid."""
    issues: list[Issue] = []

    for mmd_file in diagram_dir.rglob("*.mmd"):
        issues.append(
            Issue(
                file=str(mmd_file),
                severity="ERROR",
                rule="EXT-001",
                message="Legacy .mmd extension found. Rename to .mermaid.",
            )
        )

    return issues


def lint_file(path: Path, stale_days: int) -> list[Issue]:
    """Run all checks on a single diagram file."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return [
            Issue(
                file=str(path),
                severity="ERROR",
                rule="IO-001",
                message=f"Cannot read file: {e}",
            )
        ]

    lines = content.splitlines()

    issues: list[Issue] = []
    issues.extend(check_metadata_headers(path, lines))
    issues.extend(check_naming_convention(path))
    issues.extend(check_placeholder_content(path, lines))
    issues.extend(check_staleness(path, lines, stale_days))

    return issues


def lint_directory(diagram_dir: Path, stale_days: int) -> LintResult:
    """Lint all .mermaid files in directory."""
    result = LintResult()

    # Check for .mmd files
    result.issues.extend(check_extension_consistency(diagram_dir))

    # Check all .mermaid files
    mermaid_files = sorted(diagram_dir.glob("*.mermaid"))

    for path in mermaid_files:
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(i.severity == "ERROR" for i in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)

    return result


def format_text(result: LintResult) -> str:
    """Format results as human-readable text."""
    lines: list[str] = []
    lines.append("Diagram Policy Lint Results")
    lines.append("=" * 40)
    lines.append("")

    if not result.issues:
        lines.append("All diagrams pass policy checks.")
    else:
        # Group by file
        by_file: dict[str, list[Issue]] = {}
        for issue in result.issues:
            by_file.setdefault(issue.file, []).append(issue)

        for file, issues in sorted(by_file.items()):
            lines.append(f"  {file}")
            for issue in issues:
                marker = {"ERROR": "E", "WARNING": "W", "INFO": "I"}[
                    issue.severity
                ]
                lines.append(
                    f"    [{marker}] {issue.rule}: {issue.message}"
                )
            lines.append("")

    lines.append(f"Files checked: {result.files_checked}")
    lines.append(f"Files passed:  {result.files_passed}")
    lines.append(f"Files failed:  {result.files_failed}")
    lines.append(
        f"Total issues:  {len(result.issues)} "
        f"({sum(1 for i in result.issues if i.severity == 'ERROR')} errors, "
        f"{sum(1 for i in result.issues if i.severity == 'WARNING')} warnings)"
    )

    return "\n".join(lines)


def format_json(result: LintResult) -> str:
    """Format results as JSON."""
    data = {
        "files_checked": result.files_checked,
        "files_passed": result.files_passed,
        "files_failed": result.files_failed,
        "has_errors": result.has_errors,
        "issues": [
            {
                "file": i.file,
                "severity": i.severity,
                "rule": i.rule,
                "message": i.message,
            }
            for i in result.issues
        ],
    }
    return json.dumps(data, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint diagram files against BioETL diagramming policy.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=str(DIAGRAM_DIR),
        help="Directory or file to check (default: docs/02-architecture/diagrams/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help=f"Days before diagram is considered stale (default: {DEFAULT_STALE_DAYS})",
    )

    args = parser.parse_args()
    target = Path(args.path)

    if target.is_file():
        result = LintResult(files_checked=1)
        issues = lint_file(target, args.stale_days)
        result.issues = issues
        if not any(i.severity == "ERROR" for i in issues):
            result.files_passed = 1
    elif target.is_dir():
        result = lint_directory(target, args.stale_days)
    else:
        print(f"Error: {target} does not exist", file=sys.stderr)
        return 2

    if args.json_output:
        print(format_json(result))
    else:
        print(format_text(result))

    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
