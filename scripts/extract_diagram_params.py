#!/usr/bin/env python3
"""
extract_diagram_params.py — Extract comprehensive parameters from Mermaid diagrams.

Parses every .mmd and .mermaid file in the project and produces a structured
JSON report containing 10 parameter groups per diagram:

 1. File info (format, naming, directory, idea)
 2. Metadata (@version, @date, @type, @level, title, covers)
 3. Node / edge statistics
 4. Layout engine & edge routing
 5. Layers (subgraph colours)
 6. Subgraphs (hierarchy, nesting, styles)
 7. Nodes (id, label, shape, layer, subgraph, classDef, size tier, text)
 8. Edges (source, target, arrow type, label, linkStyle)
 9. Edge labels
10. Computed quality metrics (edges/nodes ratio, hub nodes, orphans)

Usage:
    python scripts/extract_diagram_params.py                        # all diagrams → JSON stdout
    python scripts/extract_diagram_params.py --out report.json      # write to file
    python scripts/extract_diagram_params.py --markdown --out r.md  # markdown report
    python scripts/extract_diagram_params.py <path>                 # specific file/dir
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_BASE = ROOT / "docs" / "02-architecture" / "mmd-diagrams"
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
EXCLUDED_PARTS = {"99-archive"}

# Canonical palette from ADR-040
LAYER_PALETTE: dict[str, dict[str, str]] = {
    "Domain":         {"fill": "#f5f3ff", "stroke": "#7c3aed"},
    "Application":    {"fill": "#f0fdf4", "stroke": "#16a34a"},
    "Infrastructure": {"fill": "#fff1f2", "stroke": "#dc2626"},
    "Composition":    {"fill": "#fff7ed", "stroke": "#f59e0b"},
    "Interfaces":     {"fill": "#eff6ff", "stroke": "#2563eb"},
    "External":       {"fill": "#f1f5f9", "stroke": "#64748b"},
    "Bronze":         {"fill": "#fff7ed", "stroke": "#f59e0b"},
    "Silver":         {"fill": "#f8fafc", "stroke": "#475569"},
    "Gold":           {"fill": "#fefce8", "stroke": "#ca8a04"},
    "Quarantine":     {"fill": "#ffe4e6", "stroke": "#e11d48"},
}

# ── Regexes ────────────────────────────────────────────────────────────────────

_META_RE = {
    "version": re.compile(r"%%\s*@version\s+(.+)"),
    "date":    re.compile(r"%%\s*@date\s+(.+)"),
    "type":    re.compile(r"%%\s*@type\s+(.+)"),
    "level":   re.compile(r"%%\s*@level\s+(.+)"),
    "nodes":   re.compile(r"%%\s*@nodes\s+(\d+)"),
    "adr":     re.compile(r"%%\s*@adr\s+(.+)"),
    "view":    re.compile(r"%%\s*(?:@view|View:)\s*(.+?)(?:\s*\|.*)?$"),
    "parent":  re.compile(r"%%\s*(?:@parent|Parent:)\s*(.+)"),
    "uniform": re.compile(r"%%\s*@uniform\s+(.+)"),
}
_TITLE_RE = re.compile(r"^%%\s*BioETL\s*[—–-]\s*(.+)")
_COVERS_RE = re.compile(r"^%%\s*(?!@|BioETL)(.+)")
_INIT_RE = re.compile(r"%%\{init:\s*(.+?)\}%%", re.DOTALL)
_ELK_RE = re.compile(r"layout.*elk", re.IGNORECASE)
_EDGE_ROUTING_RE = re.compile(
    r"['\"]?edgeRouting['\"]?\s*:\s*['\"]?([A-Z_]+)['\"]?", re.IGNORECASE,
)
_GRAPH_DIR_RE = re.compile(r"^(?:graph|flowchart)\s+(TB|BT|LR|RL|TD)", re.IGNORECASE)
_CLASSDIAGRAM_RE = re.compile(r"^classDiagram\b", re.IGNORECASE)
_SEQUENCE_RE = re.compile(r"^sequenceDiagram\b", re.IGNORECASE)
_STATE_RE = re.compile(r"^stateDiagram", re.IGNORECASE)
_ER_RE = re.compile(r"^erDiagram\b", re.IGNORECASE)
_MINDMAP_RE = re.compile(r"^mindmap\b", re.IGNORECASE)

# Flowchart node definition patterns
_FLOW_NODE_RE = re.compile(
    r"""
    (?:^|\s)                     # start or space
    ([A-Za-z_][A-Za-z0-9_]*)    # node id (group 1)
    \s*                          # optional space
    (                            # shape group (group 2)
      \[\(".*?"\)\]             # cylinder [("...")]
    | \[\[.*?\]\]               # subroutine [[...]]
    | \[".*?"\]                 # rectangle ["..."]
    | \[.*?\]                   # rectangle [...]
    | \(\[".*?"\]\)             # stadium (["..."])
    | \(\[.*?\]\)               # stadium ([...])
    | \(\(".*?"\)\)             # double circle (("..."))
    | \(\(.*?\)\)               # double circle ((...))
    | \(".*?"\)                 # rounded ("...")
    | \(.*?\)                   # rounded (...)
    | \{".*?"\}                 # rhombus {"..."}
    | \{.*?\}                   # rhombus {...}
    | \{\{".*?"\}\}             # hexagon {{"..."}}
    | \{\{.*?\}\}               # hexagon {{...}}
    | \>".*?"\]                 # flag >"..."]
    | \>.*?\]                   # flag >...]
    )
    """,
    re.VERBOSE | re.DOTALL,
)

# Multiline node: ID["text<br/>...text"]
_FLOW_NODE_MULTILINE_RE = re.compile(
    r'([A-Za-z_][A-Za-z0-9_]*)\s*\["((?:[^"\\]|\\.)*)"\]',
)

# Subgraph
_SUBGRAPH_RE = re.compile(
    r'^\s*subgraph\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\["([^"]+)"\])?\s*$'
)
_SUBGRAPH_LABEL_RE = re.compile(
    r'^\s*subgraph\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\["([^"]+)"\])?'
)
_END_RE = re.compile(r"^\s*end\s*$")

# Edges (flowchart)
_FLOW_EDGE_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)"         # source
    r"\s*"
    r"(-->|-.->|==>|---->|-.-->|====>|--[|]|-.[-]?[|])"  # arrow
    r'(?:\s*\|"?([^"|]*?)"?\|)?'         # optional label
    r"\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)"          # target
)

# Multi-target edges: A & B & C --> D
_MULTI_EDGE_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*&\s*[A-Za-z_][A-Za-z0-9_]*)+)"  # sources
    r"\s*(-->|-.->|==>)"                   # arrow
    r'(?:\s*\|"?([^"|]*?)"?\|)?'           # optional label
    r"\s*([A-Za-z_][A-Za-z0-9_]*)"         # target
)

# classDef
_CLASSDEF_RE = re.compile(
    r"^\s*classDef\s+([A-Za-z_][A-Za-z0-9_-]*)\s+(.+)$"
)
# class assignment:  class A,B,C styleName
_CLASS_ASSIGN_RE = re.compile(
    r"^\s*class\s+([\w,\s]+)\s+([A-Za-z_][A-Za-z0-9_-]*)\s*$"
)
# Inline class: NODE:::className
_INLINE_CLASS_RE = re.compile(r":::([A-Za-z_][A-Za-z0-9_-]*)")

# style directive:  style NodeId fill:...,stroke:...
_STYLE_DIRECT_RE = re.compile(r"^\s*style\s+(\S+)\s+(.+)$")

# linkStyle
_LINKSTYLE_RE = re.compile(r"^\s*linkStyle\s+(\S+)\s+(.+)$")

# classDiagram class block
_CD_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*\{")
_CD_MEMBER_RE = re.compile(r"^\s*([+\-#~])\s*(.+)$")
_CD_RELATION_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*"
    r"(<\|--|<\|\.\.|\.\.|--|-->|\.\.>|--\*|--o|<\|--|\*--|o--)"
    r"\s*([A-Za-z_]\w*)"
    r"(?:\s*:\s*(.+))?$"
)
_CD_STYLE_RE = re.compile(r"^\s*style\s+([A-Za-z_]\w*)\s+(.+)$")

# sequenceDiagram participant
_SEQ_PARTICIPANT_RE = re.compile(
    r"^\s*(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+))?$"
)
_SEQ_MESSAGE_RE = re.compile(
    r"^\s*(\S+)\s*(->>|-->>|-\)|--\)|->|-->)\s*(\S+)\s*:\s*(.*)$"
)

# direction inside subgraph
_DIRECTION_RE = re.compile(r"^\s*direction\s+(TB|BT|LR|RL|TD)\s*$", re.IGNORECASE)

# Size tier from :::size-sm / :::size-md / :::size-lg
_SIZE_TIER_RE = re.compile(r":::size-(sm|md|lg)")


# ── Data classes ───────────────────────────────────────────────────────────────

@dataclass
class NodeInfo:
    id: str
    label: str = ""
    shape: str = "rect"          # rect, rounded, diamond, cylinder, circle, hexagon, stadium, flag
    layer: str = ""              # resolved from subgraph / classDef
    subgraph: str = ""           # immediate parent subgraph
    class_def: str = ""          # classDef name applied
    style: str = ""              # inline style if any
    size_tier: str = ""          # sm, md, lg
    title_text: str = ""         # first line (before <br/>)
    body_text: str = ""          # rest after <br/>
    connection_count: int = 0
    # Class diagram specifics
    stereotype: str = ""         # <<Protocol>>, <<abstract>>
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


@dataclass
class EdgeInfo:
    index: int
    source: str
    target: str
    arrow_type: str              # -->, -.->, ==>, etc.
    label: str = ""
    semantic_type: str = ""      # data_flow, di_implements, critical, etc.
    link_style: str = ""         # resolved linkStyle CSS
    stroke_color: str = ""
    stroke_width: str = ""
    stroke_dasharray: str = ""


@dataclass
class SubgraphInfo:
    id: str
    label: str = ""
    parent: str = ""             # parent subgraph id, "" = root
    depth: int = 0
    style_fill: str = ""
    style_stroke: str = ""
    style_stroke_width: str = ""
    resolved_layer: str = ""     # matched canonical layer name
    direction: str = ""          # local direction override
    child_nodes: list[str] = field(default_factory=list)
    child_subgraphs: list[str] = field(default_factory=list)


@dataclass
class ClassDefInfo:
    name: str
    fill: str = ""
    stroke: str = ""
    stroke_width: str = ""
    other_props: str = ""


@dataclass
class DiagramReport:
    # Group 1: File info
    file_path: str = ""
    file_name: str = ""
    format: str = ""             # .mmd or .mermaid
    directory: str = ""
    catalog: str = ""            # architecture, class-diagrams, foundation, views
    idea: str = ""               # first comment line

    # Group 2: Metadata
    title: str = ""
    covers: str = ""
    version: str = ""
    date: str = ""
    diagram_type: str = ""       # flowchart, classDiagram, etc.
    level: str = ""
    nodes_declared: int | None = None
    adr: str = ""
    view: str = ""
    parent_file: str = ""
    uniform: str = ""

    # Group 3: Statistics
    nodes_actual: int = 0
    edges_count: int = 0
    edge_types_count: int = 0
    subgraphs_count: int = 0

    # Group 4: Layout
    direction: str = ""          # TB, LR, etc.
    layout_engine: str = ""      # dagre, elk
    edge_routing: str = ""       # ORTHOGONAL, POLYLINE, default
    init_block: str = ""
    elk_config: dict = field(default_factory=dict)

    # Group 5: Layers
    layers: list[dict] = field(default_factory=list)

    # Group 6: Subgraphs
    subgraphs: list[dict] = field(default_factory=list)

    # Group 7: Nodes
    nodes: list[dict] = field(default_factory=list)

    # Group 8: Edges
    edges: list[dict] = field(default_factory=list)

    # Group 9: Edge labels
    edge_labels: list[dict] = field(default_factory=list)

    # Group 10: Quality metrics
    edges_nodes_ratio: float = 0.0
    hub_nodes: list[dict] = field(default_factory=list)
    orphan_nodes: list[str] = field(default_factory=list)
    max_subgraph_depth: int = 0
    class_defs: list[dict] = field(default_factory=list)
    link_styles: list[dict] = field(default_factory=list)


# ── Parsing helpers ────────────────────────────────────────────────────────────

def _parse_style_props(style_str: str) -> dict[str, str]:
    """Parse CSS-like props: 'fill:#abc,stroke:#def' → dict."""
    props: dict[str, str] = {}
    for part in style_str.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip()] = v.strip()
    return props


def _detect_shape(raw: str) -> str:
    """Detect Mermaid node shape from bracket pattern."""
    raw = raw.strip()
    if raw.startswith('[("') or raw.startswith("[("):
        return "cylinder"
    if raw.startswith("[["):
        return "subroutine"
    if raw.startswith('(["') or raw.startswith("(["):
        return "stadium"
    if raw.startswith('(("') or raw.startswith("(("):
        return "double_circle"
    if raw.startswith("{{"):
        return "hexagon"
    if raw.startswith('("') or raw.startswith("("):
        return "rounded"
    if raw.startswith("{"):
        return "diamond"
    if raw.startswith('>"') or raw.startswith(">"):
        return "flag"
    if raw.startswith("["):
        return "rect"
    return "rect"


def _clean_label(raw: str) -> str:
    """Remove surrounding brackets/quotes from node label."""
    # Strip outer shape brackets
    for start, end in [
        ('(["', '"])',), ('([', '])',), ('(("', '"))',), ('((', '))',),
        ('[("', '")]',), ('["', '"]',), ('[[', ']]',),
        ('("', '")'), ('(', ')'),
        ('{{"', '"}}',), ('{{', '}}'), ('{"', '"}'), ('{', '}'),
        ('>"', '"]'), ('>', ']'),
        ('[', ']'),
    ]:
        if len(start) == 1:
            # Simple pair
            pass
        if isinstance(start, tuple):
            start, end = start[0], end if isinstance(end, str) else end[0]
        if raw.startswith(start) and raw.endswith(end):
            raw = raw[len(start):-len(end)]
            break
    return raw.strip().strip('"').strip("'")


def _split_br_label(label: str) -> tuple[str, str]:
    """Split label on <br/> → (title, body)."""
    parts = re.split(r"<br\s*/?>", label)
    title = parts[0].strip() if parts else ""
    body = "\n".join(p.strip() for p in parts[1:] if p.strip())
    return title, body


def _resolve_layer_from_style(fill: str, stroke: str) -> str:
    """Match fill+stroke to canonical layer name."""
    fill_l = fill.lower().strip()
    stroke_l = stroke.lower().strip()
    for layer_name, colors in LAYER_PALETTE.items():
        if fill_l == colors["fill"] and stroke_l == colors["stroke"]:
            return layer_name
    # Try fill-only match
    for layer_name, colors in LAYER_PALETTE.items():
        if fill_l == colors["fill"]:
            return layer_name
    return ""


def _arrow_semantic(arrow: str, label: str) -> str:
    """Infer semantic type from arrow syntax and label."""
    label_l = label.lower()
    if "implement" in label_l:
        return "di_implements"
    if "extends" in label_l or "inherit" in label_l:
        return "inheritance"
    if "wraps" in label_l or "decorat" in label_l:
        return "decorator"
    if arrow in ("-.->" , "-.->"):
        return "di_implements"
    if arrow == "==>":
        return "critical_data_flow"
    if arrow in ("-->", "---->"):
        return "data_flow"
    return "data_flow"


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_diagram(path: Path) -> DiagramReport:
    """Parse a single Mermaid file and extract all parameters."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    rpt = DiagramReport()

    # ── Group 1: File info ────────────────────────────────────────────────
    rpt.file_path = str(path.relative_to(ROOT))
    rpt.file_name = path.name
    rpt.format = path.suffix
    rpt.directory = str(path.parent.relative_to(ROOT))

    # Determine catalog
    rel = path.relative_to(DIAGRAM_BASE) if str(path).startswith(str(DIAGRAM_BASE)) else path
    parts = rel.parts
    if parts:
        rpt.catalog = parts[0]  # architecture, class-diagrams, foundation, views

    # ── Group 2: Metadata ─────────────────────────────────────────────────
    # Title from first line
    for line in lines:
        m = _TITLE_RE.match(line.strip())
        if m:
            rpt.title = m.group(1).strip()
            break

    # Covers (second comment line)
    covers_lines: list[str] = []
    seen_title = False
    for line in lines:
        s = line.strip()
        if not s.startswith("%%"):
            break
        if s.startswith("%% @"):
            continue
        if s.startswith("%%{"):
            continue
        if _TITLE_RE.match(s):
            seen_title = True
            continue
        if seen_title and _COVERS_RE.match(s):
            covers_lines.append(_COVERS_RE.match(s).group(1).strip())
            seen_title = False  # only first line after title
    rpt.covers = " ".join(covers_lines) if covers_lines else ""
    rpt.idea = rpt.title or rpt.covers

    # Structured metadata
    for key, regex in _META_RE.items():
        for line in lines:
            m = regex.search(line)
            if m:
                val = m.group(1).strip()
                if key == "version":
                    rpt.version = val
                elif key == "date":
                    rpt.date = val
                elif key == "type":
                    rpt.diagram_type = val
                elif key == "level":
                    rpt.level = val
                elif key == "nodes":
                    rpt.nodes_declared = int(val)
                elif key == "adr":
                    rpt.adr = val
                elif key == "view":
                    rpt.view = val
                elif key == "parent":
                    rpt.parent_file = val
                elif key == "uniform":
                    rpt.uniform = val
                break

    # ── Group 4: Layout ───────────────────────────────────────────────────
    # Init block
    init_m = _INIT_RE.search(content)
    if init_m:
        rpt.init_block = init_m.group(0)
        if _ELK_RE.search(init_m.group(0)):
            rpt.layout_engine = "elk"
        er_m = _EDGE_ROUTING_RE.search(init_m.group(0))
        if er_m:
            rpt.edge_routing = er_m.group(1).upper()
    if not rpt.layout_engine:
        rpt.layout_engine = "dagre"
    if not rpt.edge_routing:
        rpt.edge_routing = "default"

    # Direction
    for line in lines:
        s = line.strip()
        if s.startswith("%%"):
            continue
        m = _GRAPH_DIR_RE.match(s)
        if m:
            rpt.direction = m.group(1).upper()
            break
        if _CLASSDIAGRAM_RE.match(s):
            rpt.diagram_type = rpt.diagram_type or "classDiagram"
            break
        if _SEQUENCE_RE.match(s):
            rpt.diagram_type = rpt.diagram_type or "sequenceDiagram"
            break
        if _STATE_RE.match(s):
            rpt.diagram_type = rpt.diagram_type or "stateDiagram"
            break
        if _ER_RE.match(s):
            rpt.diagram_type = rpt.diagram_type or "erDiagram"
            break
        if _MINDMAP_RE.match(s):
            rpt.diagram_type = rpt.diagram_type or "mindmap"
            break

    # Direction inside classDiagram
    for line in lines:
        dm = _DIRECTION_RE.match(line)
        if dm and not rpt.direction:
            rpt.direction = dm.group(1).upper()

    # ── Parse classDef definitions ────────────────────────────────────────
    class_defs: dict[str, ClassDefInfo] = {}
    for line in lines:
        m = _CLASSDEF_RE.match(line)
        if m:
            name = m.group(1)
            props = _parse_style_props(m.group(2))
            cd = ClassDefInfo(
                name=name,
                fill=props.get("fill", ""),
                stroke=props.get("stroke", ""),
                stroke_width=props.get("stroke-width", ""),
                other_props=m.group(2),
            )
            class_defs[name] = cd

    # ── Parse class assignments ───────────────────────────────────────────
    node_class_map: dict[str, str] = {}  # nodeId → classDefName
    for line in lines:
        m = _CLASS_ASSIGN_RE.match(line)
        if m:
            ids = [x.strip() for x in m.group(1).split(",")]
            cls_name = m.group(2)
            for nid in ids:
                if nid:
                    node_class_map[nid] = cls_name

    # ── Parse style directives ────────────────────────────────────────────
    node_style_map: dict[str, str] = {}  # nodeId/subgraphId → CSS
    for line in lines:
        m = _STYLE_DIRECT_RE.match(line)
        if m:
            node_style_map[m.group(1)] = m.group(2)

    # ── Parse linkStyle directives ────────────────────────────────────────
    linkstyle_map: dict[int, str] = {}  # edge_index → CSS
    linkstyle_default: str = ""
    for line in lines:
        m = _LINKSTYLE_RE.match(line)
        if m:
            target = m.group(1)
            css = m.group(2).strip()
            if target == "default":
                linkstyle_default = css
            else:
                for idx_str in target.split(","):
                    idx_str = idx_str.strip()
                    if idx_str.isdigit():
                        linkstyle_map[int(idx_str)] = css

    # ── Dispatch by diagram type ──────────────────────────────────────────
    dtype = rpt.diagram_type or ""

    if dtype == "classDiagram" or _CLASSDIAGRAM_RE.search(content):
        _parse_class_diagram(rpt, lines, class_defs, node_class_map, node_style_map)
    elif dtype == "sequenceDiagram" or _SEQUENCE_RE.search(content):
        _parse_sequence_diagram(rpt, lines)
    else:
        # flowchart / graph (default)
        _parse_flowchart(
            rpt, lines, class_defs, node_class_map,
            node_style_map, linkstyle_map, linkstyle_default,
        )

    # ── Group 3: Statistics ───────────────────────────────────────────────
    rpt.nodes_actual = len(rpt.nodes)
    rpt.edges_count = len(rpt.edges)
    edge_types = {e.get("semantic_type", "") for e in rpt.edges}
    rpt.edge_types_count = len(edge_types - {""})
    rpt.subgraphs_count = len(rpt.subgraphs)

    # ── Group 10: Quality metrics ─────────────────────────────────────────
    if rpt.nodes_actual > 0:
        rpt.edges_nodes_ratio = round(rpt.edges_count / rpt.nodes_actual, 2)

    # Hub nodes (≥6 connections)
    conn_count: dict[str, int] = {}
    for e in rpt.edges:
        conn_count[e["source"]] = conn_count.get(e["source"], 0) + 1
        conn_count[e["target"]] = conn_count.get(e["target"], 0) + 1
    rpt.hub_nodes = [
        {"id": nid, "connections": cnt}
        for nid, cnt in sorted(conn_count.items(), key=lambda x: -x[1])
        if cnt >= 6
    ]

    # Orphan nodes
    connected = set()
    for e in rpt.edges:
        connected.add(e["source"])
        connected.add(e["target"])
    all_ids = {n["id"] for n in rpt.nodes}
    rpt.orphan_nodes = sorted(all_ids - connected)

    # Max subgraph depth
    rpt.max_subgraph_depth = max(
        (s.get("depth", 0) for s in rpt.subgraphs), default=0,
    )

    # classDef list
    rpt.class_defs = [asdict(cd) for cd in class_defs.values()]

    # linkStyle list
    ls_list: list[dict] = []
    for idx, css in sorted(linkstyle_map.items()):
        props = _parse_style_props(css)
        ls_list.append({
            "edge_index": idx,
            "css": css,
            "stroke": props.get("stroke", ""),
            "stroke_width": props.get("stroke-width", ""),
            "stroke_dasharray": props.get("stroke-dasharray", ""),
        })
    if linkstyle_default:
        ls_list.insert(0, {"edge_index": "default", "css": linkstyle_default})
    rpt.link_styles = ls_list

    # Update node connection counts
    for node_dict in rpt.nodes:
        nid = node_dict["id"]
        node_dict["connection_count"] = conn_count.get(nid, 0)

    # ── Group 9: Edge labels ──────────────────────────────────────────────
    rpt.edge_labels = [
        {
            "edge_index": e["index"],
            "source": e["source"],
            "target": e["target"],
            "label": e["label"],
            "label_length": len(e["label"]),
        }
        for e in rpt.edges
        if e.get("label")
    ]

    return rpt


# ── Flowchart parser ───────────────────────────────────────────────────────────

def _parse_flowchart(
    rpt: DiagramReport,
    lines: list[str],
    class_defs: dict[str, ClassDefInfo],
    node_class_map: dict[str, str],
    node_style_map: dict[str, str],
    linkstyle_map: dict[int, str],
    linkstyle_default: str,
) -> None:
    """Parse flowchart/graph nodes, edges, subgraphs."""
    nodes_map: dict[str, NodeInfo] = {}
    subgraphs: dict[str, SubgraphInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    # Parse subgraph hierarchy
    sg_stack: list[str] = []  # stack of current subgraph ids
    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        # Subgraph open
        sm = _SUBGRAPH_LABEL_RE.match(s)
        if sm and s.strip().startswith("subgraph"):
            sg_id = sm.group(1)
            sg_label = sm.group(2) or sg_id
            parent = sg_stack[-1] if sg_stack else ""
            depth = len(sg_stack)
            sg = SubgraphInfo(
                id=sg_id,
                label=sg_label,
                parent=parent,
                depth=depth,
            )
            # Check for style
            if sg_id in node_style_map:
                props = _parse_style_props(node_style_map[sg_id])
                sg.style_fill = props.get("fill", "")
                sg.style_stroke = props.get("stroke", "")
                sg.style_stroke_width = props.get("stroke-width", "")
                sg.resolved_layer = _resolve_layer_from_style(sg.style_fill, sg.style_stroke)

            # Try to resolve layer from subgraph label/id
            if not sg.resolved_layer:
                for layer_name in LAYER_PALETTE:
                    if layer_name.lower() in sg_id.lower() or layer_name.lower() in sg_label.lower():
                        sg.resolved_layer = layer_name
                        break

            subgraphs[sg_id] = sg
            if parent and parent in subgraphs:
                subgraphs[parent].child_subgraphs.append(sg_id)
            sg_stack.append(sg_id)
            continue

        # Direction inside subgraph
        dm = _DIRECTION_RE.match(s)
        if dm and sg_stack and sg_stack[-1] in subgraphs:
            subgraphs[sg_stack[-1]].direction = dm.group(1).upper()
            continue

        # End subgraph
        if _END_RE.match(s):
            if sg_stack:
                sg_stack.pop()
            continue

        # Edges
        # Multi-target first
        mm = _MULTI_EDGE_RE.search(s)
        if mm:
            sources = [x.strip() for x in mm.group(1).split("&")]
            arrow = mm.group(2)
            label = mm.group(3) or ""
            target = mm.group(4)
            for src in sources:
                e = EdgeInfo(
                    index=edge_idx,
                    source=src,
                    target=target,
                    arrow_type=arrow,
                    label=label.strip(),
                    semantic_type=_arrow_semantic(arrow, label),
                )
                # linkStyle
                if edge_idx in linkstyle_map:
                    e.link_style = linkstyle_map[edge_idx]
                    lprops = _parse_style_props(e.link_style)
                    e.stroke_color = lprops.get("stroke", "")
                    e.stroke_width = lprops.get("stroke-width", "")
                    e.stroke_dasharray = lprops.get("stroke-dasharray", "")
                elif linkstyle_default:
                    e.link_style = linkstyle_default
                edges.append(e)
                edge_idx += 1
            continue

        # Single edge (may have multiple on one line: A --> B --> C)
        found_edges = list(_FLOW_EDGE_RE.finditer(s))
        if found_edges:
            for em in found_edges:
                src = em.group(1)
                arrow = em.group(2)
                label = em.group(3) or ""
                tgt = em.group(4)
                e = EdgeInfo(
                    index=edge_idx,
                    source=src,
                    target=tgt,
                    arrow_type=arrow,
                    label=label.strip(),
                    semantic_type=_arrow_semantic(arrow, label),
                )
                if edge_idx in linkstyle_map:
                    e.link_style = linkstyle_map[edge_idx]
                    lprops = _parse_style_props(e.link_style)
                    e.stroke_color = lprops.get("stroke", "")
                    e.stroke_width = lprops.get("stroke-width", "")
                    e.stroke_dasharray = lprops.get("stroke-dasharray", "")
                elif linkstyle_default:
                    e.link_style = linkstyle_default
                edges.append(e)
                edge_idx += 1
            # Also extract node definitions from edge lines
            # (nodes may be defined inline in edges)

        # Node definitions
        for nm in _FLOW_NODE_MULTILINE_RE.finditer(s):
            nid = nm.group(1)
            raw_label = nm.group(2)
            if nid in ("subgraph", "end", "class", "classDef", "style", "linkStyle", "click"):
                continue
            if nid not in nodes_map:
                # Detect shape from the wider context
                shape_match = re.search(
                    re.escape(nid) + r'\s*(\[\[|\[\(|\(\[|\(\(|\{\{|\["|>"|[(\[{>])',
                    s,
                )
                shape = "rect"
                if shape_match:
                    bracket = shape_match.group(1)
                    shape_map = {
                        '[(': 'cylinder', '[[': 'subroutine', '([': 'stadium',
                        '((': 'double_circle', '{{': 'hexagon', '["': 'rect',
                        '("': 'rounded', '(': 'rounded', '[': 'rect',
                        '{': 'diamond', '>"': 'flag', '>': 'flag',
                    }
                    shape = shape_map.get(bracket, "rect")

                title, body = _split_br_label(raw_label)
                # Size tier
                size_m = _SIZE_TIER_RE.search(s)
                size_tier = size_m.group(1) if size_m else ""

                # Inline class
                icm = _INLINE_CLASS_RE.search(s[s.index(nid):] if nid in s else s)
                inline_cls = icm.group(1) if icm else ""

                node = NodeInfo(
                    id=nid,
                    label=raw_label,
                    shape=shape,
                    size_tier=size_tier,
                    title_text=title,
                    body_text=body,
                    subgraph=sg_stack[-1] if sg_stack else "",
                )
                if inline_cls and inline_cls.startswith("size-"):
                    node.size_tier = inline_cls.replace("size-", "")
                elif inline_cls:
                    node.class_def = inline_cls

                nodes_map[nid] = node

                # Register in subgraph
                if sg_stack and sg_stack[-1] in subgraphs:
                    subgraphs[sg_stack[-1]].child_nodes.append(nid)

    # Apply class assignments
    for nid, cls_name in node_class_map.items():
        if nid in nodes_map and not nodes_map[nid].class_def:
            nodes_map[nid].class_def = cls_name
        elif nid not in nodes_map:
            # Node may only appear in edge lines — create stub
            nodes_map[nid] = NodeInfo(id=nid, class_def=cls_name)

    # Resolve layer from classDef
    for nid, node in nodes_map.items():
        if node.class_def and node.class_def in class_defs:
            cd = class_defs[node.class_def]
            node.style = cd.other_props
            if not node.layer:
                node.layer = _resolve_layer_from_style(cd.fill, cd.stroke)
        # Direct style
        if nid in node_style_map:
            props = _parse_style_props(node_style_map[nid])
            if not node.layer:
                node.layer = _resolve_layer_from_style(
                    props.get("fill", ""), props.get("stroke", ""),
                )

    # Apply subgraph style to nodes missing layer
    rpt.subgraphs = [asdict(sg) for sg in subgraphs.values()]

    # Resolve subgraph styles from node_style_map
    for sg in subgraphs.values():
        if sg.id in node_style_map and not sg.style_fill:
            props = _parse_style_props(node_style_map[sg.id])
            sg.style_fill = props.get("fill", "")
            sg.style_stroke = props.get("stroke", "")
            sg.style_stroke_width = props.get("stroke-width", "")
            sg.resolved_layer = _resolve_layer_from_style(sg.style_fill, sg.style_stroke)

    # Update subgraphs in report
    rpt.subgraphs = [asdict(sg) for sg in subgraphs.values()]

    # Layers = unique layers used
    used_layers: dict[str, dict] = {}
    for sg in subgraphs.values():
        if sg.resolved_layer and sg.resolved_layer not in used_layers:
            palette = LAYER_PALETTE.get(sg.resolved_layer, {})
            used_layers[sg.resolved_layer] = {
                "name": sg.resolved_layer,
                "fill": palette.get("fill", sg.style_fill),
                "stroke": palette.get("stroke", sg.style_stroke),
                "class_def": "",
                "subgraph_ids": [],
            }
        if sg.resolved_layer:
            used_layers[sg.resolved_layer]["subgraph_ids"].append(sg.id)

    # Also from classDefs
    for cd in class_defs.values():
        layer = _resolve_layer_from_style(cd.fill, cd.stroke)
        if layer and layer not in used_layers:
            used_layers[layer] = {
                "name": layer,
                "fill": cd.fill,
                "stroke": cd.stroke,
                "class_def": cd.name,
                "subgraph_ids": [],
            }
        elif layer:
            used_layers[layer]["class_def"] = cd.name

    rpt.layers = list(used_layers.values())
    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


# ── Class diagram parser ──────────────────────────────────────────────────────

def _parse_class_diagram(
    rpt: DiagramReport,
    lines: list[str],
    class_defs: dict[str, ClassDefInfo],
    node_class_map: dict[str, str],
    node_style_map: dict[str, str],
) -> None:
    """Parse classDiagram nodes, relations, styles."""
    nodes_map: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    # Parse class blocks
    current_class: str | None = None
    current_stereotype = ""
    current_attrs: list[str] = []
    current_methods: list[str] = []

    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        # Class block start
        cm = _CD_CLASS_RE.match(s)
        if cm:
            current_class = cm.group(1)
            current_stereotype = ""
            current_attrs = []
            current_methods = []
            continue

        # Inside class block
        if current_class:
            if s == "}":
                node = NodeInfo(
                    id=current_class,
                    label=current_class,
                    shape="class_box",
                    stereotype=current_stereotype,
                    attributes=list(current_attrs),
                    methods=list(current_methods),
                    title_text=current_class,
                    body_text="\n".join(current_attrs + current_methods),
                )
                nodes_map[current_class] = node
                current_class = None
                continue

            # Stereotype
            if s.startswith("<<") and s.endswith(">>"):
                current_stereotype = s
                continue

            # Member
            mm = _CD_MEMBER_RE.match(s)
            if mm:
                visibility = mm.group(1)
                member = mm.group(2).strip()
                if "(" in member:
                    current_methods.append(f"{visibility} {member}")
                else:
                    current_attrs.append(f"{visibility} {member}")
                continue

            # Blank line inside class (padding)
            continue

        # Relations (outside class blocks)
        rm = _CD_RELATION_RE.match(s)
        if rm:
            src = rm.group(1)
            arrow = rm.group(2)
            tgt = rm.group(3)
            label = rm.group(4) or ""
            e = EdgeInfo(
                index=edge_idx,
                source=src,
                target=tgt,
                arrow_type=arrow,
                label=label.strip(),
                semantic_type="inheritance" if "<|" in arrow else "association",
            )
            edges.append(e)
            edge_idx += 1
            continue

    # Apply styles
    for nid, node in nodes_map.items():
        if nid in node_class_map:
            node.class_def = node_class_map[nid]
        if nid in node_style_map:
            props = _parse_style_props(node_style_map[nid])
            node.layer = _resolve_layer_from_style(
                props.get("fill", ""), props.get("stroke", ""),
            )
            node.style = node_style_map[nid]

    # Layers from styles
    used_layers: dict[str, dict] = {}
    for nid, css_str in node_style_map.items():
        props = _parse_style_props(css_str)
        layer = _resolve_layer_from_style(props.get("fill", ""), props.get("stroke", ""))
        if layer and layer not in used_layers:
            used_layers[layer] = {
                "name": layer,
                "fill": props.get("fill", ""),
                "stroke": props.get("stroke", ""),
                "class_def": "",
                "subgraph_ids": [],
            }

    rpt.layers = list(used_layers.values())
    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


# ── Sequence diagram parser ───────────────────────────────────────────────────

def _parse_sequence_diagram(
    rpt: DiagramReport,
    lines: list[str],
) -> None:
    """Parse sequenceDiagram participants and messages."""
    nodes_map: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        # Participant
        pm = _SEQ_PARTICIPANT_RE.match(s)
        if pm:
            pid = pm.group(1)
            alias = pm.group(2) or pid
            nodes_map[pid] = NodeInfo(id=pid, label=alias, shape="actor")
            continue

        # Message
        mm = _SEQ_MESSAGE_RE.match(s)
        if mm:
            src = mm.group(1)
            arrow = mm.group(2)
            tgt = mm.group(3)
            msg = mm.group(4).strip()
            e = EdgeInfo(
                index=edge_idx,
                source=src,
                target=tgt,
                arrow_type=arrow,
                label=msg,
                semantic_type="sync_call" if ">>" in arrow else "async_call",
            )
            edges.append(e)
            edge_idx += 1

            # Auto-create participants
            for p in (src, tgt):
                if p not in nodes_map:
                    nodes_map[p] = NodeInfo(id=p, label=p, shape="actor")

    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


# ── File discovery ─────────────────────────────────────────────────────────────

def find_diagrams(targets: list[Path]) -> list[Path]:
    """Find all diagram files from given targets."""
    files: list[Path] = []
    seen: set[Path] = set()

    for target in targets:
        if target.is_file():
            if target.suffix in SUPPORTED_SUFFIXES and not target.name.startswith("_"):
                if target not in seen:
                    seen.add(target)
                    files.append(target)
        elif target.is_dir():
            for ext in SUPPORTED_SUFFIXES:
                for f in sorted(target.rglob(f"*{ext}")):
                    if (
                        f not in seen
                        and not f.name.startswith("_")
                        and not EXCLUDED_PARTS.intersection(f.parts)
                    ):
                        seen.add(f)
                        files.append(f)

    return sorted(files)


# ── Output formatters ──────────────────────────────────────────────────────────

def _to_json(reports: list[DiagramReport]) -> str:
    return json.dumps(
        {
            "total_diagrams": len(reports),
            "diagrams": [asdict(r) for r in reports],
        },
        indent=2,
        ensure_ascii=False,
    )


def _to_markdown(reports: list[DiagramReport]) -> str:
    """Generate markdown summary table + per-diagram detail."""
    lines: list[str] = []
    lines.append("# Diagram Parameters Inventory")
    lines.append(f"\nTotal diagrams: **{len(reports)}**\n")

    # Summary table
    lines.append("## Summary Table\n")
    lines.append("| # | File | Type | Nodes | Edges | E/N Ratio | Engine | Direction | Layers | Subgraphs |")
    lines.append("|---|------|------|-------|-------|-----------|--------|-----------|--------|-----------|")
    for i, r in enumerate(reports, 1):
        lines.append(
            f"| {i} | `{r.file_name}` | {r.diagram_type} | "
            f"{r.nodes_actual} | {r.edges_count} | {r.edges_nodes_ratio} | "
            f"{r.layout_engine} | {r.direction} | {len(r.layers)} | {r.subgraphs_count} |"
        )

    # Per-diagram detail
    for i, r in enumerate(reports, 1):
        lines.append(f"\n---\n## {i}. {r.file_name}\n")

        lines.append("### 1. File Info\n")
        lines.append(f"- **Path**: `{r.file_path}`")
        lines.append(f"- **Format**: `{r.format}`")
        lines.append(f"- **Directory**: `{r.directory}`")
        lines.append(f"- **Catalog**: `{r.catalog}`")
        lines.append(f"- **Idea**: {r.idea}")

        lines.append("\n### 2. Metadata\n")
        lines.append(f"- **Title**: {r.title}")
        lines.append(f"- **Covers**: {r.covers}")
        lines.append(f"- **@version**: {r.version}")
        lines.append(f"- **@date**: {r.date}")
        lines.append(f"- **@type**: {r.diagram_type}")
        lines.append(f"- **@level**: {r.level}")
        lines.append(f"- **@nodes (declared)**: {r.nodes_declared}")
        lines.append(f"- **@adr**: {r.adr}")
        if r.view:
            lines.append(f"- **View**: {r.view}")
        if r.parent_file:
            lines.append(f"- **Parent**: {r.parent_file}")

        lines.append("\n### 3. Statistics\n")
        lines.append(f"- **Nodes (actual)**: {r.nodes_actual}")
        lines.append(f"- **Edges**: {r.edges_count}")
        lines.append(f"- **Edge semantic types**: {r.edge_types_count}")
        lines.append(f"- **Subgraphs**: {r.subgraphs_count}")

        lines.append("\n### 4. Layout\n")
        lines.append(f"- **Direction**: {r.direction}")
        lines.append(f"- **Layout engine**: {r.layout_engine}")
        lines.append(f"- **Edge routing**: {r.edge_routing}")

        if r.layers:
            lines.append("\n### 5. Layers\n")
            lines.append("| Layer | Fill | Stroke | classDef |")
            lines.append("|-------|------|--------|----------|")
            for l in r.layers:
                lines.append(f"| {l['name']} | `{l['fill']}` | `{l['stroke']}` | `{l.get('class_def', '')}` |")

        if r.subgraphs:
            lines.append("\n### 6. Subgraphs\n")
            lines.append("| ID | Label | Parent | Depth | Layer | Nodes | Sub-subgraphs |")
            lines.append("|----|-------|--------|-------|-------|-------|---------------|")
            for sg in r.subgraphs:
                lines.append(
                    f"| `{sg['id']}` | {sg['label']} | `{sg['parent']}` | "
                    f"{sg['depth']} | {sg['resolved_layer']} | "
                    f"{len(sg['child_nodes'])} | {len(sg['child_subgraphs'])} |"
                )

        if r.nodes:
            lines.append("\n### 7. Nodes\n")
            lines.append("| ID | Label/Title | Shape | Layer | Subgraph | classDef | Size | Connections |")
            lines.append("|----|-------------|-------|-------|----------|----------|------|-------------|")
            for n in r.nodes:
                title = n.get("title_text", n.get("label", ""))[:30]
                lines.append(
                    f"| `{n['id']}` | {title} | {n['shape']} | "
                    f"{n['layer']} | `{n['subgraph']}` | "
                    f"`{n['class_def']}` | {n['size_tier']} | {n['connection_count']} |"
                )

        if r.edges:
            lines.append("\n### 8. Edges\n")
            lines.append("| # | Source | Target | Arrow | Type | Label | Stroke | Width | Dash |")
            lines.append("|---|--------|--------|-------|------|-------|--------|-------|------|")
            for e in r.edges:
                lines.append(
                    f"| {e['index']} | `{e['source']}` | `{e['target']}` | "
                    f"`{e['arrow_type']}` | {e['semantic_type']} | "
                    f"{e['label']} | `{e['stroke_color']}` | "
                    f"`{e['stroke_width']}` | `{e['stroke_dasharray']}` |"
                )

        if r.edge_labels:
            lines.append("\n### 9. Edge Labels\n")
            lines.append("| Edge # | Source→Target | Label | Length |")
            lines.append("|--------|--------------|-------|--------|")
            for el in r.edge_labels:
                lines.append(
                    f"| {el['edge_index']} | `{el['source']}`→`{el['target']}` | "
                    f"{el['label']} | {el['label_length']} |"
                )

        lines.append("\n### 10. Quality Metrics\n")
        lines.append(f"- **Edges/Nodes ratio**: {r.edges_nodes_ratio}")
        if r.hub_nodes:
            hubs = ", ".join(f"`{h['id']}` ({h['connections']})" for h in r.hub_nodes)
            lines.append(f"- **Hub nodes (>=6 conn)**: {hubs}")
        if r.orphan_nodes:
            lines.append(f"- **Orphan nodes**: {', '.join(f'`{o}`' for o in r.orphan_nodes)}")
        lines.append(f"- **Max subgraph depth**: {r.max_subgraph_depth}")

    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract comprehensive parameters from Mermaid diagrams.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files/directories to analyze (default: all diagram dirs).",
    )
    parser.add_argument("--out", help="Output file path (default: stdout).")
    parser.add_argument("--markdown", action="store_true", help="Output as Markdown.")
    parser.add_argument("--json", action="store_true", dest="json_out", help="Output as JSON (default).")

    args = parser.parse_args()

    targets = [Path(p) for p in args.paths] if args.paths else [DIAGRAM_BASE]
    diagrams = find_diagrams(targets)

    if not diagrams:
        print("No diagram files found.", file=sys.stderr)
        return 1

    reports: list[DiagramReport] = []
    for path in diagrams:
        try:
            rpt = parse_diagram(path)
            reports.append(rpt)
        except Exception as exc:
            print(f"ERROR parsing {path}: {exc}", file=sys.stderr)

    if args.markdown:
        output = _to_markdown(reports)
    else:
        output = _to_json(reports)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written {len(reports)} diagram reports to {args.out}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
