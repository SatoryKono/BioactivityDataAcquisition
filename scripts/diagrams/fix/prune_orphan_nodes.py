#!/usr/bin/env python3
"""prune_orphan_nodes.py — Detect and remove orphan nodes from Mermaid diagrams.

DEFINITION
    An orphan node is a node ID that is *defined* in the diagram but participates
    in NO edge or message (neither incoming nor outgoing) within the same file.

SUPPORTED DIAGRAM TYPES
    - flowchart / graph   — parses node shapes + arrow connections
    - sequenceDiagram     — parses participant/actor declarations + messages

SKIPPED (by design)
    - classDiagram, stateDiagram, erDiagram, mindmap, gantt, pie
    - Files matching the pattern ``00-legend*``

EXCEPTIONS (node never flagged as orphan)
    - Inline annotation:  ``%% keep-orphan: NodeId``  (anywhere in file)
    - Multi-node:         ``%% keep-orphan: A, B, C``

USAGE
    # Report only
    python scripts/diagrams/fix/prune_orphan_nodes.py --check

    # Report specific paths
    python scripts/diagrams/fix/prune_orphan_nodes.py --check path/to/file.mmd another/dir/

    # Machine-readable output for CI
    python scripts/diagrams/fix/prune_orphan_nodes.py --check --json

    # Remove confirmed orphans (writes files in-place)
    python scripts/diagrams/fix/prune_orphan_nodes.py --fix

ADR reference: ADR-040-diagram-governance.md (D6 CI Validation)
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
for candidate in (SCRIPT_DIR, REPO_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

if isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, source_dir
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import DIAGRAM_ROOT, source_dir

# ── Paths ─────────────────────────────────────────────────────────────────────
DEFAULT_DIRS = [
    DIAGRAM_ROOT,
    source_dir("views"),
]
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
NODE_ID_SPLIT_PATTERN = r"[\s,]+"


def _ensure_repo_path(path: Path) -> Path:
    resolved_root = REPO_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(
            f"refusing to process path outside {resolved_root}: {resolved_path}"
        )
    return resolved_path


def _repo_relative_path(path: Path) -> Path:
    safe_path = _ensure_repo_path(path)
    return safe_path.relative_to(REPO_ROOT.resolve())


def _write_repo_text(relative_path: Path, content: str) -> None:
    """Write Mermaid content via a repository-relative path."""
    target_path = REPO_ROOT / relative_path
    target_path.write_text(content, encoding="utf-8")


# ── Regex constants ───────────────────────────────────────────────────────────

# Node ID: letters/digits/underscore, must start with letter or underscore
_NID = r"[A-Za-z_]\w*"

# Edge arrow / connector variants (Mermaid flowchart).
# Covers: --> -.-> -..- -.- --- --o --x <--> <-- ==> ~~~ and labelled forms.
# IMPORTANT: longer / more-specific patterns MUST come before shorter ones
# so that -.-  never matches the first 3 chars of  -.->  (which would leave
# a stray  >  before the target node ID and break ID extraction).
_ARROW_RE = re.compile(
    r"-\.\.->"  # -..->   double-dotted forward arrow
    r"|-\.->"  # -.->    dotted forward arrow   ← must precede  -.-
    r"|-\.\.-"  # -..-    double-dotted undirected
    r"|-\.-"  # -.-     dotted undirected
    r"|<-->"  # <-->    bidirectional solid
    r"|-->"  # -->     solid forward arrow
    r"|<--"  # <--     solid backward arrow
    r"|---"  # ---     solid undirected
    r"|--[oxX]"  # --o  --x  circle / cross end
    r"|o--o"  # o--o    circle bidirectional
    r"|x--x"  # x--x    cross bidirectional
    r"|==>>"  # ==>>    thick double arrow
    r"|==>"  # ==>     thick arrow
    r"|~~~"  # ~~~     tilde link
)

# Flowchart: subgraph open — capture the subgraph ID
_SUBGRAPH_RE = re.compile(r"^\s*subgraph\s+(\w+)")

# Flowchart: style directive — `style NodeId key:val`
_STYLE_DIRECTIVE_RE = re.compile(r"^\s*style\s+(\w+)\b")

# Flowchart: node shape definition (line starts with NodeId followed by shape)
# Matches: id[".."], id(["..]), id{{"..}}, id[("..], id(("..)), id>"..], id[, id(, id{
_NODE_SHAPE_RE = re.compile(
    r"^\s*(\w+)\s*(?:"
    r"\[{1,2}[^]]*\]?"  # [text], [[text]], [(text)]
    r"|\({1,2}[^)]*\)?"  # (text), ((text)), ([text])
    r"|\{{1,2}[^}]*\}?"  # {text}, {{text}}
    r"|\x3e[^]]*\]"  # >text] (encoded to avoid an HTML-shape false positive)
    r"|/[^/]*/?"  # /text/
    r")"
)

# keep-orphan annotation
_KEEP_ORPHAN_RE = re.compile(r"%%\s*keep-orphan\s*:\s*(.*)")

# Sequence: message line  A ->> B: msg  or  A --> B
_SEQ_MESSAGE_RE = re.compile(
    r"^\s*(\w+)\s*(?:->>|-->>|->|-->|-x|--x|-\)|--\)|->>\+|-->>\+|<<-|<<--)"
    r"\s*(?:\+|-)?\s*(\w+)\s*:",
)

# Sequence: activate/deactivate
_SEQ_ACTIVATE_RE = re.compile(r"^\s*(?:activate|deactivate)\s+(\w+)", re.IGNORECASE)

# Sequence: box … end  (do NOT treat box names as participants)
_SEQ_BOX_RE = re.compile(r"^\s*box\b", re.IGNORECASE)
_FLOWCHART_RESERVED_IDS = {
    "end",
    "direction",
    "graph",
    "flowchart",
    "sequencediagram",
}


def _parse_class_directive(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped.startswith("class "):
        return None
    payload = stripped[len("class ") :].strip()
    if not payload:
        return None
    parts = payload.rsplit(maxsplit=1)
    if len(parts) != 2:
        return None
    node_ids, class_name = parts
    if not class_name.isidentifier():
        return None
    return node_ids, class_name


def _parse_sequence_participant(line: str) -> str | None:
    stripped = line.strip()
    lowered = stripped.lower()
    if lowered.startswith("participant "):
        payload = stripped[len("participant ") :].strip()
    elif lowered.startswith("actor "):
        payload = stripped[len("actor ") :].strip()
    else:
        return None
    if not payload:
        return None
    alias_part = payload.partition(" as ")[0].strip()
    return alias_part if alias_part.isidentifier() else None


def _parse_sequence_note_targets(line: str) -> str | None:
    stripped = line.strip()
    lowered = stripped.lower()
    for prefix in ("note over ", "note left of ", "note right of "):
        if not lowered.startswith(prefix):
            continue
        payload = stripped[len(prefix) :]
        targets, separator, _ = payload.partition(":")
        if not separator:
            return None
        return targets.strip()
    return None


# ── Data classes ──────────────────────────────────────────────────────────────


@dataclass
class OrphanResult:
    file: Path
    diagram_type: str  # "flowchart" | "sequence" | "skipped"
    orphan_ids: set[str] = field(default_factory=set)
    skipped_reason: str = ""

    @property
    def has_orphans(self) -> bool:
        return bool(self.orphan_ids)


# ── Diagram type detection ────────────────────────────────────────────────────

_SUPPORTED_TYPES = {"flowchart", "graph"}
_SKIP_TYPES = {
    "classdiagram",
    "statediagram",
    "statediagram-v2",
    "erdiagram",
    "mindmap",
    "gantt",
    "pie",
    "xychart-beta",
}


def detect_diagram_type(lines: list[str]) -> str:
    """Return canonical diagram type string or 'skip'/'unknown'."""
    for ln in lines:
        s = ln.strip().lower()
        if not s or s.startswith("%%"):
            continue
        first_word = s.split()[0]
        if first_word == "sequencediagram":
            return "sequence"
        if first_word in _SUPPORTED_TYPES:
            return "flowchart"
        if first_word in _SKIP_TYPES or any(s.startswith(t) for t in _SKIP_TYPES):
            return "skip"
        break
    return "unknown"


# ── keep-orphan annotation parsing ───────────────────────────────────────────


def parse_keep_orphans(lines: list[str]) -> set[str]:
    """Return set of node IDs explicitly exempted from orphan detection."""
    kept: set[str] = set()
    for ln in lines:
        m = _KEEP_ORPHAN_RE.search(ln)
        if m:
            for nid in re.split(NODE_ID_SPLIT_PATTERN, m.group(1).strip()):
                if nid:
                    kept.add(nid)
    return kept


# ── Flowchart parser ──────────────────────────────────────────────────────────


def _ids_from_edge_line(line: str) -> set[str]:
    """Extract all node IDs from a flowchart edge line."""
    # Strip quoted labels between pipes: |"label"| or |label|
    cleaned = re.sub(r"\|[^|]*\|", "", line)
    # Remove quoted strings
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    # Split on any arrow variant
    parts = _ARROW_RE.split(cleaned)
    ids: set[str] = set()
    for part in parts:
        # Each part may contain NodeA & NodeB (multi-source or multi-target)
        for chunk in part.split("&"):
            m = re.match(rf"\s*({_NID})", chunk.strip())
            if m:
                ids.add(m.group(1))
    return ids


def _register_defined_node(
    *,
    node_id: str,
    line_index: int,
    all_defined: set[str],
    definition_lines: dict[str, list[int]],
    node_parent: dict[str, str],
    subgraph_stack: list[str],
) -> None:
    all_defined.add(node_id)
    definition_lines.setdefault(node_id, []).append(line_index)
    if subgraph_stack and subgraph_stack[-1]:
        node_parent[node_id] = subgraph_stack[-1]


def _is_skippable_flowchart_line(line: str) -> bool:
    return bool(
        re.match(
            r"^(?:direction\b|classDef\b|linkStyle\b|%%\{|graph\b|flowchart\b)",
            line,
            re.IGNORECASE,
        )
    )


def _consume_flowchart_structure_line(
    stripped_line: str,
    subgraph_names: set[str],
    subgraph_stack: list[str],
) -> bool:
    if re.match(r"^subgraph\b", stripped_line, re.IGNORECASE):
        match = _SUBGRAPH_RE.match(stripped_line)
        subgraph_name = match.group(1) if match else ""
        if subgraph_name:
            subgraph_names.add(subgraph_name)
        subgraph_stack.append(subgraph_name)
        return True

    if stripped_line.lower() == "end":
        if subgraph_stack:
            subgraph_stack.pop()
        return True

    if _is_skippable_flowchart_line(stripped_line):
        return True

    if _parse_class_directive(stripped_line) is not None:
        return True

    return bool(_STYLE_DIRECTIVE_RE.match(stripped_line))


def _consume_flowchart_edge_line(raw_line: str, connected: set[str]) -> bool:
    if not _ARROW_RE.search(raw_line):
        return False
    connected.update(_ids_from_edge_line(raw_line))
    return True


def _consume_flowchart_node_definition(
    *,
    raw_line: str,
    stripped_line: str,
    line_index: int,
    all_defined: set[str],
    definition_lines: dict[str, list[int]],
    node_parent: dict[str, str],
    subgraph_stack: list[str],
) -> bool:
    match = _NODE_SHAPE_RE.match(stripped_line)
    if match:
        node_id = match.group(1)
        if node_id and re.match(rf"^{_NID}$", node_id):
            _register_defined_node(
                node_id=node_id,
                line_index=line_index,
                all_defined=all_defined,
                definition_lines=definition_lines,
                node_parent=node_parent,
                subgraph_stack=subgraph_stack,
            )
        return True

    match = re.match(rf"^\s*({_NID})\s*$", raw_line)
    if not match:
        return False

    node_id = match.group(1)
    if node_id.lower() in _FLOWCHART_RESERVED_IDS:
        return True

    _register_defined_node(
        node_id=node_id,
        line_index=line_index,
        all_defined=all_defined,
        definition_lines=definition_lines,
        node_parent=node_parent,
        subgraph_stack=subgraph_stack,
    )
    return True


def _consume_sequence_declaration(
    stripped_line: str,
    line_index: int,
    all_declared: set[str],
    declaration_lines: dict[str, list[int]],
) -> bool:
    participant_id = _parse_sequence_participant(stripped_line)
    if participant_id is None:
        return False
    all_declared.add(participant_id)
    declaration_lines.setdefault(participant_id, []).append(line_index)
    return True


def _consume_sequence_interaction(stripped_line: str, messaged: set[str]) -> bool:
    message_match = _SEQ_MESSAGE_RE.match(stripped_line)
    if message_match:
        messaged.add(message_match.group(1))
        messaged.add(message_match.group(2))
        return True

    note_targets = _parse_sequence_note_targets(stripped_line)
    if note_targets is not None:
        for node_id in re.split(NODE_ID_SPLIT_PATTERN, note_targets):
            if node_id and re.match(rf"^{_NID}$", node_id):
                messaged.add(node_id)
        return True

    activate_match = _SEQ_ACTIVATE_RE.match(stripped_line)
    if activate_match:
        messaged.add(activate_match.group(1))
        return True

    return False


def parse_flowchart_orphans(
    lines: list[str],
    keep: set[str],
) -> tuple[set[str], set[str], dict[str, list[int]]]:
    """Analyse a flowchart/graph diagram.

    Returns:
        orphan_ids        — IDs defined but not connected
        all_defined       — all node IDs with standalone definitions
        definition_lines  — map: node_id → [line indices of standalone defs]

    Lenient rule: a node whose *immediate parent subgraph* appears in any edge
    is NOT flagged as an orphan.  Such nodes are intentional descriptive
    children of a connected subgraph container (e.g. B1–B4 inside Bronze when
    ``Bronze --> Silver`` exists).
    """
    subgraph_names: set[str] = set()
    all_defined: set[str] = set()  # standalone node definition IDs
    connected: set[str] = set()  # IDs appearing in edge lines
    definition_lines: dict[str, list[int]] = {}
    node_parent: dict[str, str] = {}  # node_id → immediate parent subgraph
    subgraph_stack: list[str] = []  # stack of open subgraph names

    for i, ln in enumerate(lines):
        s = ln.strip()

        if not s or s.startswith("%%"):
            continue

        if _consume_flowchart_structure_line(s, subgraph_names, subgraph_stack):
            continue

        if _consume_flowchart_edge_line(ln, connected):
            continue

        if _consume_flowchart_node_definition(
            raw_line=ln,
            stripped_line=s,
            line_index=i,
            all_defined=all_defined,
            definition_lines=definition_lines,
            node_parent=node_parent,
            subgraph_stack=subgraph_stack,
        ):
            continue

    # Subgraph names that appear in edge lines (they act as connected nodes)
    connected_subgraph_names: set[str] = connected & subgraph_names

    # Remove subgraph containers from both sets — they're layout groupings,
    # not actual diagram nodes.
    all_defined -= subgraph_names
    connected -= subgraph_names

    # Initial candidate orphans: defined but not directly in any edge
    raw_orphans = (all_defined - connected) - keep

    # Lenient rule: a node inside a *connected* subgraph is not an orphan —
    # it is a descriptive child of that subgraph.
    orphans = _filter_connected_subgraph_orphans(
        raw_orphans=raw_orphans,
        node_parent=node_parent,
        connected_subgraph_names=connected_subgraph_names,
    )

    return orphans, all_defined, definition_lines


def _filter_connected_subgraph_orphans(
    *,
    raw_orphans: set[str],
    node_parent: dict[str, str],
    connected_subgraph_names: set[str],
) -> set[str]:
    """Keep only true orphan nodes, excluding children of connected subgraphs."""
    return {
        node_id
        for node_id in raw_orphans
        if node_parent.get(node_id) not in connected_subgraph_names
    }


# ── Sequence parser ───────────────────────────────────────────────────────────


def parse_sequence_orphans(
    lines: list[str],
    keep: set[str],
) -> tuple[set[str], set[str], dict[str, list[int]]]:
    """Analyse a sequenceDiagram.

    Returns:
        orphan_ids           — declared participants with no messages
        all_declared         — all participant/actor IDs
        declaration_lines    — map: participant_id → [line indices]
    """
    all_declared: set[str] = set()
    declaration_lines: dict[str, list[int]] = {}
    messaged: set[str] = set()

    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue

        if _SEQ_BOX_RE.match(s):
            continue

        if _consume_sequence_declaration(s, i, all_declared, declaration_lines):
            continue

        _consume_sequence_interaction(s, messaged)

    orphans = (all_declared - messaged) - keep
    return orphans, all_declared, declaration_lines


# ── Fix: flowchart ────────────────────────────────────────────────────────────


def fix_flowchart_lines(
    lines: list[str],
    orphan_ids: set[str],
    definition_lines: dict[str, list[int]],
) -> list[str]:
    """Remove standalone orphan node definitions, class refs, and style lines."""
    remove_indices = {
        idx for node_id in orphan_ids for idx in definition_lines.get(node_id, [])
    }

    for i, ln in enumerate(lines):
        style_match = _STYLE_DIRECTIVE_RE.match(ln.strip())
        if style_match and style_match.group(1) in orphan_ids:
            remove_indices.add(i)

    new_lines: list[str] = []
    for i, ln in enumerate(lines):
        if i in remove_indices:
            continue

        class_directive = _parse_class_directive(ln.strip())
        if class_directive is None:
            new_lines.append(ln)
            continue

        rewritten_line = _rewrite_flowchart_class_directive(
            ln, class_directive, orphan_ids
        )
        if rewritten_line is not None:
            new_lines.append(rewritten_line)

    return new_lines


def _rewrite_flowchart_class_directive(
    line: str,
    class_directive: tuple[str, str],
    orphan_ids: set[str],
) -> str | None:
    raw_ids, class_name = class_directive
    node_ids = [node_id.strip() for node_id in re.split(NODE_ID_SPLIT_PATTERN, raw_ids)]
    surviving = [
        node_id for node_id in node_ids if node_id and node_id not in orphan_ids
    ]
    if not surviving:
        return None
    if len(surviving) == len(node_ids):
        return line

    indent = len(line) - len(line.lstrip())
    return f"{' ' * indent}class {','.join(surviving)} {class_name}\n"


# ── Fix: sequence ─────────────────────────────────────────────────────────────


def fix_sequence_lines(
    lines: list[str],
    orphan_ids: set[str],
    declaration_lines: dict[str, list[int]],
) -> list[str]:
    """Remove orphan participant/actor declaration lines."""
    remove_indices: set[int] = set()
    for nid in orphan_ids:
        for idx in declaration_lines.get(nid, []):
            remove_indices.add(idx)
    return [ln for i, ln in enumerate(lines) if i not in remove_indices]


# ── Per-file analysis ─────────────────────────────────────────────────────────


def analyse_file(path: Path) -> OrphanResult:
    """Analyse a single diagram file for orphan nodes."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        return OrphanResult(path, "error", skipped_reason=str(e))

    # Skip legend files
    if path.stem.startswith("00-legend"):
        return OrphanResult(path, "skipped", skipped_reason="legend file")

    lines = content.splitlines(keepends=True)
    stripped = [ln.rstrip("\n") for ln in lines]

    dtype = detect_diagram_type(stripped)
    if dtype == "skip" or dtype == "unknown":
        return OrphanResult(path, "skipped", skipped_reason=f"type={dtype}")

    keep = parse_keep_orphans(stripped)

    if dtype == "flowchart":
        orphans, _, _ = parse_flowchart_orphans(stripped, keep)
        return OrphanResult(path, "flowchart", orphan_ids=orphans)
    elif dtype == "sequence":
        orphans, _, _ = parse_sequence_orphans(stripped, keep)
        return OrphanResult(path, "sequence", orphan_ids=orphans)

    return OrphanResult(path, "skipped", skipped_reason=f"unsupported={dtype}")


def _load_diagram_content(
    path: Path,
) -> tuple[Path, list[str], list[str]] | None:
    """Return validated path plus original/stripped line buffers for a diagram file."""
    try:
        safe_path = _ensure_repo_path(path)
        content = safe_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    if safe_path.stem.startswith("00-legend"):
        return None

    lines = content.splitlines(keepends=True)
    stripped = [line.rstrip("\n") for line in lines]
    return safe_path, lines, stripped


def _fixable_diagram_type(stripped: list[str]) -> str | None:
    dtype = detect_diagram_type(stripped)
    if dtype not in {"flowchart", "sequence"}:
        return None
    return dtype


def fix_file(path: Path) -> tuple[bool, set[str]]:
    """Fix orphan nodes in a single file. Returns (was_modified, removed_ids)."""
    loaded = _load_diagram_content(path)
    if loaded is None:
        return False, set()
    safe_path, lines, stripped = loaded
    dtype = _fixable_diagram_type(stripped)
    if dtype is None:
        return False, set()

    keep = parse_keep_orphans(stripped)
    orphans, new_lines = _fixed_diagram_lines(
        dtype=dtype,
        lines=lines,
        stripped=stripped,
        keep=keep,
    )
    if not orphans:
        return False, set()

    _write_repo_text(_repo_relative_path(safe_path), "".join(new_lines))
    return True, orphans


def _fixed_diagram_lines(
    *,
    dtype: str,
    lines: list[str],
    stripped: list[str],
    keep: set[str],
) -> tuple[set[str], list[str]]:
    """Return orphan ids and updated lines for a supported diagram."""
    if dtype == "flowchart":
        orphans, _, definition_lines = parse_flowchart_orphans(stripped, keep)
        return orphans, fix_flowchart_lines(lines, orphans, definition_lines)

    orphans, _, declaration_lines = parse_sequence_orphans(stripped, keep)
    return orphans, fix_sequence_lines(lines, orphans, declaration_lines)


# ── File discovery ────────────────────────────────────────────────────────────


def _is_supported_input_file(path: Path) -> bool:
    return path.suffix in SUPPORTED_SUFFIXES and not path.name.startswith("_")


def _is_discoverable_diagram_file(path: Path) -> bool:
    return (
        _is_supported_input_file(path)
        and "svg" not in path.parts
        and "png" not in path.parts
    )


def _iter_discoverable_files(target: Path) -> list[Path]:
    if target.is_file():
        return [target] if _is_supported_input_file(target) else []
    if not target.is_dir():
        return []
    return sorted(
        path for path in target.rglob("*") if _is_discoverable_diagram_file(path)
    )


def _append_unseen_paths(
    result: list[Path],
    seen: set[Path],
    paths: list[Path],
) -> None:
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)


def find_files(targets: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for target in targets:
        _append_unseen_paths(result, seen, _iter_discoverable_files(target))
    return result


# ── Output formatters ─────────────────────────────────────────────────────────


def format_text_check(results: list[OrphanResult]) -> str:
    lines: list[str] = ["Orphan Node Check", "=" * 60, ""]

    total_files = sum(1 for r in results if r.diagram_type not in {"skipped", "error"})
    total_orphans = sum(len(r.orphan_ids) for r in results)
    files_with_orphans = [r for r in results if r.has_orphans]

    if not files_with_orphans:
        lines.append("  No orphan nodes found.")
    else:
        for r in files_with_orphans:
            lines.append(f"  {r.file}")
            lines.append(f"    type:    {r.diagram_type}")
            lines.append(f"    orphans: {', '.join(sorted(r.orphan_ids))}")
            lines.append("")

    lines.append("=" * 60)
    lines.append(f"Files analysed: {total_files}")
    lines.append(f"Files with orphans: {len(files_with_orphans)}")
    lines.append(f"Total orphan nodes: {total_orphans}")

    if total_orphans > 0:
        lines.append("")
        lines.append(
            "To remove: python scripts/diagrams/diagrams/prune_orphan_nodes.py --fix"
        )
        lines.append("To keep:   add  %% keep-orphan: NodeId  to the file")

    return "\n".join(lines)


def format_json_check(results: list[OrphanResult]) -> str:
    data = {
        "total_orphans": sum(len(r.orphan_ids) for r in results),
        "files": [
            {
                "file": str(r.file),
                "diagram_type": r.diagram_type,
                "orphan_ids": sorted(r.orphan_ids),
            }
            for r in results
            if r.has_orphans
        ],
    }
    return json.dumps(data, indent=2)


# ── Grandfather mode ──────────────────────────────────────────────────────────


def grandfather_file(path: Path) -> tuple[bool, set[str]]:
    """Add ``%% keep-orphan:`` annotation for every current orphan in the file.

    Inserts the annotation on the line *after* the diagram-type declaration
    (``flowchart``/``graph``/``sequenceDiagram``) so it appears near the top.
    Returns (was_modified, grandfathered_ids).
    """
    try:
        safe_path = _ensure_repo_path(path)
        content = safe_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False, set()

    if safe_path.stem.startswith("00-legend"):
        return False, set()

    lines = content.splitlines(keepends=True)
    stripped = [ln.rstrip("\n") for ln in lines]

    dtype = detect_diagram_type(stripped)
    if dtype not in {"flowchart", "sequence"}:
        return False, set()

    keep = parse_keep_orphans(stripped)

    if dtype == "flowchart":
        orphans, _, _ = parse_flowchart_orphans(stripped, keep)
    else:
        orphans, _, _ = parse_sequence_orphans(stripped, keep)

    if not orphans:
        return False, set()

    annotation = f"%% keep-orphan: {', '.join(sorted(orphans))}\n"

    # Insert after the diagram-type declaration line
    insert_idx: int | None = None
    decl_re = re.compile(r"^(?:flowchart|graph|sequenceDiagram)\b", re.IGNORECASE)
    for i, ln in enumerate(stripped):
        s = ln.strip()
        if not s or s.startswith("%%"):
            continue
        if decl_re.match(s):
            insert_idx = i + 1
            break

    if insert_idx is None:
        # Fallback: append at end
        new_lines = lines + [annotation]
    else:
        new_lines = lines[:insert_idx] + [annotation] + lines[insert_idx:]

    _write_repo_text(_repo_relative_path(safe_path), "".join(new_lines))
    return True, orphans


def _parse_targets(raw_paths: list[str]) -> list[Path]:
    return [Path(path) for path in raw_paths] if raw_paths else DEFAULT_DIRS


def _print_missing_targets(missing: list[Path]) -> None:
    for target in missing:
        print(f"Error: {target} does not exist", file=sys.stderr)


def _run_check(files: list[Path], *, json_output: bool) -> int:
    results = [analyse_file(path) for path in files]
    if json_output:
        print(format_json_check(results))
    else:
        print(format_text_check(results))

    total_orphans = sum(len(result.orphan_ids) for result in results)
    return 1 if total_orphans > 0 else 0


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect and remove orphan nodes from Mermaid diagrams.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files and/or directories to check. Default: both diagram directories.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report orphans without modifying files (default mode).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Remove orphan nodes from files in-place.",
    )
    parser.add_argument(
        "--grandfather",
        action="store_true",
        help=(
            "Add  %%keep-orphan:  annotation for every current orphan — "
            "use once to exempt existing diagrams before enforcing the rule."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="Output results as JSON (useful for CI).",
    )
    args = parser.parse_args()

    # Default to --check if neither flag given
    if not args.fix and not args.grandfather:
        args.check = True

    targets = _parse_targets(args.paths)
    missing = [t for t in targets if not t.exists()]
    if missing:
        _print_missing_targets(missing)
        return 2

    files = find_files(targets)
    if not files:
        print("No diagram files found.", file=sys.stderr)
        return 0

    if args.grandfather:
        _run_grandfather(files)
        return 0

    if args.fix:
        _run_fix(files)
        return 0

    return _run_check(files, json_output=args.json_output)


def _run_grandfather(files: list[Path]) -> None:
    """Grandfather orphan nodes across all selected files."""
    print(f"Grandfathering orphan nodes in {len(files)} files...")
    print("=" * 60)
    total_modified = 0
    total_grandfathered: list[str] = []

    for file_path in files:
        modified, grandfathered_ids = grandfather_file(file_path)
        if not modified:
            continue
        total_modified += 1
        total_grandfathered.extend(sorted(grandfathered_ids))
        print(
            f"  [GF] {file_path.name}  keep-orphan: {', '.join(sorted(grandfathered_ids))}"
        )

    print("=" * 60)
    print(f"Modified files:        {total_modified}")
    print(f"Grandfathered nodes:   {len(total_grandfathered)}")
    print("")
    print(
        "Re-run  --check  to confirm zero orphans. "
        "GRAPH-001 will now only flag NEW orphans added after this point."
    )


def _run_fix(files: list[Path]) -> None:
    """Fix orphan nodes across all selected files."""
    print(f"Fixing orphan nodes in {len(files)} files...")
    print("=" * 60)
    total_modified = 0
    total_removed: list[str] = []

    for file_path in files:
        modified, removed_ids = fix_file(file_path)
        if not modified:
            continue
        total_modified += 1
        total_removed.extend(sorted(removed_ids))
        print(f"  [FIXED] {file_path.name}  removed: {', '.join(sorted(removed_ids))}")

    print("=" * 60)
    print(f"Modified files:   {total_modified}")
    print(f"Removed nodes:    {len(total_removed)}")


if __name__ == "__main__":
    sys.exit(main())
