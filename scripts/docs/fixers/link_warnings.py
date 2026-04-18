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


def _parse_subgraphs(lines: list[str]) -> dict[str, str]:
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
        for nm in NODE_DEF_RE.finditer(s):
            nid = nm.group(1)
            if nid.lower() in (
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
            ):
                continue
            if stack:
                node_sg[nid] = stack[-1]
    return node_sg


def _parse_linkstyle_single(line: str) -> tuple[str, str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("linkStyle "):
        return None
    indent = line[: len(line) - len(line.lstrip())]
    payload = stripped[len("linkStyle ") :].strip()
    index, separator, style = payload.partition(" ")
    if not separator or not index.isdigit():
        return None
    return indent, index, style.strip()


def _get_node_labels(lines: list[str]) -> dict[str, str]:
    labels: dict[str, str] = {}
    for ln in lines:
        for m in NODE_DEF_RE.finditer(ln):
            nid = m.group(1)
            lbl = m.group(2).split("<br")[0].replace("&nbsp;", "").strip()
            if nid.lower() not in (
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
            ):
                labels[nid] = lbl
    return labels


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
    entries: list[tuple[int, int, str, str]] = []
    for i, ln in enumerate(lines):
        m = LINKSTYLE_SINGLE_RE.match(ln)
        if m:
            entries.append((i, int(m.group(2)), m.group(3).strip(), m.group(1)))

    if len(entries) < 12:
        return lines

    by_style: dict[str, list[int]] = defaultdict(list)
    for _, edge_idx, style, _ in entries:
        normalised = " ".join(style.split())
        by_style[normalised].append(edge_idx)

    indent = entries[0][3]
    grouped: list[str] = []
    for style, indices in sorted(by_style.items(), key=lambda item: min(item[1])):
        idx_str = ",".join(str(i) for i in sorted(indices))
        grouped.append(f"{indent}linkStyle {idx_str} {style}")

    line_indices = sorted({e[0] for e in entries}, reverse=True)
    for li in line_indices:
        lines.pop(li)

    insert_at = min(e[0] for e in entries)
    for i, gl in enumerate(grouped):
        lines.insert(insert_at + i, gl)

    return lines


def fix_link001(lines: list[str]) -> list[str]:
    edge_info: list[tuple[int, str]] = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if _is_edge_line(s):
            edge_info.append((i, ln))

    if len(edge_info) < 8:
        return lines

    has_solid = any("-->" in ln for _, ln in edge_info)
    has_dashed = any("-.->" in ln for _, ln in edge_info)
    has_thick = any("==>" in ln for _, ln in edge_info)
    style_count = sum([has_solid, has_dashed, has_thick])
    if style_count >= 2:
        return lines

    node_sg = _parse_subgraphs(lines)
    node_labels = _get_node_labels(lines)

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

            if (
                "Port" in tgt_label
                or "Protocol" in tgt_label
                or "Port" in src_label
                or "Protocol" in src_label
            ):
                lines[line_idx] = lines[line_idx].replace("-->", "-.->", 1)
                changed_types.add("-.->")
                break

        if len(changed_types) >= 2:
            break

    if len(changed_types) < 2:
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

    if len(changed_types) < 2:
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
