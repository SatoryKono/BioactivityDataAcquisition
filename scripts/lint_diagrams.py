#!/usr/bin/env python3
"""Lint Mermaid diagrams for BioETL (.mmd canonical, .mermaid legacy)."""

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
    "#fafafa",
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


def should_skip(_: Path, lines: list[str]) -> bool:
    for line in lines[:10]:
        low = line.lower()
        if "@status" in low and "superseded" in low:
            return True
        if "@type" in low and "legend" in low:
            return True
    return False


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    has_version = any(line.strip().startswith("%% @version") for line in lines[:30])
    has_date = any(line.strip().startswith("%% @date") for line in lines[:30])
    has_type = any(line.strip().startswith("%% @type") for line in lines[:30])
    has_level = any(line.strip().startswith("%% @level") for line in lines[:30])
    for ok, field_name in (
        (has_version, "@version"),
        (has_date, "@date"),
        (has_type, "@type"),
        (has_level, "@level"),
    ):
        if not ok:
            issues.append(
                Issue(
                    str(path),
                    "ERROR",
                    "META-001",
                    f"Missing required metadata field: %% {field_name}",
                )
            )
    return issues


def check_naming_convention(path: Path) -> list[Issue]:
    if NAMING_PATTERN.match(path.name):
        return []
    return [
        Issue(
            str(path),
            "ERROR",
            "NAME-001",
            f"File name '{path.name}' does not follow NN-topic.(mmd|mermaid) convention",
        )
    ]


def check_placeholder_content(path: Path, lines: list[str]) -> list[Issue]:
    content = "\n".join(lines).lower()
    for marker in PLACEHOLDER_MARKERS:
        if marker.lower() in content:
            return [
                Issue(
                    str(path),
                    "ERROR",
                    "CONTENT-001",
                    f"Contains placeholder marker: '{marker}'",
                )
            ]

    non_comment_lines = [
        line for line in lines if line.strip() and not line.strip().startswith("%%")
    ]
    if len(non_comment_lines) < 3:
        return [
            Issue(
                str(path),
                "ERROR",
                "CONTENT-002",
                f"Diagram has only {len(non_comment_lines)} non-comment lines (minimum 3)",
            )
        ]
    return []


def check_staleness(path: Path, lines: list[str], stale_days: int) -> list[Issue]:
    date_line = next(
        (line for line in lines if line.strip().startswith("%% @date")), None
    )
    if date_line is None:
        return []
    raw = date_line.split("@date", 1)[1].strip()
    try:
        updated = datetime.strptime(raw, "%Y-%m-%d")
    except ValueError:
        return [
            Issue(
                str(path),
                "ERROR",
                "META-002",
                f"Invalid date format in %% @date: '{raw}' (expected YYYY-MM-DD)",
            )
        ]

    age = datetime.now() - updated
    if age > timedelta(days=WARNING_STALE_DAYS):
        return [
            Issue(
                str(path),
                "ERROR",
                "STALE-001",
                f"Diagram is {age.days} days old (>{WARNING_STALE_DAYS}d threshold)",
            )
        ]
    if age > timedelta(days=stale_days):
        return [
            Issue(
                str(path),
                "WARNING",
                "STALE-002",
                f"Diagram is {age.days} days old (>{stale_days}d threshold)",
            )
        ]
    return []


def check_view_metadata(path: Path, lines: list[str]) -> list[Issue]:
    if not re.match(r"^\d{2}[a-z]-", path.name):
        return []
    issues: list[Issue] = []
    if not any(line.strip().startswith("%% @view") for line in lines[:40]):
        issues.append(
            Issue(
                str(path),
                "WARNING",
                "VIEW-001",
                "Decomposed diagram missing %% @view metadata",
            )
        )
    if not any(line.strip().startswith("%% @parent") for line in lines[:40]):
        issues.append(
            Issue(
                str(path),
                "WARNING",
                "VIEW-002",
                "Decomposed diagram missing %% @parent metadata",
            )
        )
    return issues


def detect_diagram_type(lines: list[str]) -> str | None:
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("%%") or not stripped:
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
    content = "\n".join(lines)
    dtype = detect_diagram_type(lines)
    patterns_by_type: dict[str, list[str]] = {
        "flowchart": [
            r"^\s*(\w+)\[",
            r"^\s*(\w+)\(",
            r"^\s*(\w+)\{",
            r"^\s*(\w+)>",
            r"^\s*(\w+)\[\[",
        ],
        "classDiagram": [r"^\s*class\s+(\w+)"],
        "sequenceDiagram": [r"^\s*participant\s+(\w+)", r"^\s*actor\s+(\w+)"],
        "stateDiagram": [r"^\s*state\s+\"?(\w+)"],
    }
    patterns = patterns_by_type.get(dtype or "flowchart", patterns_by_type["flowchart"])
    names: set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            names.add(match.group(1))
    count = len(names)
    if count > 35:
        return [
            Issue(
                str(path),
                "ERROR",
                "SIZE-001",
                f"Estimated {count} unique nodes (>35 CRITICAL). Decompose into Views.",
            )
        ]
    if count > 20:
        return [
            Issue(
                str(path),
                "WARNING",
                "SIZE-002",
                f"Estimated {count} unique nodes (>20 soft limit). Consider decomposition.",
            )
        ]
    return []


def check_subgraph_colours(path: Path, lines: list[str]) -> list[Issue]:
    issues: list[Issue] = []
    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("style ") and "fill:" in stripped:
            m = re.search(r"fill:(#[0-9a-fA-F]{6})", stripped)
            if m and m.group(1).lower() not in APPROVED_FILLS:
                issues.append(
                    Issue(
                        str(path),
                        "WARNING",
                        "COLOUR-001",
                        f"Line {idx}: Unapproved fill colour {m.group(1)}. See README.md colour scheme.",
                    )
                )
    return issues


def check_layout_hacks(path: Path, lines: list[str]) -> list[Issue]:
    count = sum(1 for line in lines if "LAYOUT-HACK" in line)
    if count > 5:
        return [
            Issue(
                str(path),
                "WARNING",
                "HACK-001",
                f"{count} LAYOUT-HACK comments (>5). Consider further decomposition.",
            )
        ]
    return []


def lint_file(path: Path, stale_days: int) -> list[Issue]:
    lines = path.read_text(encoding="utf-8").splitlines()
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
    files = sorted(
        list(diagram_dir.rglob("*.mmd")) + list(diagram_dir.rglob("*.mermaid"))
    )
    result = LintResult(files_checked=len(files))
    for path in files:
        issues = lint_file(path, stale_days)
        result.issues.extend(issues)
        if not any(i.severity == "ERROR" for i in issues):
            result.files_passed += 1
    return result


def format_text(result: LintResult) -> str:
    lines = ["Diagram Lint Results", "=" * 20, ""]
    for issue in result.issues:
        lines.append(f"[{issue.severity}] {issue.rule} {issue.file}: {issue.message}")
    if result.issues:
        lines.append("")
    lines.append(f"Files checked: {result.files_checked}")
    lines.append(f"Files passed:  {result.files_passed}")
    lines.append(f"Files failed:  {result.files_failed}")
    lines.append(f"Has errors:    {'yes' if result.has_errors else 'no'}")
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
    parser = argparse.ArgumentParser(
        description="Lint Mermaid diagram files against BioETL policy."
    )
    parser.add_argument(
        "path", nargs="?", default="", help="Directory or file to check"
    )
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--stale-days", type=int, default=DEFAULT_STALE_DAYS)
    args = parser.parse_args()

    if args.path:
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
    else:
        result = LintResult()
        for diagram_dir in DIAGRAM_DIRS:
            if diagram_dir.exists():
                dir_result = lint_directory(diagram_dir, args.stale_days)
                result.files_checked += dir_result.files_checked
                result.files_passed += dir_result.files_passed
                result.issues.extend(dir_result.issues)

    sys.stdout.write(
        (format_json(result) if args.json_output else format_text(result)) + "\n"
    )
    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
