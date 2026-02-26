#!/usr/bin/env python3
"""Normalize Mermaid flowchart node sizes using diagram-level maxima.

Rule implemented (per diagram):
1. Width baseline is derived from max title length across all nodes.
2. Height baseline is derived from max description line count across all nodes.

Implementation strategy:
- Parse node labels in flowchart/graph diagrams.
- For each node, extract:
  - title: first non-empty line
  - description: remaining non-empty lines
- Compute maxima:
  - max_title_len
  - max_desc_lines
- Rebuild each node label to match maxima:
  - pad title with ``&nbsp;`` to max_title_len
  - append description filler lines ``&nbsp;`` to max_desc_lines

The script writes a metadata marker:
    %% @uniform width=<W> height=<H> max_title_len=<N> max_desc_lines=<M>

Usage:
    python scripts/normalize_node_sizes.py --check
    python scripts/normalize_node_sizes.py --fix
    python scripts/normalize_node_sizes.py --check --json
    python scripts/normalize_node_sizes.py --fix docs/02-architecture/mmd-diagrams
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DIRS = [
    REPO_ROOT / "docs/02-architecture/mmd-diagrams",
    REPO_ROOT / "docs/02-architecture/diagrams/mermaid",
]
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}

# Size coefficients (px)
BASE_W = 40
CHAR_W = 8
MIN_W = 140
MAX_W = 420

BASE_H = 36
LINE_H = 18
MIN_H = 56
MAX_H = 240

_GRAPH_DECL_RE = re.compile(r"^\s*(?:graph|flowchart)\b", re.IGNORECASE)
_SKIP_DECL_RE = re.compile(
    r"^\s*(?:classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap|gantt|pie)\b",
    re.IGNORECASE,
)
_EDGE_HINT_RE = re.compile(r"(--|->|==>|-.->|~~~|<--|--x|--o)")
_KEEP_SIZE_RE = re.compile(r"%%\s*keep-size\s*:\s*(.*)")
_UNIFORM_META_RE = re.compile(r"^\s*%%\s*@uniform\b")
_LINE_BREAK_RE = re.compile(r"(?i)<br\s*/?>|\\n")

# Node declarations with quoted labels:
#   A["text"], A('text'), A{{"text"}}, A["text"]:::cls
_NODE_QUOTED_RE = re.compile(
    r"^(?P<lead>\s*(?P<id>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<open>\[\[|\[|\(\(|\(|\{\{|\{)\s*"
    r"(?P<quote>\"|'))"
    r"(?P<label>.*?)"
    r"(?P<trail>(?P=quote)\s*(?P<close>\]\]|\]|\)\)|\)|\}\}|\}).*)$"
)

# Node declarations with unquoted labels:
#   A[text], A((text)), A{text}
_NODE_UNQUOTED_RE = re.compile(
    r"^(?P<lead>\s*(?P<id>[A-Za-z_][A-Za-z0-9_]*)\s*"
    r"(?P<open>\[\[|\[|\(\(|\(|\{\{|\{)\s*)"
    r"(?P<label>[^)\]}]+?)"
    r"(?P<trail>\s*(?P<close>\]\]|\]|\)\)|\)|\}\}|\}).*)$"
)


@dataclass
class NodeLabel:
    line_idx: int
    node_id: str
    lead: str
    label: str
    tail: str
    title_len: int
    desc_lines: int


@dataclass
class FileResult:
    file: str
    diagram_type: str
    processed_nodes: int = 0
    max_title_len: int = 0
    max_desc_lines: int = 0
    width: int = 0
    height: int = 0
    changed: bool = False
    skipped_reason: str = ""


@dataclass
class RunResult:
    files_checked: int = 0
    files_changed: int = 0
    files_skipped: int = 0
    details: list[FileResult] = field(default_factory=list)


def clamp(value: int, lower: int, upper: int) -> int:
    return max(lower, min(upper, value))


def find_diagram_files(targets: list[Path]) -> list[Path]:
    found: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        if target.is_file():
            if (
                target.suffix in SUPPORTED_SUFFIXES
                and not target.name.startswith("_")
                and not target.name.startswith("00-legend")
                and target not in seen
            ):
                seen.add(target)
                found.append(target)
            continue
        for path in target.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in SUPPORTED_SUFFIXES:
                continue
            if path.name.startswith("_") or path.name.startswith("00-legend"):
                continue
            if path not in seen:
                seen.add(path)
                found.append(path)
    return sorted(found)


def detect_diagram_type(lines: list[str]) -> str:
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue
        if _GRAPH_DECL_RE.match(s):
            return "flowchart"
        if _SKIP_DECL_RE.match(s):
            return "skip"
        break
    return "unknown"


def parse_keep_size(lines: list[str]) -> set[str]:
    kept: set[str] = set()
    for ln in lines:
        m = _KEEP_SIZE_RE.search(ln)
        if not m:
            continue
        for token in re.split(r"[\s,]+", m.group(1).strip()):
            if token:
                kept.add(token)
    return kept


def split_label(raw_label: str) -> list[str]:
    """Split Mermaid label by <br/> and escaped newlines."""
    parts = _LINE_BREAK_RE.split(raw_label)
    # keep non-empty semantic lines only
    normalized = [p.strip() for p in parts if p.strip()]
    return normalized


def visible_length(text: str) -> int:
    no_tags = re.sub(r"<[^>]+>", "", text)
    unescaped = html.unescape(no_tags)
    return len(unescaped.strip())


def title_and_desc_metrics(label: str) -> tuple[int, int]:
    lines = split_label(label)
    if not lines:
        return 0, 0
    title_len = visible_length(lines[0])
    desc_count = len(lines[1:])
    return title_len, desc_count


def parse_flowchart_nodes(lines: list[str], keep_ids: set[str]) -> list[NodeLabel]:
    nodes: list[NodeLabel] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if stripped.startswith(
            ("subgraph ", "classDef ", "class ", "style ", "linkStyle ")
        ):
            continue
        # Do not rewrite edge lines; normalize explicit node declarations only.
        if _EDGE_HINT_RE.search(line):
            continue

        match = _NODE_QUOTED_RE.match(line)
        if match is None:
            match = _NODE_UNQUOTED_RE.match(line)
        if match is None:
            continue

        node_id = match.group("id")
        if node_id in keep_ids:
            continue

        label = match.group("label")
        title_len, desc_lines = title_and_desc_metrics(label)
        nodes.append(
            NodeLabel(
                line_idx=idx,
                node_id=node_id,
                lead=match.group("lead"),
                label=label,
                tail=match.group("trail"),
                title_len=title_len,
                desc_lines=desc_lines,
            )
        )
    return nodes


def normalize_label(
    label: str,
    max_title_len: int,
    max_desc_lines: int,
) -> str:
    lines = split_label(label)
    if not lines:
        lines = [""]

    title = lines[0].strip()
    desc = [ln.strip() for ln in lines[1:]]

    pad_count = max(0, max_title_len - visible_length(title))
    padded_title = title + ("&nbsp;" * pad_count)

    while len(desc) < max_desc_lines:
        desc.append("&nbsp;")

    if max_desc_lines == 0:
        return padded_title
    return "<br/>".join([padded_title, *desc])


def upsert_uniform_metadata(
    lines: list[str],
    width: int,
    height: int,
    max_title_len: int,
    max_desc_lines: int,
) -> list[str]:
    meta = (
        "%% @uniform "
        f"width={width} height={height} "
        f"max_title_len={max_title_len} max_desc_lines={max_desc_lines}"
    )
    for i, ln in enumerate(lines):
        if _UNIFORM_META_RE.match(ln):
            if lines[i] == meta:
                return lines
            updated = list(lines)
            updated[i] = meta
            return updated

    insert_at = 0
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith("%%"):
            insert_at = i + 1
            continue
        if not s:
            continue
        break
    updated = list(lines)
    updated.insert(insert_at, meta)
    return updated


def process_file(path: Path, fix: bool) -> FileResult:
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    diagram_type = detect_diagram_type(lines)
    result = FileResult(file=str(path), diagram_type=diagram_type)

    if diagram_type != "flowchart":
        result.skipped_reason = (
            "unsupported-diagram-type"
            if diagram_type in {"skip", "unknown"}
            else "not-flowchart"
        )
        return result

    keep_ids = parse_keep_size(lines)
    nodes = parse_flowchart_nodes(lines, keep_ids)
    result.processed_nodes = len(nodes)

    if not nodes:
        result.skipped_reason = "no-parsable-node-labels"
        return result

    max_title_len = max(n.title_len for n in nodes)
    max_desc_lines = max(n.desc_lines for n in nodes)

    width = clamp(BASE_W + (CHAR_W * max_title_len), MIN_W, MAX_W)
    height = clamp(BASE_H + (LINE_H * max_desc_lines), MIN_H, MAX_H)

    result.max_title_len = max_title_len
    result.max_desc_lines = max_desc_lines
    result.width = width
    result.height = height

    updated_lines = list(lines)
    changed = False
    for node in nodes:
        normalized = normalize_label(node.label, max_title_len, max_desc_lines)
        rebuilt = f"{node.lead}{normalized}{node.tail}"
        if rebuilt != updated_lines[node.line_idx]:
            updated_lines[node.line_idx] = rebuilt
            changed = True

    updated_lines = upsert_uniform_metadata(
        updated_lines, width, height, max_title_len, max_desc_lines
    )
    if updated_lines != lines:
        changed = True

    result.changed = changed
    if fix and changed:
        path.write_text("\n".join(updated_lines).rstrip("\n") + "\n", encoding="utf-8")
    return result


def format_text(run: RunResult, *, mode: str) -> str:
    lines: list[str] = []
    lines.append(f"Node Size Normalization ({mode})")
    lines.append("=" * 44)
    lines.append("")
    for item in run.details:
        if item.skipped_reason:
            lines.append(f"- SKIP {item.file} ({item.skipped_reason})")
            continue
        marker = "CHANGED" if item.changed else "OK"
        lines.append(
            f"- {marker} {item.file} "
            f"[nodes={item.processed_nodes}, max_title_len={item.max_title_len}, "
            f"max_desc_lines={item.max_desc_lines}, width={item.width}, height={item.height}]"
        )
    lines.append("")
    lines.append(f"Files checked: {run.files_checked}")
    lines.append(f"Files changed: {run.files_changed}")
    lines.append(f"Files skipped: {run.files_skipped}")
    return "\n".join(lines)


def format_json(run: RunResult, *, mode: str) -> str:
    data = {
        "mode": mode,
        "files_checked": run.files_checked,
        "files_changed": run.files_changed,
        "files_skipped": run.files_skipped,
        "details": [
            {
                "file": item.file,
                "diagram_type": item.diagram_type,
                "processed_nodes": item.processed_nodes,
                "max_title_len": item.max_title_len,
                "max_desc_lines": item.max_desc_lines,
                "width": item.width,
                "height": item.height,
                "changed": item.changed,
                "skipped_reason": item.skipped_reason,
            }
            for item in run.details
        ],
    }
    return json.dumps(data, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize Mermaid node sizes by diagram-level max title length and "
            "max description lines"
        )
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--check", action="store_true", help="Report only")
    mode_group.add_argument("--fix", action="store_true", help="Write normalized files")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "paths",
        nargs="*",
        help=(
            "Optional files/directories. Defaults: "
            "docs/02-architecture/mmd-diagrams and "
            "docs/02-architecture/diagrams/mermaid"
        ),
    )
    args = parser.parse_args()

    mode = "fix" if args.fix else "check"
    targets = [Path(p) for p in args.paths] if args.paths else DEFAULT_DIRS
    missing = [p for p in targets if not p.exists()]
    if missing:
        for path in missing:
            print(f"Error: path does not exist: {path}", file=sys.stderr)
        return 2

    files = find_diagram_files(targets)
    run = RunResult()

    for path in files:
        run.files_checked += 1
        item = process_file(path, fix=args.fix)
        if item.skipped_reason:
            run.files_skipped += 1
        if item.changed:
            run.files_changed += 1
        run.details.append(item)

    if args.json:
        print(format_json(run, mode=mode))
    else:
        print(format_text(run, mode=mode))

    # In check mode, non-zero exit when changes are needed.
    if not args.fix and run.files_changed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
