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
    python scripts/diagrams/lint_diagrams.py

    # Check specific paths (files and/or directories)
    python scripts/diagrams/lint_diagrams.py docs/02-architecture/diagrams/
    python scripts/diagrams/lint_diagrams.py docs/02-architecture/diagrams/mermaid/01-high-level.mermaid

    # Output JSON format
    python scripts/diagrams/lint_diagrams.py --json

    # Set staleness threshold (days)
    python scripts/diagrams/lint_diagrams.py --stale-days 90

References:
    - docs/**/*.mmd
    - docs/**/*.mermaid
    - excludes docs/99-archive/**
"""

from __future__ import annotations

import argparse
import json
import math
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
NAMING_PATTERN = re.compile(r"^\d{2}[a-z]?-[a-z0-9]+(?:-[a-z0-9]+)*\.(?:mmd|mermaid)$")
PLACEHOLDER_MARKERS = ["placeholder", "TODO", "FIXME", "stub"]

# ── Layout rules (ADR-040 adaptive layout) ────────────────────────────────────
_NODES_RE = re.compile(r"%%\s*@nodes\s+(\d+)")
_GRAPH_LINE_RE = re.compile(r"^(graph|flowchart)\b", re.IGNORECASE)
_EDGE_ROUTING_VALUE_RE = re.compile(
    r"""(?:['"])?edgeRouting(?:['"])?\s*:\s*['"]([A-Z_]+)['"]""",
    re.IGNORECASE,
)
_NON_FLOW_RE = re.compile(
    r"^(classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap|gantt|pie)",
    re.IGNORECASE,
)
_CLASS_DIAGRAM_RE = re.compile(r"^\s*classDiagram\b", re.IGNORECASE)
_UNESCAPED_DUNDER_METHOD_RE = re.compile(r"^\s*[+\-#~][^\n]*?(?<!\\)__\w+__(?=\s*\()")
_STYLE_OR_CLASSDEF_RE = re.compile(r"^\s*(style|classDef)\b")
_HEX_COLOR_RE = re.compile(r"#[0-9a-f]{6}\b", re.IGNORECASE)
_SUBGRAPH_RE = re.compile(r"^\s*subgraph\b", re.IGNORECASE)
_LINK_STYLE_RE = re.compile(r"^\s*linkStyle\s+([^\s]+)")
_BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
_QUOTED_LABEL_RE = re.compile(r'"([^"]+)"')
_HTML_TAG_RE = re.compile(r"<[^>]+>")
ELK_WARN_THRESHOLD = 20
ELK_ERROR_THRESHOLD = 40
SIZE_WARN_THRESHOLD = 20
SIZE_ERROR_THRESHOLD = 35
LABEL_WARN_LINE_CHARS = 42
LABEL_WARN_MAX_LINES = 8
LABEL_WARN_PADDING_BREAKS = 3
CLASS_METHOD_WARN_LINE_CHARS = 88
PLACEHOLDER_PATTERNS = {
    marker: re.compile(rf"\b{re.escape(marker)}\b", re.IGNORECASE)
    for marker in PLACEHOLDER_MARKERS
}
DEFAULT_STALE_DAYS = 90
WARNING_STALE_DAYS = 180
DISALLOWED_SUBGRAPH_EMOJI = ("🟡", "🟢", "🔵", "🟣", "⚪")
# Canonical ADR-040 palette values that must not be flagged by COLOUR-001.
CANONICAL_PALETTE = {
    "#f5f3ff",
    "#7c3aed",  # Domain
    "#f0fdf4",
    "#16a34a",  # Application
    "#fff1f2",
    "#dc2626",  # Infrastructure
    "#fff7ed",
    "#f59e0b",  # Composition / Bronze
    "#eff6ff",
    "#2563eb",  # Interfaces
    "#f1f5f9",
    "#64748b",  # External
    "#f8fafc",
    "#475569",  # Silver
    "#fefce8",
    "#ca8a04",  # Gold
    "#ffe4e6",
    "#e11d48",  # Quarantine
}
# Legacy palette values blocked in style/classDef rules.
DEPRECATED_PALETTE = {
    # Material palette (superseded by muted 2026 palette).
    "#ecfdf5",
    "#10b981",
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


def _is_flowchart(lines: list[str]) -> bool:
    """Detect whether diagram body is flowchart/graph (vs class/sequence/state)."""
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if s.startswith("%%"):
            continue
        if _GRAPH_LINE_RE.match(s):
            return True
        if _NON_FLOW_RE.match(s):
            return False
        return False
    return False


def _iter_edge_lines(lines: list[str]) -> list[str]:
    """Return non-comment flow edges containing Mermaid arrow tokens."""
    edges: list[str] = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue
        if s.startswith("linkStyle"):
            continue
        if "-->" in s or "-.->" in s or "==>" in s:
            edges.append(s)
    return edges


def _parse_class_method_signature(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped[0] not in "+-#~":
        return None

    payload = stripped[1:].lstrip()
    method_name, separator, remainder = payload.partition("(")
    if not separator:
        return None

    method_name = method_name.strip()
    if not method_name:
        return None
    if not (method_name[0].isalpha() or method_name[0] in {"_", "\\"}):
        return None
    if any(not (char.isalnum() or char in {"_", "\\"}) for char in method_name):
        return None

    closing_paren = remainder.find(")")
    if closing_paren < 0:
        return None
    return method_name, remainder[closing_paren + 1 :]


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
            not f.name.startswith("_") and not EXCLUDED_PATH_PARTS.intersection(f.parts)
        )
    )


def _missing_mmd_metadata_tags(lines: list[str]) -> list[str]:
    required_tags = {"@version", "@date", "@type", "@level"}
    stripped_lines = [line.strip() for line in lines]
    found_tags = {
        tag
        for tag in required_tags
        if any(line.startswith(f"%% {tag}") for line in stripped_lines)
    }
    return sorted(required_tags - found_tags)


def _has_mermaid_view_metadata(lines: list[str]) -> bool:
    return any(
        line.strip().startswith("%% View:") or line.strip().startswith("%% @view")
        for line in lines
    )


def check_metadata_headers(path: Path, lines: list[str]) -> list[Issue]:
    """Check for structured metadata; format depends on file type/location."""
    issues: list[Issue] = []
    fname = str(path)

    if path.suffix == ".mmd":
        for tag in _missing_mmd_metadata_tags(lines):
            issues.append(
                Issue(
                    file=fname,
                    severity="WARNING",
                    rule="META-001",
                    message=f"Missing metadata: %% {tag}",
                )
            )
    else:
        if not _has_mermaid_view_metadata(lines):
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
        line for line in lines if line.strip() and not line.strip().startswith("%%")
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
    updated_label = "%% Updated:"
    date_label_token = "%% @date"
    issues: list[Issue] = []
    fname = str(path)

    date_str: str | None = None
    date_label: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(updated_label):
            date_str = stripped.replace(updated_label, "").strip()
            date_label = updated_label
            break
        if stripped.startswith(date_label_token):
            date_str = stripped.replace(date_label_token, "").strip()
            date_label = date_label_token
            break

    if date_str is None:
        return issues

    updated_date = _parse_staleness_date(
        fname=fname,
        date_label=date_label,
        date_str=date_str,
    )
    if updated_date is None:
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

    issues.extend(
        _staleness_issues(
            fname=fname,
            age=datetime.now() - updated_date,
            stale_days=stale_days,
        )
    )
    return issues


def _parse_staleness_date(
    *,
    fname: str,
    date_label: str | None,
    date_str: str,
) -> datetime | None:
    del fname, date_label
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def _staleness_issues(
    *,
    fname: str,
    age: timedelta,
    stale_days: int,
) -> list[Issue]:
    if age > timedelta(days=WARNING_STALE_DAYS):
        return [
            Issue(
                file=fname,
                severity="ERROR",
                rule="STALE-001",
                message=f"Diagram is {age.days} days old (>{WARNING_STALE_DAYS}d threshold)",
            )
        ]
    if age > timedelta(days=stale_days):
        return [
            Issue(
                file=fname,
                severity="WARNING",
                rule="STALE-002",
                message=f"Diagram is {age.days} days old (>{stale_days}d threshold)",
            )
        ]
    return []


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
            if normalized in DEPRECATED_PALETTE and normalized not in CANONICAL_PALETTE:
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

    has_decomposed_siblings = _has_decomposed_siblings(path)

    if nodes > SIZE_ERROR_THRESHOLD:
        if has_decomposed_siblings:
            issues.append(
                Issue(
                    file=fname,
                    severity="WARNING",
                    rule="SIZE-003",
                    message=(
                        f"@nodes={nodes} > {SIZE_ERROR_THRESHOLD}, "
                        "but decomposed sibling views are present (01a/01b/... pattern)"
                    ),
                )
            )
            return issues
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


def _has_decomposed_siblings(path: Path) -> bool:
    """Check whether a canonical full diagram already has focused siblings."""
    if path.suffix != ".mmd":
        return False
    prefix = path.stem.split("-", 1)[0]
    sibling_pattern = f"{prefix}[a-z]-*.mmd"
    return any(path.parent.glob(sibling_pattern))


def _uses_flowchart_layout_policy(lines: list[str]) -> bool:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        return bool(_GRAPH_LINE_RE.match(stripped))
    return False


def _extract_layout_nodes(lines: list[str]) -> int | None:
    for line in lines:
        match = _NODES_RE.search(line)
        if match:
            return int(match.group(1))
    return None


def _extract_edge_routing(lines: list[str]) -> str | None:
    for line in lines:
        match = _EDGE_ROUTING_VALUE_RE.search(line)
        if match:
            return match.group(1).upper()
    return None


def check_layout_policy(path: Path, lines: list[str]) -> list[Issue]:
    """Check adaptive layout rules (ADR-040).

    LAYOUT-001: flowchart/graph with @nodes > 20 and no ELK init → WARNING
    LAYOUT-002: flowchart/graph with @nodes > 40 and no ELK init → ERROR
    LAYOUT-003: ELK flowchart with edgeRouting=POLYLINE (no override marker) → WARNING
    """
    issues: list[Issue] = []
    fname = str(path)

    if path.suffix != ".mmd":
        return issues

    if not _uses_flowchart_layout_policy(lines):
        return issues

    nodes = _extract_layout_nodes(lines)
    if nodes is None:
        return issues

    has_elk = any(_has_elk_layout_init(ln) for ln in lines)
    edge_routing = _extract_edge_routing(lines)
    allow_polyline = any(
        "@allow-polyline-routing" in ln or "@allow-polyline" in ln for ln in lines
    )

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
    elif has_elk and edge_routing == "POLYLINE" and not allow_polyline:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LAYOUT-003",
                message=(
                    "ELK flowchart uses edgeRouting=POLYLINE; prefer ORTHOGONAL for "
                    "consistent link geometry (add %% @allow-polyline-routing to opt out)"
                ),
            )
        )

    return issues


def check_link_semantics(path: Path, lines: list[str]) -> list[Issue]:
    """Check semantic arrow diversity in dense flowcharts — LINK-001 (WARNING).

    For flowcharts with enough edges, using only one arrow style makes
    interaction semantics hard to read.
    """
    issues: list[Issue] = []
    fname = str(path)

    if not _is_flowchart(lines):
        return issues
    if path.name.startswith("00-legend"):
        return issues

    edges = _iter_edge_lines(lines)
    if len(edges) < 8:
        return issues

    has_solid = any("-->" in e for e in edges)
    has_dashed = any("-.->" in e for e in edges)
    has_thick = any("==>" in e for e in edges)
    style_count = sum([has_solid, has_dashed, has_thick])

    if style_count < 2:
        # Some diagrams intentionally keep one arrow token and encode semantics
        # via differentiated linkStyle groups. Treat that as semantically valid.
        linkstyle_styles: set[str] = set()
        for ln in lines:
            parsed = _parse_link_style_line(ln)
            if parsed is None:
                continue
            target, style_payload = parsed
            if target == "default":
                continue
            linkstyle_styles.add(style_payload)
        if len(linkstyle_styles) >= 2:
            return issues

        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LINK-001",
                message=(
                    f"Flowchart has {len(edges)} edge(s) but only one arrow semantic style. "
                    "Use a semantic mix (--> runtime, -.-> DI/implements, ==> critical data path)."
                ),
            )
        )
    return issues


def check_linkstyle_index_fragility(path: Path, lines: list[str]) -> list[Issue]:
    """Check brittle linkStyle index usage — LINK-002 (WARNING).

    Long index lists in linkStyle are fragile: inserting one edge shifts indices.
    """
    issues: list[Issue] = []
    fname = str(path)

    if not _is_flowchart(lines):
        return issues

    groups: list[int] = []
    styles: list[str] = []
    for ln in lines:
        parsed = _parse_link_style_line(ln)
        if parsed is None:
            continue
        target, style_payload = parsed
        if target == "default":
            continue
        if re.fullmatch(r"\d+(,\d+)*", target):
            groups.append(len(target.split(",")))
            styles.append(style_payload)

    if not groups:
        return issues

    singleton_count = sum(1 for g in groups if g == 1)
    singleton_ratio = singleton_count / len(groups)
    unique_styles = len(set(styles))

    # Warn on brittle patterns only:
    # - many singleton linkStyle lines (index-by-index mapping), or
    # - many style lines with very low style diversity (typically repetitive copy-paste).
    if (len(groups) >= 20 and singleton_ratio >= 0.85 and unique_styles <= 3) or (
        len(groups) >= 12 and math.isclose(singleton_ratio, 1.0) and unique_styles == 1
    ):
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LINK-002",
                message=(
                    "Fragile linkStyle singleton-index pattern detected "
                    f"(groups={groups}, singleton={singleton_count}/{len(groups)}, "
                    f"styles={unique_styles}). "
                    "Prefer grouped mappings and semantic arrow types."
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


def _extract_node_decl_labels(line: str) -> list[str]:
    """Extract quoted labels from node declaration lines.

    Skip edges and subgraph declarations to avoid noisy false positives from
    relationship labels.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("%%"):
        return []
    if _SUBGRAPH_RE.match(stripped):
        return []
    if "-->" in stripped or "-.->" in stripped or "==>" in stripped:
        return []
    return [m.group(1) for m in _QUOTED_LABEL_RE.finditer(stripped)]


def _normalize_label_fragment(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _record_label_readability_observations(
    *,
    line_no: int,
    raw_label: str,
    long_segments: list[str],
    over_tall_labels: list[str],
    padded_labels: list[int],
) -> None:
    if re.search(
        rf"(?:<br\s*/?>\s*){{{LABEL_WARN_PADDING_BREAKS},}}",
        raw_label,
        flags=re.IGNORECASE,
    ):
        padded_labels.append(line_no)

    split_parts = _BR_RE.split(raw_label)
    normalized_parts = [
        _normalize_label_fragment(_HTML_TAG_RE.sub("", part)) for part in split_parts
    ]
    nonempty_parts = [part for part in normalized_parts if part]

    if len(nonempty_parts) > LABEL_WARN_MAX_LINES:
        over_tall_labels.append(f"L{line_no}:{len(nonempty_parts)}")

    for part in nonempty_parts:
        if len(part) <= LABEL_WARN_LINE_CHARS:
            continue
        sample = part[:32]
        if len(part) > 32:
            sample += "..."
        long_segments.append(f"L{line_no}:{len(part)}:'{sample}'")


def check_label_readability(path: Path, lines: list[str]) -> list[Issue]:
    """Check node-label readability heuristics — LABEL-001/002/003 (WARNING)."""
    issues: list[Issue] = []
    fname = str(path)

    if path.suffix != ".mmd":
        return issues

    long_segments: list[str] = []
    over_tall_labels: list[str] = []
    padded_labels: list[int] = []

    for line_no, line in enumerate(lines, start=1):
        labels = _extract_node_decl_labels(line)
        if not labels:
            continue

        for raw_label in labels:
            _record_label_readability_observations(
                line_no=line_no,
                raw_label=raw_label,
                long_segments=long_segments,
                over_tall_labels=over_tall_labels,
                padded_labels=padded_labels,
            )

    if long_segments:
        preview = ", ".join(long_segments[:4])
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LABEL-001",
                message=(
                    "Long node label line(s) detected "
                    f"(>{LABEL_WARN_LINE_CHARS} chars): {preview}"
                ),
            )
        )

    if over_tall_labels:
        preview = ", ".join(over_tall_labels[:4])
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LABEL-002",
                message=(
                    "Node label has too many lines "
                    f"(>{LABEL_WARN_MAX_LINES}): {preview}"
                ),
            )
        )

    if padded_labels:
        first = padded_labels[:5]
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="LABEL-003",
                message=(
                    "Excessive <br/> padding detected in node labels "
                    f"(runs >= {LABEL_WARN_PADDING_BREAKS}, lines: {first})"
                ),
            )
        )

    return issues


def _collect_class_method_render_observations(
    lines: list[str],
) -> tuple[list[int], list[int], list[int], list[tuple[int, int, str]]]:
    offenders: list[int] = []
    colon_return_lines: list[int] = []
    bare_return_lines: list[int] = []
    long_method_lines: list[tuple[int, int, str]] = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue

        if _UNESCAPED_DUNDER_METHOD_RE.search(stripped):
            offenders.append(idx)

        parsed_signature = _parse_class_method_signature(stripped)
        if not parsed_signature:
            continue

        method_name = parsed_signature[0].replace("\\_", "_")
        tail = parsed_signature[1].strip()
        if tail:
            target_lines = (
                colon_return_lines if tail.startswith(":") else bare_return_lines
            )
            target_lines.append(idx)

        if len(stripped) > CLASS_METHOD_WARN_LINE_CHARS:
            long_method_lines.append((idx, len(stripped), method_name))

    return offenders, colon_return_lines, bare_return_lines, long_method_lines


def check_class_method_render_safety(path: Path, lines: list[str]) -> list[Issue]:
    """Check classDiagram method signatures for known render pitfalls."""
    issues: list[Issue] = []
    fname = str(path)

    if "class-diagrams" not in path.parts:
        return issues

    if not any(_CLASS_DIAGRAM_RE.match(line) for line in lines):
        return issues

    offenders, colon_return_lines, bare_return_lines, long_method_lines = (
        _collect_class_method_render_observations(lines)
    )

    if offenders:
        first = ", ".join(str(x) for x in offenders[:6])
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="CLASS-001",
                message=(
                    "Unescaped dunder method in classDiagram can lose underscores in SVG/PDF. "
                    f"Use escaped form like '+\\_\\_enter\\_\\_()'. Lines: {first}"
                ),
            )
        )

    if colon_return_lines and bare_return_lines:
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="CLASS-002",
                message=(
                    "Mixed method return notation in classDiagram "
                    "(both '): Type' and ') Type'). "
                    f"Colon lines: {', '.join(str(x) for x in colon_return_lines[:4])}; "
                    f"bare lines: {', '.join(str(x) for x in bare_return_lines[:4])}"
                ),
            )
        )

    if long_method_lines:
        preview = ", ".join(
            f"L{line_no}:{length}({name})"
            for line_no, length, name in long_method_lines[:6]
        )
        issues.append(
            Issue(
                file=fname,
                severity="WARNING",
                rule="CLASS-003",
                message=(
                    "Overlong method signature may wrap poorly in SVG/PDF "
                    f"(>{CLASS_METHOD_WARN_LINE_CHARS} chars): {preview}"
                ),
            )
        )

    return issues


def _has_elk_layout_init(line: str) -> bool:
    lowered = line.lower()
    return "%%{init" in lowered and "layout" in lowered and "elk" in lowered


def _parse_link_style_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("linkStyle "):
        return None
    payload = stripped[len("linkStyle ") :].strip()
    if not payload:
        return None
    parts = payload.split(maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[0], " ".join(parts[1].split())


def check_orphan_nodes(path: Path, lines: list[str]) -> list[Issue]:
    """Check for orphan nodes — GRAPH-001 (WARNING, ADR-040 D6).

    Delegates to prune_orphan_nodes parser for flowchart/graph and
    sequenceDiagram files only.  classDiagram and other types are skipped.
    """
    import sys as _sys

    _sys.path.insert(0, str(Path(__file__).parent))
    try:
        from scripts.diagrams.prune_orphan_nodes import (
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
                    "scripts/diagrams/prune_orphan_nodes.py --fix"
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

    return _collect_file_issues(path=path, lines=lines, stale_days=stale_days)


def _collect_file_issues(
    path: Path, *, lines: list[str], stale_days: int
) -> list[Issue]:
    """Collect all lint issues for a parsed diagram file."""
    issue_groups = (
        check_metadata_headers(path, lines),
        check_naming_convention(path),
        check_placeholder_content(path, lines),
        check_staleness(path, lines, stale_days),
        check_colour_policy(path, lines),
        check_subgraph_emoji(path, lines),
        check_node_count_policy(path, lines),
        check_layout_policy(path, lines),
        check_link_semantics(path, lines),
        check_linkstyle_index_fragility(path, lines),
        check_nbsp_padding(path, lines),
        check_label_readability(path, lines),
        check_class_method_render_safety(path, lines),
        check_orphan_nodes(path, lines),
    )
    issues: list[Issue] = []
    for group in issue_groups:
        issues.extend(group)
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
    for path in _collect_target_files(targets):
        result.files_checked += 1
        file_issues = lint_file(path, stale_days)
        if not any(i.severity == "ERROR" for i in file_issues):
            result.files_passed += 1
        result.issues.extend(file_issues)

    return result


def _collect_target_files(targets: list[Path]) -> list[Path]:
    """Collect unique diagram files from explicit file and directory targets."""
    seen: set[Path] = set()
    files: list[Path] = []

    for target in targets:
        if _is_explicit_supported_file(target) and target not in seen:
            seen.add(target)
            files.append(target)
            continue
        for path in find_diagram_files(target):
            if path in seen:
                continue
            seen.add(path)
            files.append(path)

    return sorted(files)


def _is_explicit_supported_file(path: Path) -> bool:
    """Return whether a target path is a supported direct diagram file."""
    return (
        path.is_file()
        and path.suffix in SUPPORTED_SUFFIXES
        and not EXCLUDED_PATH_PARTS.intersection(path.parts)
    )


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
                marker = {"ERROR": "E", "WARNING": "W", "INFO": "I"}[issue.severity]
                lines.append(f"    [{marker}] {issue.rule}: {issue.message}")
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

    def _out(message: str) -> None:
        sys.stdout.write(f"{message}\n")

    def _err(message: str) -> None:
        sys.stderr.write(f"{message}\n")

    missing_targets = [t for t in targets if not t.exists()]
    if missing_targets:
        for target in missing_targets:
            _err(f"Error: {target} does not exist")
        return 2

    result = lint_paths(targets, args.stale_days)

    if args.json_output:
        _out(format_json(result))
    else:
        _out(format_text(result))

    return 1 if result.has_errors else 0


if __name__ == "__main__":
    sys.exit(main())
