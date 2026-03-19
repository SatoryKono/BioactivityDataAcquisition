#!/usr/bin/env python3
"""Normalize Mermaid node sizes for class/sequence diagrams.

Implemented rules (per diagram):
1. `classDiagram`:
   - width baseline from max class name length
   - height baseline from max number of semantic lines inside class body
2. `sequenceDiagram`:
   - width baseline from max participant/actor display title length
   - height is NOT normalized

Flowchart/graph diagrams are intentionally skipped.

Metadata marker:
    %% @uniform <type> width=<W> [height=<H>] max_title_len=<N> [max_desc_lines=<M>]

Usage:
    python scripts/diagrams/normalize_node_sizes.py --check
    python scripts/diagrams/normalize_node_sizes.py --fix
    python scripts/diagrams/normalize_node_sizes.py --check --json
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

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIRS = [
    REPO_ROOT / "docs/02-architecture/mmd-diagrams",
    REPO_ROOT / "docs/02-architecture/diagrams/views",
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
_CLASS_DECL_RE = re.compile(r"^\s*classDiagram\b", re.IGNORECASE)
_SEQUENCE_DECL_RE = re.compile(r"^\s*sequenceDiagram\b", re.IGNORECASE)
_SKIP_DECL_RE = re.compile(
    r"^\s*(?:stateDiagram|erDiagram|mindmap|gantt|pie)\b",
    re.IGNORECASE,
)
_EDGE_HINT_RE = re.compile(r"(--|->|==>|-.->|~~~|<--|--x|--o)")
_KEEP_SIZE_RE = re.compile(r"%%\s*keep-size\s*:\s*(.*)")
_UNIFORM_META_RE = re.compile(r"^\s*%%\s*@uniform\b(?!-(group|stats))")
_LINE_BREAK_RE = re.compile(r"(?i)<br\s*/?>|\\n")
_NBSP_TAIL_RE = re.compile(r"(?:&nbsp;|\u00A0)+$")
_CLASS_BLOCK_START_RE = re.compile(
    r"^(?P<indent>\s*)class\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{\s*$"
)
_CLASS_BLOCK_END_RE = re.compile(r"^\s*}\s*$")
_SEQUENCE_PARTICIPANT_RE = re.compile(
    r"^(?P<indent>\s*)(?P<kind>participant|actor)\s+"
    r"(?P<id>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+as\s+(?P<label>.+?))?\s*$",
    re.IGNORECASE,
)

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
        if _CLASS_DECL_RE.match(s):
            return "class"
        if _SEQUENCE_DECL_RE.match(s):
            return "sequence"
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


@dataclass
class ClassBlock:
    start_idx: int
    end_idx: int
    indent: str
    class_name: str
    body_lines: list[str]
    title_len: int
    desc_lines: int


@dataclass
class SequenceParticipant:
    line_idx: int
    indent: str
    kind: str
    participant_id: str
    raw_label: str | None
    title_len: int


def split_label(raw_label: str) -> list[str]:
    """Split Mermaid label by <br/> and escaped newlines."""
    parts = _LINE_BREAK_RE.split(raw_label)
    normalized = [p.strip() for p in parts if p.strip()]
    return normalized


def strip_trailing_nbsp(text: str) -> str:
    return _NBSP_TAIL_RE.sub("", text).rstrip()


def is_semantic_line(text: str) -> bool:
    return bool(strip_trailing_nbsp(text.strip()))


def visible_length(text: str) -> int:
    no_tags = re.sub(r"<[^>]+>", "", text)
    unescaped = html.unescape(no_tags)
    # Ignore non-breaking spaces used as width fillers.
    normalized = unescaped.replace("\u00A0", "")
    return len(normalized.strip())


def title_and_desc_metrics(label: str) -> tuple[int, int]:
    lines = split_label(label)
    if not lines:
        return 0, 0
    title_len = visible_length(strip_trailing_nbsp(lines[0]))
    desc_count = sum(1 for ln in lines[1:] if is_semantic_line(ln))
    return title_len, desc_count


def parse_class_blocks(lines: list[str], keep_ids: set[str]) -> list[ClassBlock]:
    blocks: list[ClassBlock] = []
    idx = 0
    total = len(lines)
    while idx < total:
        line = lines[idx]
        match = _CLASS_BLOCK_START_RE.match(line)
        if not match:
            idx += 1
            continue

        class_name = match.group("name")
        if class_name in keep_ids:
            idx += 1
            continue

        end_idx = idx + 1
        while end_idx < total and not _CLASS_BLOCK_END_RE.match(lines[end_idx]):
            end_idx += 1
        if end_idx >= total:
            idx += 1
            continue

        body_lines = lines[idx + 1 : end_idx]
        semantic_body = [ln for ln in body_lines if is_semantic_line(ln)]
        blocks.append(
            ClassBlock(
                start_idx=idx,
                end_idx=end_idx,
                indent=match.group("indent"),
                class_name=class_name,
                body_lines=body_lines,
                title_len=visible_length(class_name),
                desc_lines=len(semantic_body),
            )
        )
        idx = end_idx + 1
    return blocks


def pad_semantic_line(line: str, target_len: int, fallback_indent: str) -> str:
    raw = line.rstrip()
    indent_match = re.match(r"^(\s*)", raw)
    indent = indent_match.group(1) if indent_match else fallback_indent
    semantic = strip_trailing_nbsp(raw.strip())
    if not semantic:
        return f"{indent}&nbsp;"
    pad_count = max(0, target_len - visible_length(semantic))
    return f"{indent}{semantic}{'&nbsp;' * pad_count}"


def normalize_class_lines(
    lines: list[str],
    blocks: list[ClassBlock],
    max_title_len: int,
    max_desc_lines: int,
) -> list[str]:
    if not blocks:
        return list(lines)

    out: list[str] = []
    i = 0
    block_by_start = {b.start_idx: b for b in blocks}
    while i < len(lines):
        block = block_by_start.get(i)
        if block is None:
            out.append(lines[i])
            i += 1
            continue

        out.append(lines[block.start_idx])  # class X {
        semantic = [ln for ln in block.body_lines if is_semantic_line(ln)]
        body_indent = (
            re.match(r"^(\s*)", semantic[0]).group(1)
            if semantic
            else f"{block.indent}    "
        )
        for ln in semantic:
            out.append(pad_semantic_line(ln, max_title_len, body_indent))
        fillers = max(0, max_desc_lines - len(semantic))
        out.extend([f"{body_indent}&nbsp;"] * fillers)
        out.append(lines[block.end_idx])  # }
        i = block.end_idx + 1
    return out


def parse_sequence_participants(
    lines: list[str],
    keep_ids: set[str],
) -> list[SequenceParticipant]:
    participants: list[SequenceParticipant] = []
    for idx, line in enumerate(lines):
        m = _SEQUENCE_PARTICIPANT_RE.match(line)
        if not m:
            continue
        pid = m.group("id")
        if pid in keep_ids:
            continue
        raw_label = m.group("label")
        display = raw_label if raw_label is not None else pid
        parts = split_label(display)
        title = strip_trailing_nbsp(parts[0]) if parts else strip_trailing_nbsp(display)
        participants.append(
            SequenceParticipant(
                line_idx=idx,
                indent=m.group("indent"),
                kind=m.group("kind"),
                participant_id=pid,
                raw_label=raw_label,
                title_len=visible_length(title),
            )
        )
    return participants


def pad_sequence_label(raw_label: str, max_title_len: int) -> str:
    parts = split_label(raw_label)
    if not parts:
        parts = [raw_label]
    first = strip_trailing_nbsp(parts[0])
    rest = [p.strip() for p in parts[1:] if p.strip()]
    pad_count = max(0, max_title_len - visible_length(first))
    padded_first = f"{first}{'&nbsp;' * pad_count}"
    return "<br/>".join([padded_first, *rest]) if rest else padded_first


def normalize_sequence_lines(
    lines: list[str],
    participants: list[SequenceParticipant],
    max_title_len: int,
) -> list[str]:
    updated = list(lines)
    for p in participants:
        raw_label = p.raw_label if p.raw_label is not None else p.participant_id
        label = pad_sequence_label(raw_label, max_title_len)
        if p.raw_label is None and label == p.participant_id:
            rebuilt = f"{p.indent}{p.kind} {p.participant_id}"
        else:
            rebuilt = f"{p.indent}{p.kind} {p.participant_id} as {label}"
        updated[p.line_idx] = rebuilt
    return updated


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

    title = strip_trailing_nbsp(lines[0].strip())
    desc = [
        strip_trailing_nbsp(ln.strip())
        for ln in lines[1:]
        if is_semantic_line(ln)
    ]

    pad_count = max(0, max_title_len - visible_length(title))
    padded_title = title + ("&nbsp;" * pad_count)

    while len(desc) < max_desc_lines:
        desc.append("&nbsp;")

    if max_desc_lines == 0:
        return padded_title
    return "<br/>".join([padded_title, *desc])


def upsert_uniform_metadata(
    lines: list[str],
    meta: str,
) -> list[str]:
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

    if diagram_type not in {"class", "sequence"}:
        result.skipped_reason = (
            "unsupported-diagram-type"
            if diagram_type in {"skip", "unknown"}
            else "not-target-diagram-type"
        )
        return result

    # Skip files managed by uniform_diagram_sizes.py groupwise sizing
    if any(
        re.match(r"^\s*%%\s*@uniform-group\b", ln) for ln in lines
    ):
        result.skipped_reason = "has-uniform-groups"
        return result

    keep_ids = parse_keep_size(lines)
    changed = False

    if diagram_type == "class":
        blocks = parse_class_blocks(lines, keep_ids)
        result.processed_nodes = len(blocks)
        if not blocks:
            result.skipped_reason = "no-parsable-class-blocks"
            return result

        max_title_len = max(b.title_len for b in blocks)
        max_desc_lines = max(b.desc_lines for b in blocks)
        width = clamp(BASE_W + (CHAR_W * max_title_len), MIN_W, MAX_W)
        height = clamp(BASE_H + (LINE_H * max_desc_lines), MIN_H, MAX_H)

        result.max_title_len = max_title_len
        result.max_desc_lines = max_desc_lines
        result.width = width
        result.height = height

        updated_lines = normalize_class_lines(lines, blocks, max_title_len, max_desc_lines)
        updated_lines = upsert_uniform_metadata(
            updated_lines,
            (
                "%% @uniform class "
                f"width={width} height={height} "
                f"max_title_len={max_title_len} max_desc_lines={max_desc_lines}"
            ),
        )
    else:
        participants = parse_sequence_participants(lines, keep_ids)
        result.processed_nodes = len(participants)
        if not participants:
            result.skipped_reason = "no-parsable-sequence-participants"
            return result

        max_title_len = max(p.title_len for p in participants)
        width = clamp(BASE_W + (CHAR_W * max_title_len), MIN_W, MAX_W)
        result.max_title_len = max_title_len
        result.max_desc_lines = 0
        result.width = width
        result.height = 0

        updated_lines = normalize_sequence_lines(lines, participants, max_title_len)
        updated_lines = upsert_uniform_metadata(
            updated_lines,
            (
                "%% @uniform sequence "
                f"width={width} max_title_len={max_title_len}"
            ),
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
            "docs/02-architecture/diagrams/views"
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
