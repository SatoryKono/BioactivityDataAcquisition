"""Differentiate linkStyle in mermaid flowchart diagrams by connection type.

Applies only to files where:
  1. Diagram type is `flowchart` (not stateDiagram / classDiagram / sequenceDiagram)
  2. All existing linkStyle lines are uniform (stroke:#475569,stroke-width:2px,stroke-dasharray:5)
  3. Total connections > 5
  4. >= 3 distinct connection types are detected via subgraph-layer heuristics

Usage:
    python src/tools/differentiate_linkstyle.py [--dry-run]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")  # Windows cp1251 fix

MERMAID_DIR = (
    Path(__file__).resolve().parents[2] / "docs/02-architecture/diagrams/mermaid"
)

# ── Styles per link type ──────────────────────────────────────────────────────

LINK_STYLES: dict[str, str] = {
    "data": "stroke:#1E293B,stroke-width:2px",
    "orchestration": "stroke:#2e7d32,stroke-width:2px",
    "di": "stroke:#6a1b9a,stroke-width:1.5px,stroke-dasharray:5",
    "observability": "stroke:#94A3B8,stroke-width:1px",
    "error": "stroke:#c62828,stroke-width:2px,stroke-dasharray:4",
    "generic": "stroke:#475569,stroke-width:2px,stroke-dasharray:5",
}

UNIFORM_STYLE = "stroke:#475569,stroke-width:2px,stroke-dasharray:5"

# ── Regex helpers ─────────────────────────────────────────────────────────────

_LINKSTYLE_LINE = re.compile(r"^\s*linkStyle\s+\d+")
_SUBGRAPH_OPEN = re.compile(r"^\s*subgraph\s+(\w+)")
_NODE_DEF = re.compile(r"^\s*(\w+)[\s\[({<]")
_SKIP_LINE = re.compile(
    r"^\s*(?:%%|style\b|classDef\b|class\b|linkStyle\b|direction\b|subgraph\b|end\b)"
)
# Connection with optional label: SRC ARROW |label| TGT  or  SRC ARROW TGT

# ── Core functions ────────────────────────────────────────────────────────────


def diagram_type(lines: list[str]) -> str:
    for ln in lines:
        s = ln.strip()
        if s.startswith("flowchart"):
            return "flowchart"
        if s.startswith("stateDiagram"):
            return "stateDiagram"
        if s.startswith("classDiagram"):
            return "classDiagram"
        if s.startswith("sequenceDiagram"):
            return "sequenceDiagram"
        if s.startswith("graph "):
            return "graph"
    return "unknown"


def _ensure_path_within_root(path: Path, root: Path) -> Path:
    """Resolve and validate that ``path`` stays within ``root``."""
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to write outside {resolved_root}: {resolved_path}")
    return resolved_path


def _mermaid_relative_path(path: Path) -> Path:
    safe_path = _ensure_path_within_root(path, MERMAID_DIR)
    return safe_path.relative_to(MERMAID_DIR.resolve())


def _write_mermaid_text(relative_path: Path, content: str) -> None:
    """Write Mermaid content via a MERMAID_DIR-relative path."""
    target_path = MERMAID_DIR / relative_path
    target_path.write_text(content, encoding="utf-8")


def build_node_layer_map(lines: list[str]) -> dict[str, str]:
    """Map node_id → subgraph name (layer)."""
    node_layer: dict[str, str] = {}
    stack: list[str] = []
    for ln in lines:
        m = _SUBGRAPH_OPEN.match(ln)
        if m:
            stack.append(m.group(1))
        elif ln.strip() == "end" and stack:
            stack.pop()
        elif stack and not _SKIP_LINE.match(ln):
            nd = _NODE_DEF.match(ln)
            if nd:
                node_layer[nd.group(1)] = stack[-1]
    return node_layer


def parse_connections(lines: list[str]) -> list[tuple[str, str, str, str]]:
    """Return list of (src, arrow, label, tgt) for every connection line."""
    conns: list[tuple[str, str, str, str]] = []
    for ln in lines:
        parsed = _parse_connection_line(ln)
        if parsed is not None:
            conns.append(parsed)
    return conns


def _parse_connection_line(line: str) -> tuple[str, str, str, str] | None:
    stripped = line.strip()
    for arrow in ("-.->", "-->", "==>"):
        if arrow not in stripped:
            continue
        left, _, right = stripped.partition(arrow)
        src = left.strip()
        if not src.isidentifier():
            continue
        label = ""
        rhs = right.strip()
        if rhs.startswith("|"):
            _, separator, remainder = rhs[1:].partition("|")
            if not separator:
                return None
            label = _.strip()
            rhs = remainder.strip()
        target = rhs.split(maxsplit=1)[0]
        if target.isidentifier():
            return src, arrow, label, target
    return None


def classify(
    src: str,
    tgt: str,
    arrow: str,
    label: str,
    node_layer: dict[str, str],
) -> str:
    """Classify a single connection into a link type."""
    lbl = label.lower()
    src_layer = node_layer.get(src, "")
    tgt_layer = node_layer.get(tgt, "")

    # 1. Dashed arrow → dependency / DI
    if "." in arrow:
        return "di"

    # 2. Edge label implies DI
    if any(
        k in lbl
        for k in (
            "implement",
            "inject",
            "k06",
            "k07",
            "k08",
            "k09",
            "k10",
            "k11",
            "k12",
        )
    ):
        return "di"

    # 3. Target in Domain subgraph → DI (port dependency)
    if tgt_layer == "Domain":
        return "di"

    # 4. Observability keywords in node ids (abbreviated labels use these)
    if re.search(
        r"(?i)\bobs\b|logger|loggerport|metric|metricsport|tracing|tracingport",
        f"{src} {tgt}",
    ):
        return "observability"

    # 5. Error / quarantine targets
    if re.search(r"(?i)quarantine|errorhandl", tgt):
        return "error"
    if re.search(r"(?i)\bfail\b|\berror\b", lbl) and re.search(
        r"(?i)quarantine|error", tgt
    ):
        return "error"

    # 6. Cross-layer involving Infrastructure → data flow
    if src_layer == "Infrastructure" or tgt_layer == "Infrastructure":
        return "data"

    # 7. Interfaces / Composition initiating something → orchestration
    if src_layer in ("Interfaces", "Composition"):
        return "orchestration"

    # 8. Application ↔ Application / Interfaces → orchestration
    if src_layer == "Application" and tgt_layer in ("Application", "Interfaces", ""):
        return "orchestration"

    return "generic"


def is_all_uniform(lines: list[str]) -> bool:
    for ln in lines:
        if _LINKSTYLE_LINE.match(ln) and UNIFORM_STYLE not in ln:
            return False
    return True


def _compact_ranges(indices: list[int]) -> str:
    """Convert [0,1,2,5,6,9] → '0-2,5-6,9'."""
    if not indices:
        return ""
    ranges: list[str] = []
    start = end = indices[0]
    for i in indices[1:]:
        if i == end + 1:
            end = i
        else:
            ranges.append(f"{start}-{end}" if start != end else str(start))
            start = end = i
    ranges.append(f"{start}-{end}" if start != end else str(start))
    return ",".join(ranges)


def build_linkstyle_block(
    conns: list[tuple[str, str, str, str]],
    node_layer: dict[str, str],
) -> tuple[list[str], dict[str, list[int]]]:
    """Return (new linkStyle lines, type→indices map)."""
    type_indices: dict[str, list[int]] = {}
    classified: list[str] = []

    for idx, (src, arrow, lbl, tgt) in enumerate(conns):
        t = classify(src, tgt, arrow, lbl, node_layer)
        classified.append(t)
        type_indices.setdefault(t, []).append(idx)

    # Comment line: ordered by link type priority
    order = ["data", "orchestration", "di", "observability", "error", "generic"]
    parts = [
        f"{t} {_compact_ranges(type_indices[t])}" for t in order if t in type_indices
    ]
    comment = f"    %% linkStyle: {' | '.join(parts)}"

    ls_lines = [comment]
    for idx, t in enumerate(classified):
        ls_lines.append(f"    linkStyle {idx} {LINK_STYLES[t]}")

    return ls_lines, type_indices


def process_file(fpath: Path, dry_run: bool = False) -> tuple[bool, str]:
    """Process one file. Returns (modified, reason)."""
    safe_path = _ensure_path_within_root(fpath, MERMAID_DIR)
    content = safe_path.read_text(encoding="utf-8")
    lines = content.splitlines()

    if diagram_type(lines) != "flowchart":
        return False, "not_flowchart"

    if not is_all_uniform(lines):
        return False, "already_differentiated"

    conns = parse_connections(lines)
    if len(conns) <= 5:
        return False, f"too_few ({len(conns)})"

    node_layer = build_node_layer_map(lines)
    type_set = {classify(s, t, a, lbl, node_layer) for s, a, lbl, t in conns}
    if len(type_set) < 3:
        return False, f"only_{len(type_set)}_types ({','.join(sorted(type_set))})"

    # Find linkStyle block boundaries
    ls_start = ls_end = None
    for i, ln in enumerate(lines):
        if _LINKSTYLE_LINE.match(ln):
            if ls_start is None:
                ls_start = i
            ls_end = i

    new_ls_lines, _type_indices = build_linkstyle_block(conns, node_layer)

    if ls_start is not None:
        new_lines = lines[:ls_start] + new_ls_lines + lines[ls_end + 1 :]
    else:
        # Append before final blank line
        new_lines = lines + new_ls_lines

    new_content = "\n".join(new_lines).rstrip("\n") + "\n"

    if not dry_run:
        _write_mermaid_text(_mermaid_relative_path(safe_path), new_content)

    details = f"{len(conns)} conn, types={sorted(type_set)}"
    return True, details


# ── Legend update ─────────────────────────────────────────────────────────────

LEGEND_LINK_SECTION = """\
    subgraph LinkTypes["Link Types"]
        direction LR
        LW1[" "] -->|"data flow"| LW2[" "]
        LW3[" "] -.->|"DI / implements"| LW4[" "]
        LW5[" "] -->|"orchestration"| LW6[" "]
        LW7[" "] -->|"observability"| LW8[" "]
        LW9[" "] -->|"error / quarantine"| LW10[" "]
    end
    linkStyle 0 stroke:#1E293B,stroke-width:2px
    linkStyle 1 stroke:#6a1b9a,stroke-width:1.5px,stroke-dasharray:5
    linkStyle 2 stroke:#2e7d32,stroke-width:2px
    linkStyle 3 stroke:#94A3B8,stroke-width:1px
    linkStyle 4 stroke:#c62828,stroke-width:2px,stroke-dasharray:4
"""


def update_legend(fpath: Path, dry_run: bool = False) -> bool:
    safe_path = _ensure_path_within_root(fpath, MERMAID_DIR)
    content = safe_path.read_text(encoding="utf-8")
    if "LinkTypes" in content:
        return False  # already updated

    # Insert before the first existing subgraph
    lines = content.splitlines()
    insert_at = None
    for i, ln in enumerate(lines):
        if re.match(r"^\s*subgraph\s+Legend", ln):
            # Insert after the subgraph open + direction line
            insert_at = i + 2
            break

    if insert_at is None:
        # Fallback: insert at line 3 (after header)
        for i, ln in enumerate(lines):
            if ln.strip().startswith("flowchart"):
                insert_at = i + 2
                break

    if insert_at is None:
        return False

    new_lines = (
        lines[:insert_at]
        + [""]
        + LEGEND_LINK_SECTION.rstrip().splitlines()
        + [""]
        + lines[insert_at:]
    )
    new_content = "\n".join(new_lines).rstrip("\n") + "\n"
    if not dry_run:
        _write_mermaid_text(_mermaid_relative_path(safe_path), new_content)
    return True


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Differentiate mermaid linkStyle by connection type"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print plan without writing files"
    )
    args = parser.parse_args()

    files = sorted(MERMAID_DIR.glob("*.mermaid"))
    print("=" * 65)
    print(
        f"LINKSTYLE DIFFERENTIATION {'(DRY RUN) ' if args.dry_run else ''}| "
        f"{len(files)} files"
    )
    print("=" * 65)

    modified = skipped_diff = skipped_types = skipped_other = 0

    for f in files:
        if f.name == "00-legend.mermaid":
            continue
        ok, reason = process_file(f, dry_run=args.dry_run)
        if ok:
            modified += 1
            print(f"  [OK]   {f.name}  ({reason})")
        elif "already_differentiated" in reason:
            skipped_diff += 1
        elif "types" in reason:
            skipped_types += 1
        else:
            skipped_other += 1

    # Legend update
    legend = MERMAID_DIR / "00-legend.mermaid"
    if legend.exists():
        updated = update_legend(legend, dry_run=args.dry_run)
        print(
            "\n  [LEGEND] 00-legend.mermaid "
            f"{'updated' if updated else 'already has LinkTypes section'}"
        )

    print("\n" + "=" * 65)
    print(f"Modified:              {modified}")
    print(f"Skipped (already OK):  {skipped_diff}")
    print(f"Skipped (<3 types):    {skipped_types}")
    print(f"Skipped (other):       {skipped_other}")


if __name__ == "__main__":
    main()
