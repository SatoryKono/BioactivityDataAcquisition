#!/usr/bin/env python3
"""Prune orphan nodes from Mermaid sequence and flowchart diagrams.

Orphan = a node/participant declared but never connected via edges/messages.
Respects `%% keep-orphan: NODE1, NODE2` comments.
Subgraph container names are NOT treated as orphans.

Usage:
    python scripts/diagrams/mermaid_prune_orphans.py --dry-run     # report only
    python scripts/diagrams/mermaid_prune_orphans.py --apply        # modify files
    python scripts/diagrams/mermaid_prune_orphans.py --apply --filter "03-*"
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MMD_ROOT = REPO_ROOT / "docs" / "02-architecture" / "mmd-diagrams"

DEFAULT_DIRS = ["architecture", "class-diagrams", "foundation"]

# ── Regex patterns ──────────────────────────────────────────────

# Flowchart node declarations: A[label], A(label), A{label}, A((label)), A>label]
RE_FC_NODE = re.compile(
    r"^\s*([A-Za-z_][\w]*)"  # node id
    r"\s*[\[\(\{<>]"  # opening bracket
)

# Flowchart edges: A --> B, A ---|text| B, A -. text .-> B, etc.
RE_FC_EDGE = re.compile(
    r"([A-Za-z_][\w]*)"  # source
    r"\s*"
    r"(?:--+>|--+|==+>|==+|-\.+->|-\.+|~~~|<--+>)"  # arrow
    r"[^A-Za-z_]*"
    r"([A-Za-z_][\w]*)"  # target
)

# Also catch edges with label syntax: A -->|text| B or A -- text --> B
RE_FC_EDGE_LABEL = re.compile(
    r"([A-Za-z_][\w]*)"
    r"\s*(?:--+|==+|-\.+)"
    r"[^\n]*?"
    r"(?:>|--)"
    r"\s*"
    r"([A-Za-z_][\w]*)"
)

# Subgraph declaration
RE_SUBGRAPH = re.compile(r"^\s*subgraph\s+(\S+)")

# Sequence participant/actor
RE_SEQ_PARTICIPANT = re.compile(
    r"^\s*(?:participant|actor)\s+(\S+?)(?:\s+as\s+.*)?\s*$"
)

# Sequence message: A->>B: text, A-->>B: text, etc.
RE_SEQ_MSG = re.compile(r"^\s*([A-Za-z_][\w]*)\s*-+>>?\+?\s*-?\s*([A-Za-z_][\w]*)")

# Also match right-to-left and other sequence patterns
RE_SEQ_MSG2 = re.compile(
    r"([A-Za-z_][\w]*)\s*(?:->>|-->>|-)>?\+?\s*([A-Za-z_][\w]*)\s*:"
)

# Keep-orphan comment
RE_KEEP = re.compile(r"%%\s*keep-orphan:\s*(.+)", re.IGNORECASE)

# Diagram type detection
RE_FLOWCHART = re.compile(r"^\s*(?:flowchart|graph)\s+(?:TB|TD|BT|LR|RL)", re.MULTILINE)
RE_SEQUENCE = re.compile(r"^\s*sequenceDiagram", re.MULTILINE)


def detect_type(text: str) -> str | None:
    if RE_SEQUENCE.search(text):
        return "sequence"
    if RE_FLOWCHART.search(text):
        return "flowchart"
    return None


def parse_keep_orphans(text: str) -> set[str]:
    keep: set[str] = set()
    for m in RE_KEEP.finditer(text):
        for name in m.group(1).split(","):
            name = name.strip()
            if name:
                keep.add(name)
    return keep


def analyze_flowchart(text: str) -> tuple[dict[str, int], set[str], set[str]]:
    """Return (node_id->line_num, connected_ids, subgraph_ids)."""
    nodes: dict[str, int] = {}
    connected: set[str] = set()
    subgraphs: set[str] = set()

    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()

        # Skip comments and directives
        if stripped.startswith("%%") or stripped.startswith("```"):
            continue

        # Subgraph containers
        m = RE_SUBGRAPH.match(stripped)
        if m:
            subgraphs.add(m.group(1))
            continue

        if stripped in ("end", ""):
            continue

        # Skip direction declarations and style/class lines
        if re.match(
            r"^\s*(?:graph|flowchart|direction|style|classDef|class |linkStyle|click )",
            stripped,
        ):
            continue

        # Edges (check first — they also contain node refs)
        for edge_re in (RE_FC_EDGE, RE_FC_EDGE_LABEL):
            for em in edge_re.finditer(stripped):
                src, tgt = em.group(1), em.group(2)
                connected.add(src)
                connected.add(tgt)

        # Node declarations
        nm = RE_FC_NODE.match(stripped)
        if nm:
            nid = nm.group(1)
            # Skip keywords
            if nid.lower() in (
                "subgraph",
                "end",
                "graph",
                "flowchart",
                "direction",
                "style",
                "classdef",
                "click",
                "linkstyle",
                "class",
            ):
                continue
            if nid not in nodes:
                nodes[nid] = i

    return nodes, connected, subgraphs


def analyze_sequence(text: str) -> tuple[dict[str, int], set[str]]:
    """Return (participant_id->line_num, connected_ids)."""
    participants: dict[str, int] = {}
    connected: set[str] = set()

    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("%%"):
            continue

        m = RE_SEQ_PARTICIPANT.match(stripped)
        if m:
            participants[m.group(1)] = i
            continue

        for msg_re in (RE_SEQ_MSG, RE_SEQ_MSG2):
            for mm in msg_re.finditer(stripped):
                connected.add(mm.group(1))
                connected.add(mm.group(2))

    return participants, connected


def find_orphans(path: Path) -> tuple[str, list[tuple[str, int]]] | None:
    """Analyze a single .mmd file. Returns (diagram_type, [(orphan_id, line)])."""
    text = path.read_text(encoding="utf-8")
    dtype = detect_type(text)
    if dtype is None:
        return None

    keep = parse_keep_orphans(text)

    if dtype == "flowchart":
        nodes, connected, subgraphs = analyze_flowchart(text)
        orphans = [
            (nid, lineno)
            for nid, lineno in sorted(nodes.items(), key=lambda x: x[1])
            if nid not in connected and nid not in subgraphs and nid not in keep
        ]
    else:  # sequence
        participants, connected = analyze_sequence(text)
        orphans = [
            (pid, lineno)
            for pid, lineno in sorted(participants.items(), key=lambda x: x[1])
            if pid not in connected and pid not in keep
        ]

    if not orphans:
        return None
    return dtype, orphans


def remove_orphan_lines(path: Path, orphan_ids: set[str], dtype: str) -> int:
    """Remove orphan node/participant declarations. Returns lines removed."""
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    new_lines: list[str] = []
    removed = 0

    for line in lines:
        stripped = line.strip()

        should_remove = False

        if dtype == "sequence":
            m = RE_SEQ_PARTICIPANT.match(stripped)
            if m and m.group(1) in orphan_ids:
                should_remove = True

        elif dtype == "flowchart":
            # Only remove standalone node declaration lines (not edges)
            nm = RE_FC_NODE.match(stripped)
            if nm and nm.group(1) in orphan_ids:
                # Make sure this line is NOT an edge line
                has_edge = False
                for edge_re in (RE_FC_EDGE, RE_FC_EDGE_LABEL):
                    if edge_re.search(stripped):
                        has_edge = True
                        break
                if not has_edge:
                    should_remove = True

        if should_remove:
            removed += 1
        else:
            new_lines.append(line)

    if removed > 0:
        path.write_text("".join(new_lines), encoding="utf-8")

    return removed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Prune orphan nodes from Mermaid diagrams"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run", action="store_true", help="Report orphans without modifying"
    )
    group.add_argument(
        "--apply", action="store_true", help="Remove orphan declarations"
    )
    parser.add_argument("--filter", default="*", help="Glob filter for filenames")
    parser.add_argument("--dir", action="append", dest="dirs", help="Extra source dirs")
    args = parser.parse_args()

    dirs = args.dirs or [str(MMD_ROOT / d) for d in DEFAULT_DIRS]

    files: list[Path] = []
    for d in dirs:
        dp = Path(d)
        if not dp.is_dir():
            print(f"WARN: {d} not found, skipping")
            continue
        files.extend(sorted(dp.glob(f"{args.filter}.mmd")))
        files.extend(sorted(dp.glob(f"{args.filter}.mermaid")))

    total_orphans = 0
    total_files_affected = 0
    total_lines_removed = 0

    for f in files:
        result = find_orphans(f)
        if result is None:
            continue

        dtype, orphans = result
        total_orphans += len(orphans)
        total_files_affected += 1

        rel = f.relative_to(REPO_ROOT)
        print(f"\n{'=' * 60}")
        print(f"  {rel}")
        print(f"  Type: {dtype} | Orphans: {len(orphans)}")
        print(f"{'=' * 60}")

        for oid, lineno in orphans:
            print(f"  L{lineno:>4d}  {oid}")

        if args.apply:
            orphan_ids = {oid for oid, _ in orphans}
            removed = remove_orphan_lines(f, orphan_ids, dtype)
            total_lines_removed += removed
            print(f"  --> Removed {removed} lines")

    print(f"\n{'=' * 60}")
    print(f"  Files analyzed:  {len(files)}")
    print(f"  Files affected:  {total_files_affected}")
    print(f"  Total orphans:   {total_orphans}")
    if args.apply:
        print(f"  Lines removed:   {total_lines_removed}")
    else:
        print(f"  Mode: DRY-RUN (no changes)")
    print(f"{'=' * 60}")

    sys.exit(1 if total_orphans > 0 and args.dry_run else 0)


if __name__ == "__main__":
    main()
