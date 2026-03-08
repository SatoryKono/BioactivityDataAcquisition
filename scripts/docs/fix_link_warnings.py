#!/usr/bin/env python3
"""Fix LINK-001 and LINK-002 warnings in Mermaid diagram files.

LINK-001: Single arrow semantic → apply semantic arrow diversity
LINK-002: Fragile singleton linkStyle → consolidate into grouped format
"""

import re
import sys
from collections import defaultdict
from pathlib import Path

LINKSTYLE_SINGLE_RE = re.compile(r"^(\s*)linkStyle\s+(\d+)\s+(.+)$")
LINKSTYLE_ANY_RE = re.compile(r"^\s*linkStyle\s+")
SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(\S+)")
END_RE = re.compile(r"^\s*end\s*$")
# Match node["Label..."] or node("Label...") or node{"Label..."}
NODE_DEF_RE = re.compile(r"\b([A-Za-z_]\w*)\s*[\[\(\{][\"\']?([^\"\')\]\}]+)")
ARROW_TOKENS = ("-->", "-.->", "==>")


def _parse_subgraphs(lines: list[str]) -> dict[str, str]:
    """Map node IDs to their closest subgraph name."""
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
        # Detect node definitions
        for nm in NODE_DEF_RE.finditer(s):
            nid = nm.group(1)
            # Skip Mermaid keywords
            if nid.lower() in (
                "subgraph", "end", "style", "classDef", "linkStyle",
                "click", "class", "direction", "graph", "flowchart",
                "fill", "stroke", "width", "height",
            ):
                continue
            if stack:
                node_sg[nid] = stack[-1]
    return node_sg


def _get_node_labels(lines: list[str]) -> dict[str, str]:
    """Map node IDs to their label text."""
    labels: dict[str, str] = {}
    for ln in lines:
        for m in NODE_DEF_RE.finditer(ln):
            nid = m.group(1)
            lbl = m.group(2).split("<br")[0].replace("&nbsp;", "").strip()
            if nid.lower() not in (
                "subgraph", "end", "style", "classDef", "linkStyle",
                "click", "class", "direction", "graph", "flowchart",
            ):
                labels[nid] = lbl
    return labels


def _is_edge_line(s: str) -> bool:
    """Check if a stripped line is an edge (not comment, not linkStyle)."""
    if not s or s.startswith("%%") or s.startswith("linkStyle"):
        return False
    return any(tok in s for tok in ARROW_TOKENS)


def _extract_edge_endpoints(line: str) -> list[tuple[str, str]]:
    """Extract (source, target) from an edge line. Handles A --> B & C."""
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
            # Remove edge labels |...|
            right = re.sub(r"\|[^|]*\|", "", right).strip()
            # Handle & chains
            targets = right.split("&")
            for t in targets:
                t = t.strip().split("[")[0].split("(")[0].split("{")[0]
                t = t.split(":::")[0].strip()
                if source and t:
                    pairs.append((source, t))
            break
    return pairs


def fix_link002(lines: list[str]) -> list[str]:
    """Consolidate singleton linkStyle lines into grouped format."""
    # Collect singleton linkStyle entries
    entries: list[tuple[int, int, str, str]] = []  # (line_idx, edge_idx, style, indent)
    for i, ln in enumerate(lines):
        m = LINKSTYLE_SINGLE_RE.match(ln)
        if m:
            entries.append((i, int(m.group(2)), m.group(3).strip(), m.group(1)))

    if len(entries) < 12:
        return lines  # Not enough to trigger LINK-002

    # Group by normalised style
    by_style: dict[str, list[int]] = defaultdict(list)
    for _, edge_idx, style, _ in entries:
        normalised = " ".join(style.split())
        by_style[normalised].append(edge_idx)

    # Build grouped lines
    indent = entries[0][3]
    grouped: list[str] = []
    for style, indices in sorted(by_style.items(), key=lambda x: min(x[1])):
        idx_str = ",".join(str(i) for i in sorted(indices))
        grouped.append(f"{indent}linkStyle {idx_str} {style}")

    # Remove old singleton lines (reverse order to preserve indices)
    line_indices = sorted({e[0] for e in entries}, reverse=True)
    for li in line_indices:
        lines.pop(li)

    # Insert grouped lines at position of first old line
    insert_at = min(e[0] for e in entries)
    for i, gl in enumerate(grouped):
        lines.insert(insert_at + i, gl)

    return lines


def fix_link001(lines: list[str]) -> list[str]:
    """Add semantic arrow diversity if only one arrow type is used."""
    # Collect edge lines
    edge_info: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if _is_edge_line(s):
            edge_info.append((i, ln))

    if len(edge_info) < 8:
        return lines  # Too few edges for LINK-001

    has_solid = any("-->" in ln for _, ln in edge_info)
    has_dashed = any("-.->" in ln for _, ln in edge_info)
    has_thick = any("==>" in ln for _, ln in edge_info)
    style_count = sum([has_solid, has_dashed, has_thick])

    if style_count >= 2:
        return lines  # Already diverse

    # Check if linkStyle diversity suppresses the warning
    ls_styles: set[str] = set()
    for ln in lines:
        m = re.match(r"^\s*linkStyle\s+(\S+)\s+(.+)$", ln)
        if m and m.group(1) != "default":
            ls_styles.add(" ".join(m.group(2).split()))
    if len(ls_styles) >= 2:
        return lines  # Suppressed by linkStyle diversity

    # Need to add arrow diversity
    node_sg = _parse_subgraphs(lines)
    node_labels = _get_node_labels(lines)

    # Strategy: change some edges based on semantics
    # Priority 1: Port/Protocol → -.->
    # Priority 2: Cross-subgraph → ==>
    changed_types: set[str] = set()
    if has_solid:
        changed_types.add("-->")

    for line_idx, ln in edge_info:
        if len(changed_types) >= 2:
            break
        if "-->" not in ln:
            continue

        pairs = _extract_edge_endpoints(ln)
        for src, tgt in pairs:
            src_label = node_labels.get(src, src)
            tgt_label = node_labels.get(tgt, tgt)

            # Port/Protocol → dashed arrow
            if ("Port" in tgt_label or "Protocol" in tgt_label
                    or "Port" in src_label or "Protocol" in src_label):
                lines[line_idx] = lines[line_idx].replace("-->", "-.->", 1)
                changed_types.add("-.->")
                break

        if len(changed_types) >= 2:
            break

    # If still not enough, try cross-subgraph → thick arrow
    if len(changed_types) < 2:
        for line_idx, ln in edge_info:
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

    # Fallback: if no cross-subgraph edge found, change the LAST edge
    if len(changed_types) < 2:
        for line_idx, ln in reversed(edge_info):
            if "-->" in lines[line_idx]:
                lines[line_idx] = lines[line_idx].replace("-->", "==>", 1)
                changed_types.add("==>")
                break

    return lines


def fix_file(path: Path) -> bool:
    """Fix LINK-001 and LINK-002 in a single file."""
    text = path.read_text()
    lines = text.splitlines()

    # Fix LINK-002 first (grouping)
    lines = fix_link002(lines)

    # Fix LINK-001 (arrow diversity)
    lines = fix_link001(lines)

    new_text = "\n".join(lines)
    if not new_text.endswith("\n"):
        new_text += "\n"

    if new_text != text:
        path.write_text(new_text)
        return True
    return False


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: fix_link_warnings.py <path> [<path> ...]")
        sys.exit(1)

    paths: list[Path] = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_dir():
            paths.extend(p.rglob("*.mmd"))
            paths.extend(p.rglob("*.mermaid"))
        elif p.is_file():
            paths.append(p)

    fixed = 0
    for p in sorted(paths):
        if fix_file(p):
            print(f"  Fixed: {p}")
            fixed += 1
    print(f"\nTotal fixed: {fixed}/{len(paths)} files")


if __name__ == "__main__":
    main()
