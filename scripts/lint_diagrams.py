#!/usr/bin/env python3
"""
lint_diagrams.py - Diagram policy linter for BioETL project.

Validates Mermaid diagram files across docs/ tree.

Checks performed:
- Presence of structured metadata headers (format-aware)
- Naming convention compliance (NN-topic.{mmd|mermaid})
- No placeholder/stub content
- Staleness detection based on %% Updated: or %% @date
- Deprecated palette detection in style/classDef lines
- Emoji detection in subgraph labels
- Node-count threshold checks via %% @nodes

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
    - docs/**/*.mmd
    - docs/**/*.mermaid
    - excludes docs/99-archive/**
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
    Path("docs"),
]
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
EXCLUDED_PATH_PARTS = {"99-archive"}
NAMING_PATTERN = re.compile(
    r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$"
)
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]

# ── Layout rules (ADR-040 adaptive layout) ────────────────────────────────────
_NODES_RE = re.compile(r"%%\s*@nodes\s+(\d+)")
_GRAPH_LINE_RE = re.compile(r"^(graph|flowchart)\b", re.IGNORECASE)
_ELK_RE = re.compile(r"%%\{init.*layout.*elk", re.IGNORECASE)
_NON_FLOW_RE = re.compile(
    r"^(classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap|gantt|pie)",
    re.IGNORECASE,
)
_STYLE_OR_CLASSDEF_RE = re.compile(r"^\s*(style|classDef)\b")
_HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
_SUBGRAPH_RE = re.compile(r"^\s*subgraph\b", re.IGNORECASE)
ELK_WARN_THRESHOLD = 20
ELK_ERROR_THRESHOLD = 40
SIZE_WARN_THRESHOLD = 20
SIZE_ERROR_THRESHOLD = 35
PLACEHOLDER_PATTERNS = {
    marker: re.compile(rf"\b{re.escape(marker)}\b", re.IGNORECASE)
    for marker in PLACEHOLDER_MARKERS
}
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180
DISALLOWED_SUBGRAPH_EMOJI = ("🟡", "🟢", "🔵", "🟣", "⚪")
# ADR-040 pre-harmonization palette (blocked in style/classDef rules).
DEPRECATED_PALETTE = {
    # Pre-ADR-040 Material Design palette (now replaced by Tailwind Slate)
    "#fff7ed",
    "#f59e0b",
    "#ecfdf5",
    "#10b981",
    "#eff6ff",
    "#2563eb",
    "#f5f3ff",
    "#7c3aed",
    "#f1f5f9",
    "#64748b",
    # Material 500-level fills (replaced by ADR-040 canonical fills)
    "#f3e5f5",
    "#e8f5e9",
    "#ffcdd2",
    "#fff3e0",
    "#e3f2fd",
    "#eceff1",
    "#fff8e1",
    "#ffebee",
    "#fce4ec",
    "#e0f7fa",
    "#efebe9",
    # Material border/accent colours
    "#1565c0",
    "#0d47a1",
    "#b71c1c",
    "#00838f",
    "#4e342e",
    "#546e7a",
    "#90a4ae",
    "#bbdefb",
    "#90caf9",
    "#64b5f6",
    "#42a5f5",
    "#1e88e5",
    "#1976d2",
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
    """Find all supported diagram files recursively for a base path.

    Files starting with '_' (e.g. _template.mmd) are excluded — they are
    scaffolding/template files, not renderable diagrams.
    """
    if base.is_file():
        if (
            base.suffix in SUPPORTED_SUFFIXES
            and not base.name.startswith("_")
            and not EXCLUDED_PATH_PARTS.intersection(base.parts)
        ):
            return [base]
        return []

    return sorted(
        f
        for f in list(base.rglob("*.mmd")) + list(base.rglob("*.mermaid"))
        if (
            not f.name.startswith("_")
            and not EXCLUDED_PATH_PARTS.intersection(f.parts)
        )
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


def check_colour_policy(path: Path, lines: list[str]) -> list[Issue]:
    """Check for deprecated non-canonical palette usage (COLOUR-001)."""
    issues: list[Issue] = []
    fname = str(path)

    found: set[str] = set()
    for line in lines:
        if not _STYLE_OR_CLASSDEF_RE.match(line):
            continue
        for color in _HEX_COLOR_RE.findall(line):
            normalized = color.lower()
            if normalized in DEPRECATED_PALETTE:
                found.add(normalized)

    if found:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="COLOUR-001",
                message=(
                    "Deprecated palette color(s) in style/classDef: "
                    f"{', '.join(sorted(found))}"
                ),
            )
        )

    return issues


def check_subgraph_emoji(path: Path, lines: list[str]) -> list[Issue]:
    """Disallow emoji prefixes in subgraph labels (COLOUR-002)."""
    issues: list[Issue] = []
    fname = str(path)

    found: set[str] = set()
    for line in lines:
        if not _SUBGRAPH_RE.match(line):
            continue
        for icon in DISALLOWED_SUBGRAPH_EMOJI:
            if icon in line:
                found.add(icon)

    if found:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="COLOUR-002",
                message=(
                    "Emoji prefixes in subgraph labels are forbidden: "
                    f"{', '.join(sorted(found))}"
                ),
            )
        )

    return issues


def check_node_count_policy(path: Path, lines: list[str]) -> list[Issue]:
    """Check ADR-040 node-count thresholds (SIZE-001/SIZE-002)."""
    issues: list[Issue] = []
    fname = str(path)

    # Keep full reference views exempt from density limits.
    if path.name.endswith("-full.mermaid"):
        return issues
    if path.name.startswith("00-legend"):
        return issues

    nodes: int | None = None
    for ln in lines:
        m = _NODES_RE.search(ln)
        if m:
            nodes = int(m.group(1))
            break

    if nodes is None:
        return issues

    if nodes > SIZE_ERROR_THRESHOLD:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="SIZE-001",
                message=f"@nodes={nodes} > {SIZE_ERROR_THRESHOLD}",
            )
        )
    elif nodes > SIZE_WARN_THRESHOLD:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="SIZE-002",
                message=f"@nodes={nodes} > {SIZE_WARN_THRESHOLD}",
            )
        )

    return issues


def check_layout_policy(path: Path, lines: list[str]) -> list[Issue]:
    """Check adaptive layout rules (ADR-040).

    LAYOUT-001: flowchart/graph with @nodes > 20 and no ELK init → WARNING
    LAYOUT-002: flowchart/graph with @nodes > 40 and no ELK init → ERROR
    """
    issues: list[Issue] = []
    fname = str(path)

    # Only applies to .mmd canonical files
    if path.suffix != ".mmd":
        return issues

    # Determine diagram type — skip non-flowchart types
    is_flowchart = False
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("%%"):
            # skip init directives and comments
            if s.startswith("%%{"):
                continue
            continue
        if _GRAPH_LINE_RE.match(s):
            is_flowchart = True
            break
        if _NON_FLOW_RE.match(s):
            return issues  # not a flowchart — skip
        break

    if not is_flowchart:
        return issues

    # Parse @nodes count
    nodes: int | None = None
    for ln in lines:
        m = _NODES_RE.search(ln)
        if m:
            nodes = int(m.group(1))
            break

    if nodes is None:
        return issues

    # Check ELK presence
    has_elk = any(_ELK_RE.search(ln) for ln in lines)

    if not has_elk and nodes > ELK_ERROR_THRESHOLD:
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="LAYOUT-002",
                message=(
                    f"@nodes={nodes} > {ELK_ERROR_THRESHOLD} without ELK layout init — "
                    "add %%{init: {'layout': 'elk'}}%% before graph declaration"
                ),
            )
        )
    elif not has_elk and nodes > ELK_WARN_THRESHOLD:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LAYOUT-001",
                message=(
                    f"@nodes={nodes} > {ELK_WARN_THRESHOLD} without ELK layout init — "
                    "consider adding %%{init: {'layout': 'elk'}}%% for better edge routing"
                ),
            )
        )

    return issues


def check_nbsp_padding(path: Path, lines: list[str]) -> list[Issue]:
    """Check for &nbsp; padding — NBSP-001 (ERROR).

    &nbsp; padding is deprecated in favour of CSS size tiers.
    See custom.css size-sm / size-md / size-lg classes.
    """
    issues: list[Issue] = []
    fname = str(path)
    nbsp_lines = [i + 1 for i, line in enumerate(lines) if "&nbsp;" in line]
    if nbsp_lines:
        count = sum(line.count("&nbsp;") for line in lines)
        sample = nbsp_lines[:5]
        issues.append(
            Issue(
                file=fname,
                severity="ERROR",
                rule="NBSP-001",
                message=(
                    f"Found {count} &nbsp; occurrences on {len(nbsp_lines)} lines "
                    f"(first: {sample}). Use CSS size tiers instead."
                ),
            )
        )
    return issues


def check_orphan_nodes(path: Path, lines: list[str]) -> list[Issue]:
    """Check for orphan nodes — GRAPH-001 (WARNING, ADR-040 D6).

    Delegates to prune_orphan_nodes parser for flowchart/graph and
    sequenceDiagram files only.  classDiagram and other types are skipped.
    """
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).parent))
    try:
        from prune_orphan_nodes import (
            detect_diagram_type,
            parse_flowchart_orphans,
            parse_keep_orphans,
            parse_sequence_orphans,
        )
    except ImportError:
        return []

    issues: list[Issue] = []
    fname = str(path)

    dtype = detect_diagram_type(lines)
    if dtype not in {"flowchart", "sequence"}:
        return issues

    keep = parse_keep_orphans(lines)

    if dtype == "flowchart":
        orphans, _, _ = parse_flowchart_orphans(lines, keep)
    else:
        orphans, _, _ = parse_sequence_orphans(lines, keep)

    if orphans:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="GRAPH-001",
                message=(
                    f"Orphan node(s) found (no edges): "
                    f"{', '.join(sorted(orphans))}. "
                    "Add %% keep-orphan: NodeId to exempt, or run "
                    "scripts/prune_orphan_nodes.py --fix"
                ),
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
    issues.extend(check_colour_policy(path, lines))
    issues.extend(check_subgraph_emoji(path, lines))
    issues.extend(check_node_count_policy(path, lines))
    issues.extend(check_layout_policy(path, lines))
    issues.extend(check_nbsp_padding(path, lines))
    issues.extend(check_orphan_nodes(path, lines))

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
            if (
                target.suffix in SUPPORTED_SUFFIXES
                and target not in seen
                and not EXCLUDED_PATH_PARTS.intersection(target.parts)
            ):
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
            "Default: docs/ (excluding docs/99-archive/**)"
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
