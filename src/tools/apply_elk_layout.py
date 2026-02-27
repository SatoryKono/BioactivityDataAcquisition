"""Apply ELK layout engine to Mermaid flowchart diagrams.

Inserts  %%{init: {'layout': 'elk'}}%%  before the graph/flowchart declaration
for .mmd files where:
  - @nodes metadata present (any count)
  - diagram type is flowchart or graph (not classDiagram / sequenceDiagram / etc.)
  - ELK init directive is not already present

Adaptive strategy by node density:
  - default:     ELK + POLYLINE routing + NETWORK_SIMPLEX placement
  - optional:    ELK + ORTHOGONAL for very dense diagrams via CLI flag

Optionally overrides layout direction (TB → LR) for pipeline-style diagrams.

Usage:
    python src/tools/apply_elk_layout.py [--dry-run] [--threshold N] [--no-direction]
    python src/tools/apply_elk_layout.py --dense-orthogonal-from 60
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH_DIR = REPO_ROOT / "docs/02-architecture/mmd-diagrams/architecture"

# ── Constants ─────────────────────────────────────────────────────────────────

NODE_THRESHOLD = 15

# ── ELK strategy ──────────────────────────────────────────────────────────────
# Default policy:
#   - use POLYLINE for readability across architecture flowcharts
# Optional policy:
#   - switch to ORTHOGONAL only for very dense diagrams if explicitly enabled

DEFAULT_DENSE_ORTHOGONAL_FROM = 60  # recommended when opt-in is used

ELK_POLYLINE = "%%{init: {'layout': 'elk', 'elk': {'mergeEdges': false, 'nodePlacementStrategy': 'NETWORK_SIMPLEX', 'edgeRouting': 'POLYLINE'}}}%%"
ELK_ORTHOGONAL = "%%{init: {'layout': 'elk', 'elk': {'mergeEdges': false, 'nodePlacementStrategy': 'NETWORK_SIMPLEX', 'edgeRouting': 'ORTHOGONAL'}}}%%"


def get_elk_init(node_count: int, dense_orthogonal_from: int | None) -> tuple[str, str]:
    """Select ELK init directive based on optional dense threshold."""
    if dense_orthogonal_from is not None and node_count > dense_orthogonal_from:
        return ELK_ORTHOGONAL, "ORTHOGONAL"
    return ELK_POLYLINE, "POLYLINE"


# Diagrams whose content is a linear pipeline chain — better rendered LR.
# Pattern matched against stem (filename without extension).
LR_PATTERNS: list[str] = [
    r"medallion",  # Bronze→Silver→Gold chains
    r"data.flow",  # generic data flow
    r"storage.layer",  # write pipeline
    r"config",  # YAML→Loader→Schema→Domain chain
    r"cli.interface",  # CLI→Router→Service chain
]

_LR_RE = re.compile("|".join(LR_PATTERNS), re.IGNORECASE)

# ── Regex helpers ─────────────────────────────────────────────────────────────

_NODES_RE = re.compile(r"%%\s*@nodes\s+(\d+)")
_GRAPH_LINE_RE = re.compile(r"^(graph|flowchart)\s+(TB|LR|BT|RL|TD)?", re.IGNORECASE)
_ELK_ALREADY_RE = re.compile(r"%%\{init.*layout.*elk", re.IGNORECASE)
_DIAGRAM_TYPE_RE = re.compile(
    r"^(classDiagram|sequenceDiagram|stateDiagram|erDiagram|mindmap|gantt|pie|xychart)",
    re.IGNORECASE,
)


# ── Core logic ────────────────────────────────────────────────────────────────


def parse_nodes(lines: list[str]) -> int | None:
    for ln in lines:
        m = _NODES_RE.search(ln)
        if m:
            return int(m.group(1))
    return None


def is_flowchart(lines: list[str]) -> bool:
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue
        if _GRAPH_LINE_RE.match(s):
            return True
        if _DIAGRAM_TYPE_RE.match(s):
            return False
    return False


def has_elk_init(lines: list[str]) -> bool:
    return any(_ELK_ALREADY_RE.search(ln) for ln in lines)


def find_graph_line_index(lines: list[str]) -> int | None:
    """Return index of the first graph/flowchart declaration line."""
    for i, ln in enumerate(lines):
        if _GRAPH_LINE_RE.match(ln.strip()):
            return i
    return None


def should_use_lr(stem: str) -> bool:
    return bool(_LR_RE.search(stem))


def apply_elk(
    fpath: Path,
    threshold: int,
    dense_orthogonal_from: int | None,
    auto_direction: bool,
    dry_run: bool,
) -> tuple[bool, str]:
    """Process one file. Returns (modified, reason)."""
    content = fpath.read_text(encoding="utf-8")
    lines = content.splitlines()

    nodes = parse_nodes(lines)
    if nodes is None:
        return False, "no @nodes metadata"

    if nodes <= threshold:
        return False, f"@nodes={nodes} <= threshold {threshold}"

    if not is_flowchart(lines):
        return False, "not a flowchart/graph diagram"

    if has_elk_init(lines):
        return False, "ELK init already present"

    graph_idx = find_graph_line_index(lines)
    if graph_idx is None:
        return False, "graph declaration not found"

    changes: list[str] = []

    # ── Insert ELK init directive before graph declaration ────────────────────
    elk_init, routing = get_elk_init(nodes, dense_orthogonal_from)
    new_lines = lines[:graph_idx] + [elk_init] + lines[graph_idx:]
    changes.append(f"elk_init({routing})")

    # ── Optionally override direction ─────────────────────────────────────────
    if auto_direction and should_use_lr(fpath.stem):
        current_decl = new_lines[graph_idx + 1]  # shifted by +1 after insert
        updated_decl = _GRAPH_LINE_RE.sub(
            lambda m: f"{m.group(1)} LR",
            current_decl,
        )
        if updated_decl != current_decl:
            new_lines[graph_idx + 1] = updated_decl
            changes.append("direction->LR")

    new_content = "\n".join(new_lines).rstrip("\n") + "\n"

    if not dry_run:
        fpath.write_text(new_content, encoding="utf-8")

    return True, f"@nodes={nodes}, changes=[{', '.join(changes)}]"


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Apply ELK layout to high-node-count Mermaid diagrams"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without writing files",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=NODE_THRESHOLD,
        help=f"Min @nodes to trigger ELK (default: {NODE_THRESHOLD})",
    )
    parser.add_argument(
        "--no-direction",
        action="store_true",
        help="Skip automatic TB→LR direction optimization for pipeline diagrams",
    )
    parser.add_argument(
        "--dense-orthogonal-from",
        type=int,
        default=None,
        help=(
            "Optional: use ORTHOGONAL routing for @nodes > N. "
            f"Recommended start: {DEFAULT_DENSE_ORTHOGONAL_FROM}"
        ),
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=ARCH_DIR,
        help=f"Source directory (default: {ARCH_DIR})",
    )
    args = parser.parse_args()

    files = sorted(args.dir.glob("*.mmd"))
    auto_direction = not args.no_direction

    print("=" * 65)
    print(
        f"ELK LAYOUT {'(DRY RUN) ' if args.dry_run else ''}| "
        f"threshold=@nodes>{args.threshold} | "
        f"direction_opt={'on' if auto_direction else 'off'} | "
        f"dense_orthogonal_from={args.dense_orthogonal_from if args.dense_orthogonal_from is not None else 'disabled'}"
    )
    print("=" * 65)

    modified = skipped_threshold = skipped_elk = skipped_other = 0

    for f in files:
        ok, reason = apply_elk(
            f,
            args.threshold,
            args.dense_orthogonal_from,
            auto_direction,
            args.dry_run,
        )
        if ok:
            modified += 1
            print(f"  [OK]   {f.name}  ({reason})")
        elif "already" in reason:
            skipped_elk += 1
        elif "threshold" in reason or "@nodes" in reason:
            skipped_threshold += 1
        else:
            skipped_other += 1
            print(f"  [SKIP] {f.name}  ({reason})")

    print("\n" + "=" * 65)
    print(f"Modified:               {modified}")
    print(f"Skipped (already ELK):  {skipped_elk}")
    print(f"Skipped (low @nodes):   {skipped_threshold}")
    print(f"Skipped (other):        {skipped_other}")


if __name__ == "__main__":
    main()
