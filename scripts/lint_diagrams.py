#!/usr/bin/env python3
"""lint_diagrams.py - Diagram policy linter for BioETL project."""

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
NAMING_PATTERN = re.compile(r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$")
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180
APPROVED_FILLS = {
    "#f3e5f5",
    "#e8f5e9",
    "#ffcdd2",
    "#fff3e0",
    "#e3f2fd",
    "#eceff1",
    "#fff8e1",
    "#ffebee",
}


@dataclass
class Issue:
    file: str
    severity: str
    rule: str
    message: str


@dataclass
class LintResult:
    issues: list[Issue] = field(default_factory=list)
    files_checked: int = 0
    files_passed: int = 0

    @property
    def files_failed(self) -> int:
        return len({i.file for i in self.issues if i.severity == "ERROR"})

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)


def find_diagram_files(base: Path) -> list[Path]:
    return sorted(list(base.rglob("*.mmd")) + list(base.rglob("*.mermaid")))


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata — format depends on location."""
    issues: list[Issue] = []
    fname = str(path)

    if path.suffix == ".mmd":
        required_tags = {"@version", "@date", "@type", "@level"}
        found_tags: set[str] = set()
        for line in lines:
            stripped = line.strip()
            for tag in required_tags:
                if stripped.startswith(f"%% {tag}"):
                    found_tags.add(tag)
        for tag in sorted(required_tags - found_tags):
            issues.append(
                Issue(
                    file=fname,
                    severity="WARNING",
                    rule="META-001",
                    message=f"Missing metadata: %% {tag}",
                )
            )
    else:
        has_view = any(
            line.startswith("%% View:") or line.startswith("%% @view") for line in lines
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
    issues: list[Issue] = []
    if path.name.startswith("_"):
        return issues
    if not NAMING_PATTERN.match(path.name):
        issues.append(
            Issue(
                file=str(path),
                severity="ERROR",
                rule="NAME-001",
                message=(
                    f"File name '{path.name}' does not follow "
                    "NN[a]-topic(.view).(mmd|mermaid) convention"
                ),
            )
        )
    return issues


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    content = "\n".join(lines).lower()

    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in content:
            issues.append(
                Issue(
                    file=str(path),
                    severity="ERROR",
                    rule="CONTENT-001",
                    message=f"Contains placeholder marker: '{marker}'",
                )
            )
            break

    non_comment_lines = [
        line for line in lines if line.strip() and not line.strip().startswith("%%")
    ]
    if len(non_comment_lines) < 3:
        issues.append(
            Issue(
                file=str(path),
                severity="ERROR",
                rule="CONTENT-002",
                message=(
                    f"Diagram has only {len(non_comment_lines)} "
                    "non-comment lines (minimum 3)"
                ),
            )
        )

    return issues


def check_staleness(path: Path, lines: list[str], stale_days: int) -> list[Issue]:
    """Check if diagram is stale based on %% Updated: date (legacy format)."""
    issues: list[Issue] = []
    updated_line = next(
        (line for line in lines if line.startswith("%% Updated:")), None
    )
    if updated_line is None:
        return issues

    date_str = updated_line.replace("%% Updated:", "").strip()
    try:
        updated_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return [
            Issue(
                file=str(path),
                severity="ERROR",
                rule="META-002",
                message=f"Invalid date format in %% Updated: '{date_str}' (expected YYYY-MM-DD)",
            )
        ]

    age = datetime.now() - updated_date
    if age > timedelta(days=WARNING_STALE_DAYS):
        issues.append(
            Issue(
                file=str(path),
                severity="ERROR",
                rule="STALE-001",
                message=f"Diagram is {age.days} days old (>{WARNING_STALE_DAYS}d threshold)",
            )
        )
    elif age > timedelta(days=stale_days):
        issues.append(
            Issue(
                file=str(path),
                severity="WARNING",
                rule="STALE-002",
                message=f"Diagram is {age.days} days old (>{stale_days}d threshold)",
            )
        )
    return issues


def check_node_count(path: Path, lines: list[str]) -> list[Issue]:
    """Warn if diagram exceeds node limits."""
    if "-full." in path.name:
        return []

    content = "\n".join(lines)
    node_patterns = [
        r"\w+\[\"",
        r"\w+\[",
        r"\w+\(",
        r"\w+\{",
        r"class\s+\w+",
        r"participant\s",
        r"state\s+\w+",
    ]
    node_count = sum(len(re.findall(pattern, content)) for pattern in node_patterns)

    if node_count > 35:
        return [
            Issue(
                file=str(path),
                severity="ERROR",
                rule="SIZE-001",
                message=f"~{node_count} nodes (>35 CRITICAL). Decompose.",
            )
        ]
    if node_count > 20:
        return [
            Issue(
                file=str(path),
                severity="WARNING",
                rule="SIZE-002",
                message=f"~{node_count} nodes (>20 soft limit).",
            )
        ]
    return []


def check_subgraph_colours(path: Path, lines: list[str]) -> list[Issue]:
    """Check subgraph styles use approved colour scheme."""
    issues: list[Issue] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("style ") and "fill:" in stripped:
            fill_match = re.search(r"fill:(#[0-9a-fA-F]{6})", stripped)
            if fill_match and fill_match.group(1).lower() not in APPROVED_FILLS:
                issues.append(
                    Issue(
                        file=str(path),
                        severity="WARNING",
                        rule="COLOUR-001",
                        message=f"L{i + 1}: Unapproved fill {fill_match.group(1)}",
                    )
                )
    return issues


def lint_file(path: Path, stale_days: int) -> list[Issue]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        return [
            Issue(
                file=str(path),
                severity="ERROR",
                rule="IO-001",
                message=f"Cannot read file: {error}",
            )
        ]

    issues: list[Issue] = []
    issues.extend(check_metadata_headers(path, lines))
    issues.extend(check_naming_convention(path))
    issues.extend(check_placeholder_content(path, lines))
    issues.extend(check_staleness(path, lines, stale_days))
    issues.extend(check_node_count(path, lines))
    issues.extend(check_subgraph_colours(path, lines))
    return issues


def lint_directory(diagram_dir: Path, stale_days: int) -> LintResult:
    result = LintResult()
    for path in find_diagram_files(diagram_dir):
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(issue.severity == "ERROR" for issue in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)
    return result


def lint_default_targets(stale_days: int) -> LintResult:
    total = LintResult()
    for directory in DIAGRAM_DIRS:
        if not directory.exists():
            continue
        partial = lint_directory(directory, stale_days)
        total.files_checked += partial.files_checked
        total.files_passed += partial.files_passed
        total.issues.extend(partial.issues)
    return total


def format_text(result: LintResult) -> str:
    lines = ["Diagram Policy Lint Results", "=" * 40, ""]
    if not result.issues:
        lines.append("All diagrams pass policy checks.")
    else:
        grouped: dict[str, list[Issue]] = {}
        for issue in result.issues:
            grouped.setdefault(issue.file, []).append(issue)
        for file, issues in sorted(grouped.items()):
            lines.append(f"  {file}")
            for issue in issues:
                marker = {"ERROR": "E", "WARNING": "W", "INFO": "I"}[issue.severity]
                lines.append(f"    [{marker}] {issue.rule}: {issue.message}")
            lines.append("")

    errors = sum(1 for issue in result.issues if issue.severity == "ERROR")
    warnings = sum(1 for issue in result.issues if issue.severity == "WARNING")
    lines.append(f"Files checked: {result.files_checked}")
    lines.append(f"Files passed:  {result.files_passed}")
    lines.append(f"Files failed:  {result.files_failed}")
    lines.append(
        f"Total issues:  {len(result.issues)} ({errors} errors, {warnings} warnings)"
    )
    return "\n".join(lines)


def format_json(result: LintResult) -> str:
    return json.dumps(
        {
            "files_checked": result.files_checked,
            "files_passed": result.files_passed,
            "files_failed": result.files_failed,
            "has_errors": result.has_errors,
            "issues": [issue.__dict__ for issue in result.issues],
        },
        indent=2,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Mermaid/MMD diagram files.")
    parser.add_argument(
        "path", nargs="?", default=None, help="Directory or file to check"
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    args = parser.parse_args()

    if args.path is None:
        result = lint_default_targets(args.stale_days)
    else:
        target = Path(args.path)
        if target.is_file():
            result = LintResult(files_checked=1)
            result.issues = lint_file(target, args.stale_days)
            if not any(issue.severity == "ERROR" for issue in result.issues):
                result.files_passed = 1
        elif target.is_dir():
            result = lint_directory(target, args.stale_days)
        else:
            sys.stderr.write(f"Error: {target} does not exist\n")
            return 2

    sys.stdout.write(
        (format_json(result) if args.json_output else format_text(result)) + "\n"
    )
    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
