#!/usr/bin/env python3
"""
lint_diagrams.py - Diagram policy linter for BioETL project.

Validates .mmd and .mermaid diagram files against the diagramming policy
defined in docs/02-architecture/diagrams/00-diagramming-policy.md and
ADR-040 (Diagram Governance).

Checks performed:
- META-001: Presence of structured metadata (format-aware: @-tags for .mmd, View for .mermaid)
- NAME-001: Naming convention compliance (NN-topic or NNa-topic)
- CONTENT-001: No placeholder/stub content
- CONTENT-002: Minimum 3 non-comment lines
- STALE-001/002: Staleness detection based on %% Updated: or @date
- SIZE-001/002: Node count limits (35 hard, 20 soft)
- COLOUR-001: Approved colour palette enforcement

Scans two directories:
- docs/02-architecture/mmd-diagrams/ (canonical .mmd files)
- docs/02-architecture/diagrams/mermaid/ (decomposed .mermaid views)

Usage:
    # Check all diagrams (both directories)
    python scripts/lint_diagrams.py

    # Check specific directory
    python scripts/lint_diagrams.py docs/02-architecture/mmd-diagrams/

    # Output JSON format
    python scripts/lint_diagrams.py --json

    # Set staleness threshold (days)
    python scripts/lint_diagrams.py --stale-days 90

References:
    - docs/02-architecture/diagrams/00-diagramming-policy.md
    - docs/02-architecture/decisions/ADR-040-diagram-governance.md
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

DIAGRAM_DIRS = [
    Path("docs/02-architecture/mmd-diagrams"),
    Path("docs/02-architecture/diagrams/mermaid"),
]
NAMING_PATTERN = re.compile(
    r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$"
)
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180

# Approved fill colours from custom.css (ADR-040 D1)
APPROVED_FILLS = {
    "#f3e5f5", "#e8f5e9", "#ffcdd2", "#fff3e0",
    "#e3f2fd", "#eceff1", "#fff8e1", "#ffebee",
    "#f8fafc",  # Legend background
}


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


def find_diagram_files(base: Path) -> list[Path]:
    """Find all .mmd and .mermaid files recursively."""
    return sorted(
        list(base.rglob("*.mmd")) + list(base.rglob("*.mermaid"))
    )


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata — format depends on file extension."""
    issues: list[Issue] = []
    fname = str(path)

    # Skip template files
    if path.name.startswith("_"):
        return issues

    if path.suffix == ".mmd":
        # @-format metadata (mmd-diagrams/)
        required_tags = {"@version", "@date", "@type", "@level"}
        found_tags: set[str] = set()
        for line in lines:
            for tag in required_tags:
                if line.strip().startswith(f"%% {tag}"):
                    found_tags.add(tag)
        missing = required_tags - found_tags
        for tag in sorted(missing):
            issues.append(
                Issue(
                    file=fname,
                    severity="WARNING",
                    rule="META-001",
                    message=f"Missing metadata: %% {tag}",
                )
            )
    else:
        # View-format metadata (diagrams/mermaid/)
        has_view = any(
            line.startswith("%% View:") or line.startswith("%% @view")
            for line in lines
        )
        if not has_view:
            issues.append(
                Issue(
                    file=fname,
                    severity="WARNING",
                    rule="META-001",
                    message="Missing %% View: metadata line",
                )
            )

    return issues


def check_naming_convention(path: Path) -> list[Issue]:
    """Check file follows NN-topic or NNa-topic naming convention."""
    issues: list[Issue] = []
    fname = str(path)

    # Skip template files and non-standard utility files
    if path.name.startswith("_"):
        return issues

    if not NAMING_PATTERN.match(path.name):
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="NAME-001",
                message=(
                    f"File name '{path.name}' does not follow "
                    f"NN-topic.{{mmd,mermaid}} convention"
                ),
            )
        )

    return issues


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    """Check for placeholder/stub content."""
    issues: list[Issue] = []
    fname = str(path)

    # Skip template files
    if path.name.startswith("_"):
        return issues

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
    """Check if diagram is stale based on %% Updated: or %% @date."""
    issues: list[Issue] = []
    fname = str(path)

    date_str = None
    for line in lines:
        if line.startswith("%% Updated:"):
            date_str = line.replace("%% Updated:", "").strip()
            break
        if line.strip().startswith("%% @date"):
            date_str = line.strip().replace("%% @date", "").strip()
            break

    if date_str is None:
        return issues  # No date found — caught by META-001

    try:
        updated_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="META-002",
                message=f"Invalid date format: '{date_str}' (expected YYYY-MM-DD)",
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


def check_node_count(path: Path, lines: list[str]) -> list[Issue]:
    """Warn if diagram exceeds node limits."""
    issues: list[Issue] = []
    fname = str(path)
    content = "\n".join(lines)

    # Skip -full reference diagrams and templates
    if "-full." in path.name or path.name.startswith("_"):
        return issues

    node_patterns = [
        r'\w+\["',        # flowchart: NodeId["
        r'\w+\[',         # flowchart: NodeId[
        r'\w+\(',         # flowchart: NodeId(
        r'\w+\{',         # flowchart: NodeId{
        r'class\s+\w+',   # classDiagram
        r'participant\s',  # sequenceDiagram
        r'state\s+\w+',   # stateDiagram
    ]
    node_count = 0
    for pattern in node_patterns:
        node_count += len(re.findall(pattern, content))

    if node_count > 35:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="SIZE-001",
                message=f"~{node_count} nodes (>35 CRITICAL). Decompose.",
            )
        )
    elif node_count > 20:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="SIZE-002",
                message=f"~{node_count} nodes (>20 soft limit).",
            )
        )

    return issues


def check_subgraph_colours(path: Path, lines: list[str]) -> list[Issue]:
    """Check subgraph styles use approved colour scheme."""
    issues: list[Issue] = []
    fname = str(path)
    for i, line in enumerate(lines):
        if line.strip().startswith("style ") and "fill:" in line:
            fill_match = re.search(r"fill:(#[0-9a-fA-F]{6})", line)
            if fill_match and fill_match.group(1).lower() not in APPROVED_FILLS:
                issues.append(
                    Issue(
                        file=fname,
                        severity="WARNING",
                        rule="COLOUR-001",
                        message=f"L{i+1}: Unapproved fill {fill_match.group(1)}",
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
    issues.extend(check_node_count(path, lines))
    issues.extend(check_subgraph_colours(path, lines))

    return issues


def lint_directory(diagram_dir: Path, stale_days: int) -> LintResult:
    """Lint all .mmd and .mermaid files in directory."""
    result = LintResult()

    diagram_files = find_diagram_files(diagram_dir)

    for path in diagram_files:
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(i.severity == "ERROR" for i in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)

    return result


def lint_all_directories(stale_days: int) -> LintResult:
    """Lint all configured diagram directories."""
    combined = LintResult()
    for d in DIAGRAM_DIRS:
        if d.is_dir():
            result = lint_directory(d, stale_days)
            combined.files_checked += result.files_checked
            combined.files_passed += result.files_passed
            combined.issues.extend(result.issues)
    return combined


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
        default=None,
        help=(
            "Directory or file to check. "
            "If omitted, scans both mmd-diagrams/ and diagrams/mermaid/."
        ),
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

    if args.path is None:
        result = lint_all_directories(args.stale_days)
    else:
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
