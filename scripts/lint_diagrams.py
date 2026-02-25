#!/usr/bin/env python3
"""Diagram policy linter for BioETL Mermaid files (.mmd + .mermaid)."""

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
    Path("docs/02-architecture/diagrams"),
]
NAMING_PATTERN = re.compile(r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$")
PLACEHOLDER_MARKERS = ["placeholder", "todo", "fixme", "stub"]
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180


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
        failed_files = {i.file for i in self.issues if i.severity == "ERROR"}
        return len(failed_files)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "ERROR" for i in self.issues)


def _get_line_value(lines: list[str], prefix: str) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(prefix):
            return stripped[len(prefix) :].strip()
    return None


def should_skip(_path: Path, lines: list[str]) -> bool:
    """Skip superseded and legend files from content checks."""
    for line in lines[:10]:
        low = line.lower()
        if "@status" in low and "superseded" in low:
            return True
        if "@type" in low and "legend" in low:
            return True
    return False


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Allow both legacy and @-metadata styles."""
    fname = str(path)
    issues: list[Issue] = []

    # New metadata style
    has_version = _get_line_value(lines, "%% @version") is not None
    has_date = _get_line_value(lines, "%% @date") is not None
    has_type = _get_line_value(lines, "%% @type") is not None
    has_level = _get_line_value(lines, "%% @level") is not None

    # Legacy metadata style
    content = "\n".join(lines)
    has_title = "%% Title:" in content
    has_covers = "%% Covers:" in content
    has_updated = "%% Updated:" in content
    has_components = "%% Components:" in content

    if (has_version and has_date and has_type and has_level) or (
        has_title and has_covers and has_updated and has_components
    ):
        return issues

    issues.append(
        Issue(
            file=fname,
            severity="ERROR",
            rule="META-001",
            message=(
                "Missing required metadata headers. Expected either "
                "(@version,@date,@type,@level) or "
                "(Title,Covers,Updated,Components)."
            ),
        )
    )
    return issues


def check_naming_convention(path: Path) -> list[Issue]:
    if NAMING_PATTERN.match(path.name):
        return []
    return [
        Issue(
            file=str(path),
            severity="ERROR",
            rule="NAME-001",
            message=(
                f"File name '{path.name}' does not follow "
                "NN[a]-topic.(mmd|mermaid) convention"
            ),
        )
    ]


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    content = "\n".join(lines).lower()

    for marker in PLACEHOLDER_MARKERS:
        if marker in content:
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
                    f"Diagram has only {len(non_comment_lines)} non-comment "
                    "lines (minimum 3)"
                ),
            )
        )

    return issues


def check_staleness(path: Path, lines: list[str], stale_days: int) -> list[Issue]:
    issues: list[Issue] = []
    fname = str(path)

    date_str = _get_line_value(lines, "%% @date")
    if date_str is None:
        date_str = _get_line_value(lines, "%% Updated:")
    if date_str is None:
        return issues

    try:
        updated_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return [
            Issue(
                file=fname,
                severity="ERROR",
                rule="META-002",
                message=(
                    "Invalid date format in %% @date/%% Updated: "
                    f"'{date_str}' (expected YYYY-MM-DD)"
                ),
            )
        ]

    age = datetime.now() - updated_date
    if age > timedelta(days=WARNING_STALE_DAYS):
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="STALE-001",
                message=(
                    f"Diagram is {age.days} days old (>{WARNING_STALE_DAYS}d threshold)"
                ),
            )
        )
    elif age > timedelta(days=stale_days):
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="STALE-002",
                message=f"Diagram is {age.days} days old (>{stale_days}d)",
            )
        )
    return issues


def check_view_metadata(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    if not re.match(r"^\d{2}[a-z]-", path.name):
        return issues

    has_view = any(line.strip().startswith("%% @view") for line in lines)
    has_parent = any(line.strip().startswith("%% @parent") for line in lines)

    if not has_view:
        issues.append(
            Issue(
                file=str(path),
                severity="WARNING",
                rule="VIEW-001",
                message="Decomposed diagram missing %% @view metadata",
            )
        )
    if not has_parent:
        issues.append(
            Issue(
                file=str(path),
                severity="WARNING",
                rule="VIEW-002",
                message="Decomposed diagram missing %% @parent metadata",
            )
        )
    return issues


def detect_diagram_type(lines: list[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        low = stripped.lower()
        if not stripped or stripped.startswith("%%"):
            continue
        if low.startswith(("flowchart", "graph")):
            return "flowchart"
        if low.startswith("classdiagram"):
            return "classDiagram"
        if low.startswith("sequencediagram"):
            return "sequenceDiagram"
        if low.startswith("statediagram"):
            return "stateDiagram"
        return None
    return None


def check_node_count(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    content = "\n".join(lines)
    dtype = detect_diagram_type(lines)

    patterns_by_type: dict[str | None, list[str]] = {
        "flowchart": [
            r"^\s+(\w+)\[\[",
            r"^\s+(\w+)\[",
            r"^\s+(\w+)\(",
            r"^\s+(\w+)\{",
            r"^\s+(\w+)>",
        ],
        "classDiagram": [r"^\s+class\s+(\w+)"],
        "sequenceDiagram": [r"^\s+participant\s+(\w+)", r"^\s+actor\s+(\w+)"],
        "stateDiagram": [r"^\s+state\s+\"?(\w+)"],
        None: [
            r"^\s+(\w+)\[\[",
            r"^\s+(\w+)\[",
            r"^\s+(\w+)\(",
            r"^\s+(\w+)\{",
            r"^\s+(\w+)>",
        ],
    }

    node_names: set[str] = set()
    for pattern in patterns_by_type.get(dtype, patterns_by_type[None]):
        for match in re.finditer(pattern, content, re.MULTILINE):
            node_names.add(match.group(1))

    node_count = len(node_names)
    if node_count > 35:
        issues.append(
            Issue(
                file=str(path),
                severity="ERROR",
                rule="SIZE-001",
                message=(
                    f"Estimated {node_count} unique nodes (>35 CRITICAL). "
                    "Decompose into Views."
                ),
            )
        )
    elif node_count > 20:
        issues.append(
            Issue(
                file=str(path),
                severity="WARNING",
                rule="SIZE-002",
                message=(
                    f"Estimated {node_count} unique nodes (>20 soft limit). "
                    "Consider decomposition."
                ),
            )
        )
    return issues


def check_subgraph_colours(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    approved_fills = {
        "#f3e5f5",
        "#e8f5e9",
        "#ffcdd2",
        "#fff3e0",
        "#e3f2fd",
        "#eceff1",
        "#fff8e1",
        "#ffebee",
        "#fafafa",
    }

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("style ") and "fill:" in stripped:
            match = re.search(r"fill:(#[0-9a-fA-F]{6})", stripped)
            if match and match.group(1).lower() not in approved_fills:
                issues.append(
                    Issue(
                        file=str(path),
                        severity="WARNING",
                        rule="COLOUR-001",
                        message=(
                            f"Line {idx}: Unapproved fill colour {match.group(1)}. "
                            "See README.md colour scheme."
                        ),
                    )
                )
    return issues


def check_layout_hacks(path: Path, lines: list[str]) -> list[Issue]:
    hack_count = sum(1 for line in lines if "LAYOUT-HACK" in line)
    if hack_count <= 5:
        return []
    return [
        Issue(
            file=str(path),
            severity="WARNING",
            rule="HACK-001",
            message=(
                f"{hack_count} LAYOUT-HACK comments (>5). "
                "Consider further decomposition."
            ),
        )
    ]


def lint_file(path: Path, stale_days: int) -> list[Issue]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return [
            Issue(
                file=str(path),
                severity="ERROR",
                rule="IO-001",
                message=f"Cannot read file: {exc}",
            )
        ]

    if should_skip(path, lines):
        return []

    issues: list[Issue] = []
    issues.extend(check_metadata_headers(path, lines))
    issues.extend(check_naming_convention(path))
    issues.extend(check_placeholder_content(path, lines))
    issues.extend(check_staleness(path, lines, stale_days))
    issues.extend(check_view_metadata(path, lines))
    issues.extend(check_node_count(path, lines))
    issues.extend(check_subgraph_colours(path, lines))
    issues.extend(check_layout_hacks(path, lines))
    return issues


def lint_directory(diagram_dir: Path, stale_days: int) -> LintResult:
    result = LintResult()
    mermaid_files = sorted(
        list(diagram_dir.rglob("*.mmd")) + list(diagram_dir.rglob("*.mermaid"))
    )
    for path in mermaid_files:
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(i.severity == "ERROR" for i in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)
    return result


def format_text(result: LintResult) -> str:
    lines: list[str] = ["Diagram Policy Lint Results", "=" * 40, ""]
    if not result.issues:
        lines.append("All diagrams pass policy checks.")
    else:
        by_file: dict[str, list[Issue]] = {}
        for issue in result.issues:
            by_file.setdefault(issue.file, []).append(issue)
        for file, issues in sorted(by_file.items()):
            lines.append(f"  {file}")
            for issue in issues:
                marker = {"ERROR": "E", "WARNING": "W", "INFO": "I"}[issue.severity]
                lines.append(f"    [{marker}] {issue.rule}: {issue.message}")
            lines.append("")
    lines.extend(
        [
            f"Files checked: {result.files_checked}",
            f"Files passed:  {result.files_passed}",
            f"Files failed:  {result.files_failed}",
            (
                f"Total issues:  {len(result.issues)} "
                f"({sum(1 for i in result.issues if i.severity == 'ERROR')} errors, "
                f"{sum(1 for i in result.issues if i.severity == 'WARNING')} warnings)"
            ),
        ]
    )
    return "\n".join(lines)


def format_json(result: LintResult) -> str:
    return json.dumps(
        {
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
        },
        indent=2,
    )


def _lint_default_dirs(stale_days: int) -> LintResult:
    result = LintResult()
    for directory in DIAGRAM_DIRS:
        if not directory.exists():
            continue
        partial = lint_directory(directory, stale_days)
        result.files_checked += partial.files_checked
        result.files_passed += partial.files_passed
        result.issues.extend(partial.issues)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lint Mermaid diagram files against BioETL diagram policy.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=None,
        help="Directory or file to check (default: canonical + legacy dirs)",
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help=f"Days before diagram is considered stale (default: {DEFAULT_STALE_DAYS})",
    )

    args = parser.parse_args()
    if args.path is None:
        result = _lint_default_dirs(args.stale_days)
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
            sys.stderr.write(f"Error: {target} does not exist\n")
            return 2

    sys.stdout.write(
        (format_json(result) if args.json_output else format_text(result)) + "\n"
    )
    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
