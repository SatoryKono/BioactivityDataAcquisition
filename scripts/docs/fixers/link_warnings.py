#!/usr/bin/env python3
"""Fix LINK-001 and LINK-002 warnings in Mermaid diagram files.

LINK-001: Single arrow semantic -> apply semantic arrow diversity
LINK-002: Fragile singleton linkStyle -> consolidate into grouped format
"""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(\S+)")
END_RE = re.compile(r"^\s*end\s*$")
NODE_DEF_RE = re.compile(r"\b([A-Za-z_]\w*)\s*[\[\(\{][\"\']?([^\"\')\]\}]+)")
ARROW_TOKENS = ("-->", "-.->", "==>")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fix Mermaid LINK-001 and LINK-002 warnings in files or directories."
    )
    parser.add_argument("paths", nargs="+", help="Files or directories to rewrite.")
    return parser


def _is_reserved_node(nid: str) -> bool:
    """Check if the node ID is a reserved keyword."""
    return nid.lower() in (
        "subgraph",
        "end",
        "style",
        "classdef",
        "linkstyle",
        "click",
        "class",
        "direction",
        "graph",
        "flowchart",
        "fill",
        "stroke",
        "width",
        "height",
    )


def _parse_subgraphs(lines: list[str]) -> dict[str, str]:
    """Parse subgraphs and assign nodes to their respective subgraphs."""
    node_sg: dict[str, str] = {}
    stack: list[str] = []

    for ln in lines:
        s = ln.strip()
        m = SUBGRAPH_RE.match(s)
        if m:
            stack.append(m.group(1))
            continue
        if END_RE.match(s) and stack:
            stack.pop()
            continue
        _assign_nodes_to_subgraphs(s, stack, node_sg)

    return node_sg


def _assign_nodes_to_subgraphs(
    line: str, stack: list[str], node_sg: dict[str, str]
) -> None:
    """Assign nodes to their respective subgraphs based on the current stack."""
    for nm in NODE_DEF_RE.finditer(line):
        nid = nm.group(1)
        if _is_reserved_node(nid):
            continue
        if stack:
            node_sg[nid] = stack[-1]


def _parse_linkstyle_single(line: str) -> tuple[str, str, str] | None:
    """Parse a single linkStyle line and extract its components."""
    stripped = line.strip()
    if not stripped.startswith("linkStyle "):
        return None

    indent = _extract_indent(line)
    payload = stripped[len("linkStyle ") :].strip()
    index, separator, style = payload.partition(" ")

    if not _is_valid_linkstyle(index, separator):
        return None

    return indent, index, style.strip()


def _extract_indent(line: str) -> str:
    """Extract the leading whitespace from a line."""
    return line[: len(line) - len(line.lstrip())]


def _is_valid_linkstyle(index: str, separator: str) -> bool:
    """Check if the linkStyle index and separator are valid."""
    return separator and index.isdigit()


def _get_node_labels(lines: list[str]) -> dict[str, str]:
    """Extract node labels from the lines."""
    labels: dict[str, str] = {}
    for ln in lines:
        for m in NODE_DEF_RE.finditer(ln):
            nid = m.group(1)
            if _is_reserved_node(nid):
                continue
            lbl = _clean_node_label(m.group(2))
            labels[nid] = lbl
    return labels


def _clean_node_label(label: str) -> str:
    """Clean the node label by removing HTML tags and extra spaces."""
    return label.split("<br")[0].replace("&nbsp;", "").strip()


def _is_edge_line(s: str) -> bool:
    if not s or s.startswith("%%") or s.startswith("linkStyle"):
        return False
    return any(tok in s for tok in ARROW_TOKENS)


def _extract_edge_endpoints(line: str) -> list[tuple[str, str]]:
    s = line.strip()
    if "%%" in s:
        s = s[: s.index("%%")]

    pairs: list[tuple[str, str]] = []
    for tok in ARROW_TOKENS:
        if tok in s:
            parts = s.split(tok, 1)
            left = parts[0].strip()
            right = parts[1].strip()
            source = left.split()[-1] if left.split() else ""
            right = re.sub(r"\|[^|]*\|", "", right).strip()
            targets = right.split("&")
            for target in targets:
                target = target.strip().split("[")[0].split("(")[0].split("{")[0]
                target = target.split(":::")[0].strip()
                if source and target:
                    pairs.append((source, target))
            break
    return pairs


def fix_link002(lines: list[str]) -> list[str]:
    """Fix LINK-002 by grouping linkStyle entries."""
    entries = _collect_linkstyle_entries(lines)

    if len(entries) < 12:
        return lines

    by_style = _group_linkstyles_by_style(entries)
    indent = entries[0][3]
    grouped = _create_grouped_linkstyles(by_style, indent)

    lines = _remove_old_linkstyles(lines, entries)
    lines = _insert_grouped_linkstyles(lines, grouped, entries)

    return lines


def _collect_linkstyle_entries(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """Collect all linkStyle entries from the lines."""
    entries: list[tuple[int, int, str, str]] = []
    for i, ln in enumerate(lines):
        parsed = _parse_linkstyle_single(ln)
        if parsed is None:
            continue
        indent, index, style = parsed
        entries.append((i, int(index), style, indent))
    return entries


def _group_linkstyles_by_style(
    entries: list[tuple[int, int, str, str]],
) -> dict[str, list[int]]:
    """Group linkStyle entries by their style."""
    by_style: dict[str, list[int]] = defaultdict(list)
    for _, edge_idx, style, _ in entries:
        normalised = " ".join(style.split())
        by_style[normalised].append(edge_idx)
    return by_style


def _create_grouped_linkstyles(
    by_style: dict[str, list[int]], indent: str
) -> list[str]:
    """Create grouped linkStyle lines."""
    grouped: list[str] = []
    for style, indices in sorted(by_style.items(), key=lambda item: min(item[1])):
        idx_str = ",".join(str(i) for i in sorted(indices))
        grouped.append(f"{indent}linkStyle {idx_str} {style}")
    return grouped


def _remove_old_linkstyles(
    lines: list[str], entries: list[tuple[int, int, str, str]]
) -> list[str]:
    """Remove old linkStyle lines from the lines."""
    line_indices = sorted({e[0] for e in entries}, reverse=True)
    for li in line_indices:
        lines.pop(li)
    return lines


def _insert_grouped_linkstyles(
    lines: list[str], grouped: list[str], entries: list[tuple[int, int, str, str]]
) -> list[str]:
    """Insert grouped linkStyle lines into the lines."""
    insert_at = min(e[0] for e in entries)
    for i, gl in enumerate(grouped):
        lines.insert(insert_at + i, gl)
    return lines


def fix_link001(lines: list[str]) -> list[str]:
    """Fix LINK-001 by diversifying arrow types."""
    edge_info = _collect_edge_info(lines)

    if len(edge_info) < 8:
        return lines

    has_solid, has_dashed, has_thick = _check_arrow_types(edge_info)
    style_count = sum([has_solid, has_dashed, has_thick])
    if style_count >= 2:
        return lines

    node_sg = _parse_subgraphs(lines)
    node_labels = _get_node_labels(lines)

    changed_types: set[str] = set()
    if has_solid:
        changed_types.add("-->")

    lines = _apply_port_protocol_rules(lines, edge_info, node_labels, changed_types)

    if len(changed_types) < 2:
        lines = _apply_subgraph_rules(lines, edge_info, node_sg, changed_types)

    if len(changed_types) < 2:
        lines = _apply_default_rule(lines, edge_info)

    return lines


def _collect_edge_info(lines: list[str]) -> list[tuple[int, str]]:
    """Collect all edge lines from the lines."""
    edge_info: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if _is_edge_line(s):
            edge_info.append((i, ln))
    return edge_info


def _check_arrow_types(edge_info: list[tuple[int, str]]) -> tuple[bool, bool, bool]:
    """Check the types of arrows present in the edge lines."""
    has_solid = any("-->" in ln for _, ln in edge_info)
    has_dashed = any("-.->" in ln for _, ln in edge_info)
    has_thick = any("==>" in ln for _, ln in edge_info)
    return has_solid, has_dashed, has_thick


def _apply_port_protocol_rules(
    lines: list[str],
    edge_info: list[tuple[int, str]],
    node_labels: dict[str, str],
    changed_types: set[str],
) -> list[str]:
    """Apply rules for Port and Protocol labels."""
    for line_idx, ln in edge_info:
        if len(changed_types) >= 2:
            break
        if "-->" not in ln:
            continue

        pairs = _extract_edge_endpoints(ln)
        for src, tgt in pairs:
            src_label = node_labels.get(src, src)
            tgt_label = node_labels.get(tgt, tgt)

            if (
                "Port" in tgt_label
                or "Protocol" in tgt_label
                or "Port" in src_label
                or "Protocol" in src_label
            ):
                lines[line_idx] = lines[line_idx].replace("-->", "-.->", 1)
                changed_types.add("-.->")
                break

    return lines


def _apply_subgraph_rules(
    lines: list[str],
    edge_info: list[tuple[int, str]],
    node_sg: dict[str, str],
    changed_types: set[str],
) -> list[str]:
    """Apply rules for subgraph transitions."""
    for line_idx, _ in edge_info:
        if len(changed_types) >= 2:
            break
        if "-->" not in lines[line_idx]:
            continue

        pairs = _extract_edge_endpoints(lines[line_idx])
        for src, tgt in pairs:
            src_sg = node_sg.get(src, "")
            tgt_sg = node_sg.get(tgt, "")
            if src_sg and tgt_sg and src_sg != tgt_sg:
                lines[line_idx] = lines[line_idx].replace("-->", "==>", 1)
                changed_types.add("==>")
                break

    return lines


def _apply_default_rule(
    lines: list[str], edge_info: list[tuple[int, str]]
) -> list[str]:
    """Apply default rule for arrow diversification."""
    for line_idx, _ in reversed(edge_info):
        if "-->" in lines[line_idx]:
            lines[line_idx] = lines[line_idx].replace("-->", "==>", 1)
            break

    return lines


def fix_file(path: Path) -> bool:
    text = path.read_text()
    lines = text.splitlines()
    lines = fix_link002(lines)
    lines = fix_link001(lines)

    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if new_text != text:
        path.write_text(new_text)
        return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    paths: list[Path] = []
    for arg in args.paths:
        p = Path(arg)
        if p.is_dir():
            paths.extend(p.rglob("*.mmd"))
            paths.extend(p.rglob("*.mermaid"))
        elif p.is_file():
            paths.append(p)

    fixed = 0
    for path in sorted(paths):
        if fix_file(path):
            print(f"  Fixed: {path}")
            fixed += 1
    print(f"\nTotal fixed: {fixed}/{len(paths)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
