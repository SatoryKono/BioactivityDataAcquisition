#!/usr/bin/env python3
"""
uniform_diagram_sizes.py — Normalize object sizes in Mermaid diagrams.

For each diagram file, determines the maximum width (by longest visible text
line) and maximum height (by most content lines) across all objects, then
pads every object to those dimensions using &nbsp; characters.

Supports groupwise sizing: when @uniform-group tags are present, objects
within each group are normalized to their group's max height rather than
the global max. Width strategy can be controlled via:
  %% @uniform-width global   (default, globally uniform width)
  %% @uniform-width group    (group-local width)
Objects not assigned to any group go into an implicit "default" group.

Supports two diagram types:
  - classDiagram:  class Name { ... } blocks
  - flowchart/graph:  ID["Label<br/>line2<br/>..."] nodes

Usage:
    # Check all diagrams (exit 1 on drift)
    python scripts/diagrams/uniform_diagram_sizes.py --check

    # Fix all diagrams in-place
    python scripts/diagrams/uniform_diagram_sizes.py --fix

    # Dry-run: show diff without writing
    python scripts/diagrams/uniform_diagram_sizes.py --dry-run

    # Process specific files
    python scripts/diagrams/uniform_diagram_sizes.py --fix -f docs/.../01-domain-ports.mmd

    # Process specific directory
    python scripts/diagrams/uniform_diagram_sizes.py --fix --dir docs/.../class-diagrams

Groupwise sizing (add to .mmd file header):
    %% @uniform-group base    nodes=BaseHttpAdapter,BaseSyncAdapter
    %% @uniform-group adapter nodes=ChemblAdapter,PubMedAdapter,...
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[2]
for candidate in (SCRIPT_DIR, REPO_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

try:
    from .diagram_paths import source_dir
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.diagram_paths import source_dir

# ── Defaults ────────────────────────────────────────────────────────────────

DIAGRAM_DIRS = [
    source_dir("architecture"),
    source_dir("class-diagrams"),
    source_dir("foundation"),
]
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}

# ── ANSI colours ────────────────────────────────────────────────────────────

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

# ── Regex patterns ──────────────────────────────────────────────────────────

_CLASS_DIAGRAM_RE = re.compile(r"^\s*classDiagram\b", re.IGNORECASE)
_FLOWCHART_RE = re.compile(r"^\s*(graph|flowchart)\b", re.IGNORECASE)
_CLASS_BLOCK_START_RE = re.compile(r"^\s+class\s+(\w+)\s*\{")
_CLASS_BLOCK_END_RE = re.compile(r"^\s+\}")
_UNIFORM_TAG_RE = re.compile(r"^%% @uniform(?:\s|$).*$")
_UNIFORM_STATS_RE = re.compile(r"^%% @uniform-stats\b.*$")
_UNIFORM_GROUP_RE = re.compile(r"^%%\s*@uniform-group\s+(\S+)\s+nodes=(.+)$")
_UNIFORM_WIDTH_RE = re.compile(
    r"^%%\s*@uniform-width\s+(global|group|grouped)\s*$",
    re.IGNORECASE,
)
_NBSP = "&nbsp;"


def _ensure_repo_path(path: Path) -> Path:
    repo_root = SCRIPT_DIR.parents[1].resolve()
    resolved_path = path.resolve()
    if repo_root != resolved_path and repo_root not in resolved_path.parents:
        raise ValueError(
            f"refusing to process path outside {repo_root}: {resolved_path}"
        )
    return resolved_path


def _write_repo_text(safe_path: Path, content: str) -> None:
    """Write normalized diagram text to a previously validated repository path."""
    safe_path.write_text(  # NOSONAR - safe_path is validated by _ensure_repo_path
        content,
        encoding="utf-8",
    )


# Flowchart node patterns:
#   ID["Label text"]         — rectangle
#   ID(["Label text"])       — rounded
#   ID[("Label text")]       — cylinder
#   ID(("Label text"))       — circle
#   ID{{"Label text"}}       — hexagon
# We capture: ID, opening bracket sequence, label content, closing bracket sequence
_FLOWCHART_NODE_RE = re.compile(
    r"^(\s+)"  # leading indent
    r"(\w+)"  # node ID
    r'(\["|\(\["|\[\("|\(\("|\{\{")'  # opening brackets
    r"(.+?)"  # label content (non-greedy)
    r'("\]|"\)\]|"\)\]|"\)\)|"\}\})'  # closing brackets
    r"\s*$"  # trailing whitespace
)


# ── Data structures ─────────────────────────────────────────────────────────


@dataclass
class ClassBlock:
    """A parsed class block from a classDiagram."""

    name: str
    start_line: int  # index in file lines (0-based), the `class Name {` line
    end_line: int  # index of the closing `}`
    stereotype_line: str | None  # e.g. "<<Protocol>>" with existing padding
    content_lines: list[str]  # real content lines (stripped of padding &nbsp;)
    padding_lines: int  # count of trailing &nbsp;-only lines
    raw_lines: list[str]  # original lines between { and } (exclusive)
    indent: str  # whitespace prefix for body lines


@dataclass
class FlowchartNode:
    """A parsed flowchart node."""

    node_id: str
    line_index: int
    indent: str
    open_bracket: str
    close_bracket: str
    label_parts: list[str]  # split by <br/>
    content_parts: list[str]  # label_parts stripped of &nbsp; padding
    raw_label: str


@dataclass
class UniformStats:
    """Computed uniform dimensions for a diagram."""

    max_visible_width: int  # in characters (longest line across all objects)
    max_total_body: int  # total body lines (stereotype + content) max
    max_title_len: int  # longest class/node name


@dataclass
class UniformGroup:
    """A named group of objects that share uniform height."""

    name: str
    node_names: set[str]


# ── Group parsing ──────────────────────────────────────────────────────────


def _parse_uniform_groups(lines: list[str]) -> list[UniformGroup]:
    """Parse all @uniform-group tags from file header comments."""
    groups: list[UniformGroup] = []
    for line in lines:
        m = _UNIFORM_GROUP_RE.match(line.strip())
        if m:
            group_name = m.group(1)
            node_names = {n.strip() for n in m.group(2).split(",") if n.strip()}
            groups.append(UniformGroup(name=group_name, node_names=node_names))
    return groups


def _parse_uniform_width_strategy(lines: list[str]) -> str:
    """Parse optional @uniform-width strategy; default is 'global'."""
    for line in lines:
        match = _UNIFORM_WIDTH_RE.match(line.strip())
        if not match:
            continue
        raw = match.group(1).lower()
        return "group" if raw in {"group", "grouped"} else "global"
    return "global"


def _assign_groups(
    object_names: list[str],
    groups: list[UniformGroup],
) -> dict[str, str]:
    """Return mapping of object_name -> group_name.

    Unassigned objects go into the 'default' group.
    Raises ValueError if a name appears in multiple groups.
    """
    assignment: dict[str, str] = {}
    for g in groups:
        for name in g.node_names:
            if name in assignment:
                raise ValueError(
                    f"Node '{name}' assigned to multiple groups: "
                    f"'{assignment[name]}' and '{g.name}'"
                )
            assignment[name] = g.name
    for name in object_names:
        if name not in assignment:
            assignment[name] = "default"
    return assignment


_DiagramItem = TypeVar("_DiagramItem", ClassBlock, FlowchartNode)


def _partition_by_group(
    items: list[_DiagramItem],
    assignment: dict[str, str],
) -> dict[str, list[_DiagramItem]]:
    """Partition items into groups based on assignment map."""
    groups: dict[str, list[_DiagramItem]] = {}
    for item in items:
        name = item.name if isinstance(item, ClassBlock) else item.node_id
        g = assignment.get(name, "default")
        groups.setdefault(g, []).append(item)
    return groups


# ── Helpers ─────────────────────────────────────────────────────────────────


def _strip_nbsp(text: str) -> str:
    """Remove trailing &nbsp; sequences from text."""
    while text.endswith(_NBSP):
        text = text[: -len(_NBSP)]
    return text.rstrip()


def _count_visual_chars(text: str) -> int:
    """Count visual character width, treating &nbsp; as 1 char."""
    clean = text.replace(_NBSP, " ")
    return len(clean)


def _is_nbsp_only(text: str) -> bool:
    """Check if line consists only of &nbsp; and whitespace."""
    return text.strip().replace(_NBSP, "").strip() == ""


def _pad_width(text: str, target_width: int) -> str:
    """Pad text with &nbsp; to reach target visual width."""
    current = _count_visual_chars(text)
    if current >= target_width:
        return text
    needed = target_width - current
    return text + _NBSP * needed


# ── Class diagram parser ───────────────────────────────────────────────────


def _detect_diagram_type(lines: list[str]) -> str | None:
    """Detect whether file is classDiagram or flowchart."""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            if stripped.startswith("%%{"):
                continue
            continue
        if _CLASS_DIAGRAM_RE.match(stripped):
            return "class"
        if _FLOWCHART_RE.match(stripped):
            return "flowchart"
        return None
    return None


def _parse_class_blocks(lines: list[str]) -> list[ClassBlock]:
    """Parse all class blocks from classDiagram lines."""
    blocks: list[ClassBlock] = []
    i = 0
    while i < len(lines):
        m = _CLASS_BLOCK_START_RE.match(lines[i])
        if m:
            name = m.group(1)
            start = i
            end, body_lines = _class_block_body(lines, start)
            indent = _class_block_indent(body_lines)
            stereotype_line, content_lines, padding_count = _class_block_parts(
                body_lines
            )
            blocks.append(
                _build_class_block(
                    name=name,
                    start=start,
                    end=end,
                    body_lines=body_lines,
                    indent=indent,
                    stereotype_line=stereotype_line,
                    content_lines=content_lines,
                    padding_count=padding_count,
                )
            )
            i = end + 1
        else:
            i += 1

    return blocks


def _class_block_body(lines: list[str], start: int) -> tuple[int, list[str]]:
    """Return closing index and raw body lines for one class block."""
    j = start + 1
    body_lines: list[str] = []
    while j < len(lines):
        if _CLASS_BLOCK_END_RE.match(lines[j]):
            break
        body_lines.append(lines[j])
        j += 1
    return j, body_lines


def _class_block_indent(body_lines: list[str]) -> str:
    """Infer body indent from the first non-empty line."""
    for body_line in body_lines:
        if body_line.strip():
            return body_line[: len(body_line) - len(body_line.lstrip())]
    return "        "


def _class_block_parts(
    body_lines: list[str],
) -> tuple[str | None, list[str], int]:
    """Split raw body lines into stereotype, visible content, and padding."""
    stereotype_line: str | None = None
    content_lines: list[str] = []
    padding_count = 0
    for body_line in body_lines:
        stripped = body_line.strip()
        if _is_stereotype_candidate(stereotype_line, stripped):
            stereotype_line = stripped
            continue
        if _is_nbsp_only(stripped):
            padding_count += 1
            continue
        content_lines, padding_count = _append_visible_class_content(
            content_lines,
            padding_count,
            stripped,
        )
    return stereotype_line, content_lines, padding_count


def _is_stereotype_candidate(
    stereotype_line: str | None,
    stripped: str,
) -> bool:
    """Return whether the stripped line should be treated as a stereotype."""
    return stereotype_line is None and stripped.startswith("<<")


def _append_visible_class_content(
    content_lines: list[str],
    padding_count: int,
    stripped: str,
) -> tuple[list[str], int]:
    """Append visible class content while preserving interior blank separators."""
    if padding_count > 0 and content_lines:
        content_lines.extend([""] * padding_count)
        padding_count = 0
    if stripped:
        content_lines.append(stripped)
    return content_lines, padding_count


def _build_class_block(
    *,
    name: str,
    start: int,
    end: int,
    body_lines: list[str],
    indent: str,
    stereotype_line: str | None,
    content_lines: list[str],
    padding_count: int,
) -> ClassBlock:
    """Build a parsed ClassBlock container."""
    return ClassBlock(
        name=name,
        start_line=start,
        end_line=end,
        stereotype_line=stereotype_line,
        content_lines=content_lines,
        padding_lines=padding_count,
        raw_lines=body_lines,
        indent=indent,
    )


def _compute_class_uniform(blocks: list[ClassBlock]) -> UniformStats:
    """Compute uniform dimensions across all class blocks.

    Height is computed as total body lines (stereotype + content), so
    classes with and without stereotypes get the same rendered height.
    """
    max_title = 0
    max_total_body = 0
    max_width = 0

    for b in blocks:
        # Title length (class name)
        max_title = max(max_title, len(b.name))

        # Total body = stereotype (0 or 1) + content lines
        stripped_content = [_strip_nbsp(c) for c in b.content_lines]
        total_body = (1 if b.stereotype_line else 0) + len(stripped_content)
        max_total_body = max(max_total_body, total_body)

        # Max visible width across all visible lines in block
        all_visible: list[str] = []
        if b.stereotype_line:
            all_visible.append(_strip_nbsp(b.stereotype_line))
        all_visible.extend(stripped_content)

        for line in all_visible:
            max_width = max(max_width, _count_visual_chars(line))

    return UniformStats(
        max_visible_width=max_width,
        max_total_body=max_total_body,
        max_title_len=max_title,
    )


def _rebuild_class_block(
    block: ClassBlock,
    stats: UniformStats,
) -> list[str]:
    """Rebuild a class block with uniform padding.

    Total body lines = stereotype (0 or 1) + content + padding = max_total_body.
    """
    result: list[str] = []

    # Stereotype line (pad width)
    if block.stereotype_line:
        stripped_stereo = _strip_nbsp(block.stereotype_line)
        padded = _pad_width(stripped_stereo, stats.max_visible_width)
        result.append(f"{block.indent}{padded}")

    # Content lines (pad width)
    stripped_content = [_strip_nbsp(c) for c in block.content_lines]
    for line in stripped_content:
        if line:
            padded = _pad_width(line, stats.max_visible_width)
            result.append(f"{block.indent}{padded}")
        else:
            result.append(f"{block.indent}{_NBSP}")

    # Height padding: total body (stereo + content + padding) = max_total_body
    current_body = (1 if block.stereotype_line else 0) + len(stripped_content)
    pad_needed = stats.max_total_body - current_body
    for _ in range(pad_needed):
        result.append(f"{block.indent}{_NBSP}")

    return result


def _normalize_class_diagram(lines: list[str]) -> list[str]:
    """Normalize all class blocks in a classDiagram to uniform sizes.

    When @uniform-group tags are present, height is normalized per-group
    while width stays globally uniform.  Without groups, all blocks share
    a single global uniform (backward compatible).
    """
    blocks = _parse_class_blocks(lines)
    if not blocks:
        return lines

    groups = _parse_uniform_groups(lines)
    width_strategy = _parse_uniform_width_strategy(lines)
    stats_map, group_stats = _resolve_class_uniform_stats(
        blocks=blocks,
        groups=groups,
        width_strategy=width_strategy,
    )
    result = _rebuild_class_diagram_lines(lines, blocks, stats_map)
    if group_stats is not None:
        return _update_uniform_tag_grouped(
            result,
            group_stats,
            groups,
            "class",
            width_strategy=width_strategy,
        )
    stats = next(iter(stats_map.values()))
    return _update_uniform_tag(result, stats, "class")


def _resolve_class_uniform_stats(
    *,
    blocks: list[ClassBlock],
    groups: list[UniformGroup],
    width_strategy: str,
) -> tuple[dict[str, UniformStats], dict[str, UniformStats] | None]:
    """Resolve per-block stats, optionally with grouped sizing."""
    if not groups:
        stats = _compute_class_uniform(blocks)
        return {block.name: stats for block in blocks}, None

    assignment = _assign_groups([block.name for block in blocks], groups)
    grouped_blocks = _partition_by_group(blocks, assignment)
    group_stats = _build_group_stats(grouped_blocks, width_strategy)
    return (
        {block.name: group_stats[assignment[block.name]] for block in blocks},
        group_stats,
    )


def _build_group_stats(
    grouped_blocks: dict[str, list[ClassBlock]],
    width_strategy: str,
) -> dict[str, UniformStats]:
    """Build per-group uniform stats and optionally normalize width globally."""
    group_stats_raw = {
        group_name: _compute_class_uniform(group_blocks)
        for group_name, group_blocks in grouped_blocks.items()
    }
    if width_strategy != "global":
        return dict(group_stats_raw)

    global_max_width = max(
        stats.max_visible_width for stats in group_stats_raw.values()
    )
    global_max_title = max(stats.max_title_len for stats in group_stats_raw.values())
    return {
        group_name: UniformStats(
            max_visible_width=global_max_width,
            max_total_body=stats.max_total_body,
            max_title_len=global_max_title,
        )
        for group_name, stats in group_stats_raw.items()
    }


def _rebuild_class_diagram_lines(
    lines: list[str],
    blocks: list[ClassBlock],
    stats_map: dict[str, UniformStats],
) -> list[str]:
    """Rebuild classDiagram contents with normalized block bodies."""
    result: list[str] = []
    block_map: dict[int, ClassBlock] = {b.start_line: b for b in blocks}
    skip_until: int | None = None

    for i, line in enumerate(lines):
        if skip_until is not None:
            if i <= skip_until:
                continue
            skip_until = None

        if i in block_map:
            b = block_map[i]
            result.append(line)
            result.extend(_rebuild_class_block(b, stats_map[b.name]))
            result.append(lines[b.end_line])
            skip_until = b.end_line
        else:
            result.append(line)
    return result


# ── Flowchart parser ────────────────────────────────────────────────────────


def _parse_flowchart_nodes(lines: list[str]) -> list[FlowchartNode]:
    """Parse flowchart nodes that use multi-line labels (with <br/>)."""
    nodes: list[FlowchartNode] = []

    for i, line in enumerate(lines):
        m = _FLOWCHART_NODE_RE.match(line)
        if m:
            indent = m.group(1)
            node_id = m.group(2)
            open_br = m.group(3)
            raw_label = m.group(4)
            close_br = m.group(5)

            # Split by <br/> (case insensitive)
            parts = re.split(r"<br/?>", raw_label, flags=re.IGNORECASE)
            content_parts = [_strip_nbsp(p) for p in parts]

            nodes.append(
                FlowchartNode(
                    node_id=node_id,
                    line_index=i,
                    indent=indent,
                    open_bracket=open_br,
                    close_bracket=close_br,
                    label_parts=parts,
                    content_parts=content_parts,
                    raw_label=raw_label,
                )
            )

    return nodes


def _compute_flowchart_uniform(nodes: list[FlowchartNode]) -> UniformStats:
    """Compute uniform dimensions for flowchart nodes."""
    max_title = 0
    max_lines = 0
    max_width = 0

    for n in nodes:
        # First part is typically the title
        if n.content_parts:
            max_title = max(max_title, _count_visual_chars(n.content_parts[0]))

        # Number of <br/> parts
        max_lines = max(max_lines, len(n.content_parts))

        # Width of each part
        for part in n.content_parts:
            max_width = max(max_width, _count_visual_chars(part))

    return UniformStats(
        max_visible_width=max_width,
        max_total_body=max_lines,
        max_title_len=max_title,
    )


def _rebuild_flowchart_node(
    node: FlowchartNode,
    stats: UniformStats,
) -> str:
    """Rebuild a flowchart node with uniform padding."""
    # Pad each content part to max width
    padded_parts: list[str] = []
    for part in node.content_parts:
        if part:
            padded_parts.append(_pad_width(part, stats.max_visible_width))
        else:
            padded_parts.append(_NBSP)

    # Height padding: add <br/>&nbsp; lines
    while len(padded_parts) < stats.max_total_body:
        padded_parts.append(_NBSP)

    label = "<br/>".join(padded_parts)
    return f"{node.indent}{node.node_id}{node.open_bracket}{label}{node.close_bracket}"


def _normalize_flowchart(lines: list[str]) -> list[str]:
    """Normalize all flowchart nodes to uniform sizes.

    When @uniform-group tags are present, height is normalized per-group
    while width stays globally uniform.
    """
    nodes = _parse_flowchart_nodes(lines)
    if not nodes:
        return lines

    groups = _parse_uniform_groups(lines)
    width_strategy = _parse_uniform_width_strategy(lines)
    stats_map, group_stats, stats = _resolve_flowchart_uniform_stats(
        nodes=nodes,
        groups=groups,
        width_strategy=width_strategy,
    )
    replacements = _build_flowchart_replacements(nodes, stats_map)

    result: list[str] = []
    for i, line in enumerate(lines):
        if i in replacements:
            result.append(replacements[i])
        else:
            result.append(line)

    if group_stats is not None:
        result = _update_uniform_tag_grouped(
            result,
            group_stats,
            groups,
            "flowchart",
            width_strategy=width_strategy,
        )
    else:
        assert stats is not None
        result = _update_uniform_tag(result, stats, "flowchart")

    return result


def _resolve_flowchart_uniform_stats(
    *,
    nodes: list[FlowchartNode],
    groups: list[UniformGroup],
    width_strategy: str,
) -> tuple[
    dict[str, UniformStats], dict[str, UniformStats] | None, UniformStats | None
]:
    """Resolve per-node stats for flowchart nodes, optionally grouped."""
    if not groups:
        stats = _compute_flowchart_uniform(nodes)
        return {node.node_id: stats for node in nodes}, None, stats

    assignment = _assign_groups([node.node_id for node in nodes], groups)
    grouped_nodes = _partition_by_group(nodes, assignment)
    group_stats = _build_flowchart_group_stats(grouped_nodes, width_strategy)
    stats_map = {node.node_id: group_stats[assignment[node.node_id]] for node in nodes}
    return stats_map, group_stats, None


def _build_flowchart_group_stats(
    grouped_nodes: dict[str, list[FlowchartNode]],
    width_strategy: str,
) -> dict[str, UniformStats]:
    """Build grouped flowchart stats and optionally normalize width globally."""
    group_stats_raw = {
        group_name: _compute_flowchart_uniform(group_nodes)
        for group_name, group_nodes in grouped_nodes.items()
    }
    if width_strategy != "global":
        return dict(group_stats_raw)

    global_max_width = max(
        stats.max_visible_width for stats in group_stats_raw.values()
    )
    global_max_title = max(stats.max_title_len for stats in group_stats_raw.values())
    return {
        group_name: UniformStats(
            max_visible_width=global_max_width,
            max_total_body=stats.max_total_body,
            max_title_len=global_max_title,
        )
        for group_name, stats in group_stats_raw.items()
    }


def _build_flowchart_replacements(
    nodes: list[FlowchartNode],
    stats_map: dict[str, UniformStats],
) -> dict[int, str]:
    """Build replacement lines for normalized flowchart nodes."""
    return {
        node.line_index: _rebuild_flowchart_node(node, stats_map[node.node_id])
        for node in nodes
    }


# ── @uniform tag management ─────────────────────────────────────────────────


def _estimate_pixel_dims(
    stats: UniformStats,
) -> tuple[int, int]:
    """Estimate pixel width and height for a UniformStats.

    Returns (est_width, est_height) rounded to nearest 8px.
    """
    title_char_px = 10  # 15px bold font
    body_char_px = 7  # 12-13px regular font
    line_px = 18
    header_px = 36  # class name header height

    title_px = stats.max_title_len * title_char_px
    body_px = stats.max_visible_width * body_char_px
    est_width = max(title_px, body_px)
    est_height = stats.max_total_body * line_px + header_px

    est_width = ((est_width + 7) // 8) * 8
    est_height = ((est_height + 7) // 8) * 8
    return est_width, est_height


def _update_uniform_tag_grouped(
    lines: list[str],
    group_stats: dict[str, UniformStats],
    groups: list[UniformGroup],
    diagram_type: str,
    width_strategy: str = "global",
) -> list[str]:
    """Update @uniform + @uniform-stats tags for grouped normalization.

    Generates:
      %% @uniform class width=304 groups=3
      %% @uniform-stats base    height=180 max_desc_lines=8  nodes=3
      %% @uniform-stats adapter height=126 max_desc_lines=5  nodes=7
    """
    main_tag = _grouped_uniform_main_tag(
        group_stats,
        diagram_type,
        width_strategy,
    )
    stats_lines = _grouped_uniform_stats_lines(group_stats, groups)
    cleaned = _clean_uniform_metadata_lines(lines)
    insert_at = _uniform_tag_insert_index(cleaned)
    return _insert_uniform_metadata_lines(cleaned, insert_at, [main_tag, *stats_lines])


def _grouped_uniform_main_tag(
    group_stats: dict[str, UniformStats],
    diagram_type: str,
    width_strategy: str,
) -> str:
    """Render the top-level grouped @uniform metadata line."""
    global_width = max(_estimate_pixel_dims(stats)[0] for stats in group_stats.values())
    type_prefix = f"{diagram_type} " if diagram_type == "class" else ""
    return (
        f"%% @uniform {type_prefix}width={global_width} "
        f"groups={len(group_stats)} width_strategy={width_strategy}"
    )


def _grouped_uniform_stats_lines(
    group_stats: dict[str, UniformStats],
    groups: list[UniformGroup],
) -> list[str]:
    """Render ordered @uniform-stats lines for grouped normalization."""
    stats_lines: list[str] = []
    for group_name in _ordered_group_names(group_stats, groups):
        if group_name not in group_stats:
            continue
        stats_lines.append(
            _grouped_uniform_stats_line(group_name, group_stats[group_name])
        )
    return stats_lines


def _ordered_group_names(
    group_stats: dict[str, UniformStats],
    groups: list[UniformGroup],
) -> list[str]:
    """Return explicit group order with implicit default group last."""
    ordered_names = [group.name for group in groups]
    if "default" in group_stats and "default" not in ordered_names:
        ordered_names.append("default")
    return ordered_names


def _grouped_uniform_stats_line(group_name: str, stats: UniformStats) -> str:
    """Render one grouped @uniform-stats metadata line."""
    est_w, est_h = _estimate_pixel_dims(stats)
    return (
        f"%% @uniform-stats {group_name:<12s} "
        f"width={est_w} "
        f"height={est_h} "
        f"max_desc_lines={stats.max_total_body}"
    )


def _clean_uniform_metadata_lines(lines: list[str]) -> list[str]:
    """Remove existing uniform metadata lines before reinsertion."""
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if _UNIFORM_TAG_RE.match(stripped) or _UNIFORM_STATS_RE.match(stripped):
            continue
        cleaned.append(line)
    return cleaned


def _uniform_tag_insert_index(lines: list[str]) -> int | None:
    """Find insertion point before init block or diagram declaration."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if (
            _CLASS_DIAGRAM_RE.match(stripped)
            or _FLOWCHART_RE.match(stripped)
            or stripped.startswith("%%{init")
        ):
            return index
    return None


def _insert_uniform_metadata_lines(
    lines: list[str],
    insert_at: int | None,
    metadata_lines: list[str],
) -> list[str]:
    """Insert uniform metadata at the chosen position or append it."""
    if insert_at is None:
        return [*lines, *metadata_lines]
    result = list(lines)
    for offset, tag_line in enumerate(metadata_lines):
        result.insert(insert_at + offset, tag_line)
    return result


def _update_uniform_tag(
    lines: list[str],
    stats: UniformStats,
    diagram_type: str,
) -> list[str]:
    """Update or insert the @uniform metadata tag (non-grouped mode)."""
    est_width, est_height = _estimate_pixel_dims(stats)

    if diagram_type == "class":
        tag = (
            f"%% @uniform class "
            f"width={est_width} height={est_height} "
            f"max_title_len={stats.max_title_len} "
            f"max_desc_lines={stats.max_total_body}"
        )
    else:
        tag = (
            f"%% @uniform "
            f"width={est_width} height={est_height} "
            f"max_title_len={stats.max_title_len} "
            f"max_desc_lines={stats.max_total_body}"
        )

    # Remove any stale @uniform-stats lines (leftover from grouped mode)
    lines = [line for line in lines if not _UNIFORM_STATS_RE.match(line.strip())]

    # Find and replace existing @uniform, or insert before diagram declaration
    for i, line in enumerate(lines):
        if _UNIFORM_TAG_RE.match(line.strip()):
            lines[i] = tag
            return lines

    # Insert before first diagram declaration line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            _CLASS_DIAGRAM_RE.match(stripped)
            or _FLOWCHART_RE.match(stripped)
            or stripped.startswith("%%{init")
        ):
            lines.insert(i, tag)
            return lines

    return lines


# ── Main processing ─────────────────────────────────────────────────────────


def normalize_file(path: Path) -> tuple[str, str, bool]:
    """Normalize a single diagram file.
    Returns (original_content, normalized_content, changed).
    """
    safe_path = _ensure_repo_path(path)
    content = safe_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    dtype = _detect_diagram_type(lines)
    if dtype == "class":
        normalized = _normalize_class_diagram(lines)
    elif dtype == "flowchart":
        normalized = _normalize_flowchart(lines)
    else:
        return content, content, False
    new_content = "\n".join(normalized)
    # Preserve trailing newline
    if content.endswith("\n"):
        new_content += "\n"
    return content, new_content, content != new_content


def find_diagram_files(targets: list[Path]) -> list[Path]:
    """Find all supported diagram files from target paths."""
    files: list[Path] = []
    seen: set[Path] = set()

    for target in targets:
        target = _ensure_repo_path(target)
        if target.is_file():
            _append_diagram_file(target, files, seen)
            continue

        for diagram_file in _iter_supported_diagram_files(target):
            _append_diagram_file(diagram_file, files, seen)

    return sorted(files)


def _append_diagram_file(path: Path, files: list[Path], seen: set[Path]) -> None:
    """Append a supported diagram file exactly once."""
    if path.suffix not in SUPPORTED_SUFFIXES or path in seen:
        return
    if path.name.startswith("_"):
        return
    seen.add(path)
    files.append(path)


def _iter_supported_diagram_files(target: Path) -> list[Path]:
    """Collect supported diagram files under one target directory."""
    diagram_files: list[Path] = []
    for suffix in SUPPORTED_SUFFIXES:
        diagram_files.extend(sorted(target.rglob(f"*{suffix}")))
    return diagram_files


def show_diff(path: Path, original: str, normalized: str) -> None:
    """Print a unified diff for a file."""
    import io

    # Force UTF-8 output to avoid Windows cp1251 encoding errors
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        normalized.splitlines(keepends=True),
        fromfile=f"a/{path.name}",
        tofile=f"b/{path.name}",
        n=2,
    )
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            out.write(f"{GREEN}{line}{NC}")
        elif line.startswith("-") and not line.startswith("---"):
            out.write(f"{RED}{line}{NC}")
        elif line.startswith("@@"):
            out.write(f"{CYAN}{line}{NC}")
        else:
            out.write(line)
    out.flush()
    out.detach()  # prevent closing sys.stdout


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize object sizes in Mermaid diagrams. "
            "Pads all objects to uniform width (by max name length) "
            "and height (by max description lines)."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check for drift (exit 1 if any file needs normalization)",
    )
    mode.add_argument(
        "--fix",
        action="store_true",
        help="Fix files in-place",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Show diffs without writing",
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        type=Path,
        help="Specific files to process",
    )
    parser.add_argument(
        "--dir",
        nargs="+",
        type=Path,
        dest="dirs",
        help="Specific directories to process",
    )

    args = parser.parse_args()

    targets = _cli_targets(args)

    files = find_diagram_files(targets)
    if not files:
        print(f"{YELLOW}No diagram files found.{NC}")
        return 0

    print(f"{BOLD}Uniform Diagram Sizer{NC}")
    print(f"  Files: {len(files)}")
    print()

    changed_count = 0
    checked_count = 0
    error_count = 0

    for path in files:
        checked_count, changed_count, error_count = _process_diagram_file(
            path=path,
            args=args,
            checked_count=checked_count,
            changed_count=changed_count,
            error_count=error_count,
        )

    # Summary
    print()
    print(f"  Checked: {checked_count}")
    if args.fix:
        print(f"  {GREEN}Fixed:   {changed_count}{NC}")
    elif args.check:
        print(f"  Drifted: {changed_count}")
    else:
        print(f"  Would fix: {changed_count}")
    if error_count:
        print(f"  {RED}Errors:  {error_count}{NC}")

    if args.check and changed_count > 0:
        print()
        print(
            f"  {RED}FAIL{NC}: {changed_count} file(s) need normalization. "
            f"Run with --fix to correct."
        )
        return 1

    return 1 if error_count > 0 else 0


def _cli_targets(args: argparse.Namespace) -> list[Path]:
    """Resolve CLI target paths from explicit files, dirs, or defaults."""
    if args.files:
        return args.files
    if args.dirs:
        return args.dirs
    return [diagram_dir for diagram_dir in DIAGRAM_DIRS if diagram_dir.exists()]


def _process_diagram_file(
    *,
    path: Path,
    args: argparse.Namespace,
    checked_count: int,
    changed_count: int,
    error_count: int,
) -> tuple[int, int, int]:
    """Process one diagram file and return updated counters."""
    try:
        original, normalized, changed = normalize_file(path)
    except Exception as exc:
        print(f"  {RED}ERROR{NC}  {path.name}: {exc}")
        return checked_count, changed_count, error_count + 1

    checked_count += 1
    if not changed:
        if not args.check:
            print(f"  {GREEN}OK{NC}     {path}")
        return checked_count, changed_count, error_count

    changed_count += 1
    _handle_changed_diagram(path, original, normalized, args)
    return checked_count, changed_count, error_count


def _handle_changed_diagram(
    path: Path,
    original: str,
    normalized: str,
    args: argparse.Namespace,
) -> None:
    """Handle one changed diagram according to active CLI mode."""
    if args.check:
        print(f"  {RED}DRIFT{NC}  {path}")
        return
    if args.dry_run:
        print(f"  {YELLOW}DIFF{NC}   {path}")
        show_diff(path, original, normalized)
        print()
        return
    safe_path = _ensure_repo_path(path)
    _write_repo_text(safe_path, normalized)
    print(f"  {GREEN}FIXED{NC}  {path}")


if __name__ == "__main__":
    sys.exit(main())
