"""Apply ELK layout engine to Mermaid flowchart diagrams with high node count.

Inserts  %%{init: {'layout': 'elk'}}%%  before the graph/flowchart declaration
for .mmd files where:
  - @nodes > NODE_THRESHOLD (default 20)
  - diagram type is flowchart or graph (not classDiagram / sequenceDiagram / etc.)
  - ELK init directive is not already present

Optionally overrides layout direction (TB → LR) for pipeline-style diagrams.
Can also enforce a unified ELK edge routing mode for diagrams that already
have ELK init directives.

Usage:
    python src/tools/apply_elk_layout.py [--dry-run] [--threshold N] [--no-direction]
    python src/tools/apply_elk_layout.py --enforce-routing ORTHOGONAL
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

NODE_THRESHOLD = 20

DEFAULT_EDGE_ROUTING = "ORTHOGONAL"
ROUTING_CHOICES = ("ORTHOGONAL", "POLYLINE")
ELK_INIT_TEMPLATE = (
    "%%{init: {'layout': 'elk', 'theme': 'base', "
    "'themeVariables': {'fontFamily': 'Inter, Roboto, sans-serif'}, "
    "'elk': {'mergeEdges': true, 'nodePlacementStrategy': 'BRANDES_KOEPF', "
    "'cycleBreakingStrategy': 'GREEDY', 'direction': 'RIGHT', "
    "'spacing.nodeNode': 40, 'spacing.edgeNode': 30, 'spacing.edgeEdge': 20, "
    "'edgeRouting': '__EDGE_ROUTING__'}}}%%"
)

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
_ELK_ALREADY_RE = re.compile(r"%%\{init:.*layout.*elk", re.IGNORECASE | re.DOTALL)
_EDGE_ROUTING_RE = re.compile(
    r"((?:['\"])?edgeRouting(?:['\"])?\s*:\s*['\"])([A-Za-z_]+)(['\"])",
    re.IGNORECASE,
)
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
    return bool(_ELK_ALREADY_RE.search("\n".join(lines)))


def find_graph_line_index(lines: list[str]) -> int | None:
    """Return index of the first graph/flowchart declaration line."""
    for i, ln in enumerate(lines):
        if _GRAPH_LINE_RE.match(ln.strip()):
            return i
    return None


def should_use_lr(stem: str) -> bool:
    return bool(_LR_RE.search(stem))


def build_elk_init(edge_routing: str) -> str:
    return ELK_INIT_TEMPLATE.replace("__EDGE_ROUTING__", edge_routing)


def _ensure_path_within_root(path: Path, root: Path) -> Path:
    """Resolve and validate that ``path`` stays within ``root``."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to write outside {resolved_root}: {resolved_path}")
    return resolved_path


def enforce_edge_routing(
    lines: list[str], edge_routing: str
) -> tuple[list[str], bool, bool]:
    """Replace ELK edgeRouting value in existing init block(s).

    Returns: (new_lines, changed, found_edge_routing_field)
    """
    new_lines: list[str] = []
    changed = False
    found = False
    target = edge_routing.upper()

    for ln in lines:
        if "edgeRouting" not in ln:
            new_lines.append(ln)
            continue

        def _replace(match: re.Match[str]) -> str:
            nonlocal changed, found
            found = True
            current = match.group(2).upper()
            if current != target:
                changed = True
            return f"{match.group(1)}{target}{match.group(3)}"

        new_lines.append(_EDGE_ROUTING_RE.sub(_replace, ln))

    return new_lines, changed, found


def apply_elk(
    fpath: Path,
    threshold: int,
    auto_direction: bool,
    edge_routing: str | None,
    dry_run: bool,
) -> tuple[bool, str]:
    """Process one file. Returns (modified, reason)."""
    safe_path = _ensure_path_within_root(fpath, ARCH_DIR)
    content = safe_path.read_text(encoding="utf-8")
    lines = content.splitlines()
    if not is_flowchart(lines):
        return False, "not a flowchart/graph diagram"
    changes: list[str] = []
    nodes = parse_nodes(lines)
    if has_elk_init(lines):
        if edge_routing is not None:
            lines, changed, found = enforce_edge_routing(
                lines, edge_routing=edge_routing
            )
            if changed:
                changes.append(f"edgeRouting->{edge_routing}")
            elif not found:
                return False, "ELK init present but edgeRouting field not found"
    else:
        if nodes is None:
            return False, "no @nodes metadata"
        if nodes <= threshold:
            return False, f"@nodes={nodes} <= threshold {threshold}"
        graph_idx = find_graph_line_index(lines)
        if graph_idx is None:
            return False, "graph declaration not found"
        # ── Insert ELK init directive before graph declaration ────────────────────
        selected_routing = edge_routing or DEFAULT_EDGE_ROUTING
        lines = (
            lines[:graph_idx] + [build_elk_init(selected_routing)] + lines[graph_idx:]
        )
        changes.append("elk_init")
    # ── Optionally override direction ─────────────────────────────────────────
    if auto_direction and should_use_lr(fpath.stem):
        graph_idx = find_graph_line_index(lines)
        if graph_idx is not None:
            current_decl = lines[graph_idx]
            stripped_decl = current_decl.lstrip()
            indent = current_decl[: len(current_decl) - len(stripped_decl)]
            updated_decl = _GRAPH_LINE_RE.sub(
                lambda m: f"{m.group(1)} LR",
                stripped_decl,
            )
            updated_decl = indent + updated_decl
            if updated_decl != current_decl:
                lines[graph_idx] = updated_decl
                changes.append("direction->LR")
    if not changes:
        return False, "ELK init already present"
    new_content = "\n".join(lines).rstrip("\n") + "\n"
    if not dry_run:
        safe_path.write_text(new_content, encoding="utf-8")
    if "elk_init" in changes:
        return True, f"@nodes={nodes}, changes=[{', '.join(changes)}]"
    return True, f"changes=[{', '.join(changes)}]"


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
        "--dir",
        type=Path,
        default=ARCH_DIR,
        help=f"Source directory (default: {ARCH_DIR})",
    )
    parser.add_argument(
        "--enforce-routing",
        choices=ROUTING_CHOICES,
        default=None,
        help=(
            "Enforce ELK edge routing for flowcharts with existing ELK init "
            "(e.g. ORTHOGONAL for consistent Manhattan-style links)"
        ),
    )
    args = parser.parse_args()

    source_dir = _ensure_path_within_root(args.dir, REPO_ROOT)
    files = sorted(source_dir.glob("*.mmd"))
    auto_direction = not args.no_direction

    print("=" * 65)
    print(
        f"ELK LAYOUT {'(DRY RUN) ' if args.dry_run else ''}| "
        f"threshold=@nodes>{args.threshold} | "
        f"direction_opt={'on' if auto_direction else 'off'} | "
        f"routing={'keep' if args.enforce_routing is None else args.enforce_routing}"
    )
    print("=" * 65)

    modified = skipped_threshold = skipped_elk = skipped_other = 0

    for f in files:
        ok, reason = apply_elk(
            f,
            args.threshold,
            auto_direction,
            args.enforce_routing,
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
