#!/usr/bin/env python3
"""
lint_diagrams.py - Diagram policy linter for BioETL project.

Validates Mermaid diagram files across canonical and decomposed docs trees.

Checks performed:
- Presence of structured metadata headers (format-aware)
- Naming convention compliance (NN-topic.{mmd|mermaid})
- No placeholder/stub content
- Staleness detection based on %% Updated: or %% @date
- Node count thresholds (SIZE-001/002, ADR-040 D5)
- Approved colour palette enforcement (COLOUR-001, ADR-040 D3)
- View metadata for decomposed files (VIEW-001/002)
- Layout hack accumulation warning (HACK-001)

Usage:
    # Check all diagrams
    python scripts/lint_diagrams.py

    # Check specific paths (files and/or directories)
    python scripts/lint_diagrams.py docs/02-architecture/mmd-diagrams/
    python scripts/lint_diagrams.py docs/02-architecture/diagrams/mermaid/01-high-level.mermaid

    # Output JSON format
    python scripts/lint_diagrams.py --json

    # Set staleness threshold (days)
    python scripts/lint_diagrams.py --stale-days 90

References:
    - docs/02-architecture/mmd-diagrams/
    - docs/02-architecture/diagrams/mermaid/
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
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
NAMING_PATTERN = re.compile(
    r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$"
)
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]
PLACEHOLDER_PATTERNS = {
    marker: re.compile(rf"\b{re.escape(marker)}\b", re.IGNORECASE)
    for marker in PLACEHOLDER_MARKERS
}
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180

# ADR-040 D3: Approved fill colours from theme/custom.css
APPROVED_FILLS = {
    "#f3e5f5",  # Domain
    "#e8f5e9",  # Application
    "#ffcdd2",  # Infrastructure
    "#fff3e0",  # Composition / Bronze
    "#e3f2fd",  # Interfaces
    "#eceff1",  # External / Silver
    "#fff8e1",  # Gold
    "#ffebee",  # Quarantine
    "#fafafa",  # Neutral / container
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
    """Find all supported diagram files recursively for a base path."""
    if base.is_file():
        return [base] if base.suffix in SUPPORTED_SUFFIXES else []

    return sorted(
        list(base.rglob("*.mmd")) + list(base.rglob("*.mermaid"))
    )


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata; format depends on file type/location."""
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
        has_view = any(
            line.strip().startswith("%% View:")
            or line.strip().startswith("%% @view")
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
    """Check file follows NN-topic.{mmd|mermaid} naming convention."""
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
                    "NN[a]-topic(.mmd|.mermaid) convention"
                ),
            )
        )

    return issues


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    """Check for placeholder/stub content."""
    issues: list[Issue] = []
    fname = str(path)
    content = "\n".join(lines)

    for marker, pattern in PLACEHOLDER_PATTERNS.items():
        if pattern.search(content):
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

    date_str: str | None = None
    date_label: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("%% Updated:"):
            date_str = stripped.replace("%% Updated:", "").strip()
            date_label = "%% Updated:"
            break
        if stripped.startswith("%% @date"):
            date_str = stripped.replace("%% @date", "").strip()
            date_label = "%% @date"
            break

    if date_str is None:
        return issues

    try:
        updated_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="META-002",
                message=(
                    f"Invalid date format in {date_label}: '{date_str}' "
                    "(expected YYYY-MM-DD)"
                ),
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


def should_skip(path: Path, lines: list[str]) -> bool:
    """Skip superseded and legend files from content checks."""
    for line in lines[:10]:
        low = line.lower()
        if "@status" in low and "superseded" in low:
            return True
        if "@type" in low and "legend" in low:
            return True
    return False


def detect_diagram_type(lines: list[str]) -> str | None:
    """Identify diagram type from the first non-comment directive."""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        low = stripped.lower()
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
    """SIZE-001/002: Check estimated node count against ADR-040 thresholds."""
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
    """COLOUR-001: Validate fill colours against ADR-040 approved palette."""
    issues: list[Issue] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("style ") and "fill:" in stripped:
            match = re.search(r"fill:(#[0-9a-fA-F]{6})", stripped)
            if match and match.group(1).lower() not in APPROVED_FILLS:
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


def check_view_metadata(path: Path, lines: list[str]) -> list[Issue]:
    """VIEW-001/002: Check decomposed files have @view and @parent metadata."""
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


def check_layout_hacks(path: Path, lines: list[str]) -> list[Issue]:
    """HACK-001: Warn when excessive LAYOUT-HACK comments accumulate."""
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
    """Lint all supported diagram files in a directory recursively."""
    result = LintResult()
    diagram_files = find_diagram_files(diagram_dir)
    for path in diagram_files:
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(i.severity == "ERROR" for i in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)

    return result


def lint_paths(targets: list[Path], stale_days: int) -> LintResult:
    """Lint a list of file/directory targets."""
    result = LintResult()
    seen: set[Path] = set()
    files: list[Path] = []

    for target in targets:
        if target.is_file():
            if target.suffix in SUPPORTED_SUFFIXES and target not in seen:
                seen.add(target)
                files.append(target)
            continue

        for path in find_diagram_files(target):
            if path not in seen:
                seen.add(path)
                files.append(path)

    for path in sorted(files):
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
        "paths",
        nargs="*",
        help=(
            "Files and/or directories to check. "
            "Default: docs/02-architecture/mmd-diagrams and "
            "docs/02-architecture/diagrams/mermaid"
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
    targets = [Path(p) for p in args.paths] if args.paths else DIAGRAM_DIRS

    missing_targets = [t for t in targets if not t.exists()]
    if missing_targets:
        for target in missing_targets:
            print(f"Error: {target} does not exist", file=sys.stderr)
        return 2

    result = lint_paths(targets, args.stale_days)

    if args.json_output:
        print(format_json(result))
    else:
        print(format_text(result))

    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
