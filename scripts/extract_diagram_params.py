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
 7. Nodes (id, label, shape, layer, subgraph, classDef, size tier, text,
          estimated width/height, font sizes, text alignment)
 8. Edges (source, target, arrow type, label, linkStyle, stroke params)
 9. Edge labels (index, text, font size, font color)
10. Computed quality metrics (edges/nodes ratio, hub nodes, orphans)

Font sizes, colors, and text alignment are resolved from the project's
theme/mermaid-config.json and theme/custom.css (ADR-040 canonical theme).

Node width/height are *estimated* using the same heuristic as Mermaid's dagre
layout: text_measurement_approximation + 2×padding, constrained by the CSS
size-tier minimums (size-sm/md/lg) and @uniform annotations.

Usage:
    python scripts/extract_diagram_params.py                        # all → JSON stdout
    python scripts/extract_diagram_params.py --out report.json      # write to file
    python scripts/extract_diagram_params.py --markdown --out r.md  # markdown report
    python scripts/extract_diagram_params.py <path>                 # specific file/dir
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# Constants
# ══════════════════════════════════════════════════════════════════════════════

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_BASE = ROOT / "docs" / "02-architecture" / "mmd-diagrams"
THEME_DIR = DIAGRAM_BASE / "theme"
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}
EXCLUDED_PARTS = {"99-archive"}

# ── Canonical palette (ADR-040) ──────────────────────────────────────────────

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

# ── Theme constants (from mermaid-config.json + custom.css) ──────────────────
# These are loaded lazily from the actual files when possible, with these
# values as compile-time defaults matching the checked-in theme.

_THEME_CACHE: dict | None = None


def _load_theme() -> dict:
    """Load and cache theme config from mermaid-config.json."""
    global _THEME_CACHE
    if _THEME_CACHE is not None:
        return _THEME_CACHE

    config_path = THEME_DIR / "mermaid-config.json"
    if config_path.exists():
        _THEME_CACHE = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        _THEME_CACHE = {}
    return _THEME_CACHE


def _get_theme_var(key: str, default: str = "") -> str:
    cfg = _load_theme()
    return cfg.get("themeVariables", {}).get(key, default)


# ── Font / visual constants derived from theme + CSS ─────────────────────────
# Source: theme/mermaid-config.json  themeVariables.fontSize
#         theme/custom.css           .edgeLabel, g.label-group, etc.

class ThemeParams:
    """All visual parameters resolved from mermaid-config.json + custom.css."""

    # Flowchart
    flowchart_padding: int = 24         # mermaid-config.json → flowchart.padding
    flowchart_node_spacing: int = 50    # flowchart.nodeSpacing
    flowchart_rank_spacing: int = 45    # flowchart.rankSpacing
    flowchart_wrapping_width: int = 200 # flowchart.wrappingWidth

    # Fonts (px) — resolved from CSS overrides
    global_font_size: int = 14          # themeVariables.fontSize
    node_text_font_size: int = 14       # default node label
    node_text_color: str = "#212121"    # themeVariables.nodeTextColor
    node_text_align: str = "center"     # Mermaid default

    # Class diagram fonts (custom.css overrides)
    class_title_font_size: int = 15     # g.label-group .nodeLabel
    class_title_font_weight: int = 700
    class_stereotype_font_size: int = 11  # g.annotation-group .nodeLabel
    class_member_font_size: int = 12    # g.members-group, g.methods-group
    class_text_font_size: int = 13      # g.classGroup text

    # Cluster / subgraph
    cluster_font_size: int = 15         # .cluster text
    cluster_font_weight: int = 600

    # Edge labels (custom.css .edgeLabel)
    edge_label_font_size: int = 12
    edge_label_font_color: str = "#111827"  # .edgeLabel span { color }
    edge_label_bg_color: str = "#ffffff"
    edge_label_line_height: float = 1.1

    # Sequence diagram
    seq_message_font_size: int = 13     # .messageText
    seq_message_align: str = "center"   # sequence.messageAlign
    seq_actor_width: int = 180          # sequence.width
    seq_actor_height: int = 50          # sequence.height
    seq_actor_text_color: str = "#1e40af"  # themeVariables.actorTextColor

    # ER diagram
    er_font_size: int = 13              # er.fontSize

    # State diagram
    state_padding: int = 12             # state.padding

    # Mindmap
    mindmap_padding: int = 20           # mindmap.padding

    # CSS size tiers (custom.css .node.size-* foreignObject > div)
    size_tiers: dict[str, dict[str, int]] = {
        "sm": {"min_width": 180, "min_height": 80},
        "md": {"min_width": 260, "min_height": 140},
        "lg": {"min_width": 340, "min_height": 200},
    }

    # Line height multiplier for text height estimation
    line_height_px: float = 1.4  # standard line-height factor

    # Node stroke
    node_stroke_width: float = 1.5      # .node rect { stroke-width }
    node_border_radius: int = 8         # rx/ry

    @classmethod
    def load_from_project(cls) -> "ThemeParams":
        """Create ThemeParams, overriding defaults from actual project files."""
        params = cls()
        cfg = _load_theme()

        tv = cfg.get("themeVariables", {})
        fc = cfg.get("flowchart", {})
        seq = cfg.get("sequence", {})
        er = cfg.get("er", {})
        state = cfg.get("state", {})
        mm = cfg.get("mindmap", {})

        # Global
        fs_str = tv.get("fontSize", "14px")
        params.global_font_size = int(re.sub(r"[^\d]", "", fs_str) or 14)
        params.node_text_font_size = params.global_font_size
        params.node_text_color = tv.get("nodeTextColor", params.node_text_color)

        # Flowchart
        params.flowchart_padding = fc.get("padding", params.flowchart_padding)
        params.flowchart_node_spacing = fc.get("nodeSpacing", params.flowchart_node_spacing)
        params.flowchart_rank_spacing = fc.get("rankSpacing", params.flowchart_rank_spacing)
        params.flowchart_wrapping_width = fc.get("wrappingWidth", params.flowchart_wrapping_width)

        # Sequence
        params.seq_message_align = seq.get("messageAlign", params.seq_message_align)
        params.seq_actor_width = seq.get("width", params.seq_actor_width)
        params.seq_actor_height = seq.get("height", params.seq_actor_height)
        params.seq_actor_text_color = tv.get("actorTextColor", params.seq_actor_text_color)

        # ER
        params.er_font_size = er.get("fontSize", params.er_font_size)

        # State
        params.state_padding = state.get("padding", params.state_padding)

        # Mindmap
        params.mindmap_padding = mm.get("padding", params.mindmap_padding)

        return params


# ── Character width estimation ───────────────────────────────────────────────
# Mermaid uses getBBox() which requires DOM rendering.  We approximate using
# average character widths for the Inter font family at the relevant size.
# These are empirical averages (Inter Regular, measured via fonttools):
#   - Uppercase letter ≈ 0.62 × fontSize
#   - Lowercase letter ≈ 0.50 × fontSize
#   - Mixed avg         ≈ 0.54 × fontSize
#   - Space             ≈ 0.25 × fontSize
# For simplicity we use a single factor per font-size.

CHAR_WIDTH_FACTOR = 0.54  # average char width / font-size
SPACE_WIDTH_FACTOR = 0.25


def _estimate_text_width(text: str, font_size: int) -> float:
    """Estimate rendered text width in px using char-width heuristic."""
    if not text:
        return 0.0
    width = 0.0
    for ch in text:
        if ch == " ":
            width += font_size * SPACE_WIDTH_FACTOR
        else:
            width += font_size * CHAR_WIDTH_FACTOR
    return width


def _estimate_node_size(
    label: str,
    shape: str,
    size_tier: str,
    uniform_w: int | None,
    uniform_h: int | None,
    diagram_type: str,
    theme: ThemeParams,
) -> tuple[int, int]:
    """Estimate node width × height in px.

    Priority:
    1. @uniform annotation (exact override)
    2. CSS size-tier minimums
    3. Text measurement heuristic + 2×padding
    """
    # Determine padding and font size based on diagram type
    if diagram_type == "classDiagram":
        padding = 16  # class.padding
        font_size = theme.class_title_font_size
    elif diagram_type == "sequenceDiagram":
        return (theme.seq_actor_width, theme.seq_actor_height)
    elif diagram_type == "stateDiagram":
        padding = theme.state_padding
        font_size = theme.global_font_size
    else:  # flowchart / graph
        padding = theme.flowchart_padding
        font_size = theme.node_text_font_size

    # Split label into lines on <br/> tags
    lines = re.split(r"<br\s*/?>", label) if label else [""]
    # Strip HTML and clean lines
    clean_lines = []
    for ln in lines:
        clean = re.sub(r"<[^>]+>", "", ln).strip()
        # skip ━━ separator lines and empty padding lines
        if clean and not re.fullmatch(r"[━─═]+", clean):
            clean_lines.append(clean)

    if not clean_lines:
        clean_lines = [""]

    # Text width = max line width
    max_line_w = max(_estimate_text_width(ln, font_size) for ln in clean_lines)
    text_w = max_line_w + 2 * padding

    # Text height = lines × line_height + 2 × padding
    line_h = font_size * theme.line_height_px
    text_h = len(clean_lines) * line_h + 2 * padding

    # Shape adjustments
    if shape in ("circle", "double_circle"):
        diameter = max(text_w, text_h)
        text_w = text_h = diameter
    elif shape == "diamond":
        # Diamond inscribes content rotated 45°
        diagonal = math.sqrt(text_w**2 + text_h**2)
        text_w = text_h = diagonal
    elif shape == "hexagon":
        text_w *= 1.15  # extra horizontal space for angled edges

    w = int(math.ceil(text_w))
    h = int(math.ceil(text_h))

    # Apply CSS size-tier minimums
    if size_tier in ThemeParams.size_tiers:
        tier = ThemeParams.size_tiers[size_tier]
        w = max(w, tier["min_width"])
        h = max(h, tier["min_height"])

    # Apply @uniform override (takes precedence)
    if uniform_w is not None:
        w = uniform_w
    if uniform_h is not None:
        h = uniform_h

    return (w, h)


# ══════════════════════════════════════════════════════════════════════════════
# Regexes
# ══════════════════════════════════════════════════════════════════════════════

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
_TITLE_ALT_RE = re.compile(r"^%%\s*Title:\s*(.+)", re.IGNORECASE)
_COVERS_RE = re.compile(r"^%%\s*(?!@|BioETL|Title:)(.+)")
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

# Flowchart parsing
_FLOW_NODE_MULTILINE_RE = re.compile(
    r'([A-Za-z_][A-Za-z0-9_]*)\s*(\[\("|"\)\]|\[\[|\["|>\"|'
    r'\(\["|"\]\)|\(\("|\("\)|\{\{"|\{"|[(\[{>])'
    r'((?:[^"\]}>)]|\\.)*)(?:"\)?\]?\)?}?}?)?',
)
_SUBGRAPH_LABEL_RE = re.compile(
    r'^\s*subgraph\s+([A-Za-z_][A-Za-z0-9_]*)(?:\s*\["([^"]+)"\])?\s*$'
)
_END_RE = re.compile(r"^\s*end\s*$")
_DIRECTION_RE = re.compile(r"^\s*direction\s+(TB|BT|LR|RL|TD)\s*$", re.IGNORECASE)
_SIZE_TIER_RE = re.compile(r":::size-(sm|md|lg)")
_INLINE_CLASS_RE = re.compile(r":::([A-Za-z_][A-Za-z0-9_-]*)")

# Edges
_FLOW_EDGE_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*)"
    r"\s*"
    r"(---->|--->|-->|-.->|==>|--[|]|-.[-]?[|])"
    r'(?:\s*\|"?([^"|]*?)"?\|)?'
    r"\s*"
    r"([A-Za-z_][A-Za-z0-9_]*)"
)
_MULTI_EDGE_RE = re.compile(
    r"([A-Za-z_][A-Za-z0-9_]*(?:\s*&\s*[A-Za-z_][A-Za-z0-9_]*)+)"
    r"\s*(-->|-.->|==>)"
    r'(?:\s*\|"?([^"|]*?)"?\|)?'
    r"\s*([A-Za-z_][A-Za-z0-9_]*)"
)

# classDef / class / style / linkStyle
_CLASSDEF_RE = re.compile(r"^\s*classDef\s+([A-Za-z_][A-Za-z0-9_-]*)\s+(.+)$")
_CLASS_ASSIGN_RE = re.compile(r"^\s*class\s+([\w,\s]+)\s+([A-Za-z_][A-Za-z0-9_-]*)\s*$")
_STYLE_DIRECT_RE = re.compile(r"^\s*style\s+(\S+)\s+(.+)$")
_LINKSTYLE_RE = re.compile(r"^\s*linkStyle\s+(\S+)\s+(.+)$")

# classDiagram
_CD_CLASS_RE = re.compile(r"^\s*class\s+([A-Za-z_]\w*)\s*\{")
_CD_MEMBER_RE = re.compile(r"^\s*([+\-#~])\s*(.+)$")
_CD_RELATION_RE = re.compile(
    r"^\s*([A-Za-z_]\w*)\s*"
    r"(<\|--|<\|\.\.|\.\.|--|-->|\.\.>|--\*|--o|<\|--|\*--|o--)"
    r"\s*([A-Za-z_]\w*)"
    r"(?:\s*:\s*(.+))?$"
)

# sequenceDiagram
_SEQ_PARTICIPANT_RE = re.compile(
    r"^\s*(?:participant|actor)\s+(\S+)(?:\s+as\s+(.+))?$"
)
_SEQ_MESSAGE_RE = re.compile(
    r"^\s*(\S+)\s*(->>|-->>|-\)|--\)|->|-->)\s*(\S+)\s*:\s*(.*)$"
)

# stateDiagram
_STATE_DECL_RE = re.compile(r"^\s*state\s+(\w+)\s*\{?\s*$")
_STATE_LABEL_RE = re.compile(r"^\s*(\w+)\s*:\s*(.+)$")
_STATE_TRANS_RE = re.compile(
    r"^\s*(\[?\*?\]?|\w+)\s*(-->)\s*(\[?\*?\]?|\w+)"
    r"(?:\s*:\s*(.+))?$"
)

# Uniform annotation parser
_UNIFORM_WIDTH_RE = re.compile(r"width=(\d+)")
_UNIFORM_HEIGHT_RE = re.compile(r"height=(\d+)")

# Flowchart node definition — comprehensive capture of all shapes
# We capture node definitions from lines that contain bracket patterns
_NODE_DEF_RE = re.compile(
    r"""(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)    # node id
        \s*
        (\[\("|\(\["|\(\("|\{\{"|\[\[|       # multi-char openers
         \["|>"|                              # 2-char openers
         \("|                                 # 2-char openers
         \{"|                                 # 2-char openers
         [({\[>])                             # single-char openers
    """,
    re.VERBOSE,
)


# ══════════════════════════════════════════════════════════════════════════════
# Data classes
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeInfo:
    id: str
    label: str = ""
    shape: str = "rect"
    layer: str = ""
    subgraph: str = ""
    class_def: str = ""
    style: str = ""
    size_tier: str = ""
    title_text: str = ""
    body_text: str = ""
    connection_count: int = 0
    # Estimated dimensions (px)
    est_width: int = 0
    est_height: int = 0
    # Font parameters
    title_font_size: int = 0
    body_font_size: int = 0
    text_color: str = ""
    text_align: str = ""
    # Class diagram specifics
    stereotype: str = ""
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


@dataclass
class EdgeInfo:
    index: int
    source: str
    target: str
    arrow_type: str
    label: str = ""
    semantic_type: str = ""
    link_style: str = ""
    stroke_color: str = ""
    stroke_width: str = ""
    stroke_dasharray: str = ""
    # Derived display fields (resolved from arrow_type syntax)
    edge_type: str = ""       # solid / dashed / thick
    line_style: str = ""      # solid / dashed / dotted
    arrow_start: str = ""     # none / open / filled
    arrow_end: str = ""       # open / filled / none


@dataclass
class SubgraphInfo:
    id: str
    label: str = ""
    parent: str = ""
    depth: int = 0
    style_fill: str = ""
    style_stroke: str = ""
    style_stroke_width: str = ""
    resolved_layer: str = ""
    direction: str = ""
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
    format: str = ""
    directory: str = ""
    catalog: str = ""
    idea: str = ""

    # Group 2: Metadata
    title: str = ""
    covers: str = ""
    version: str = ""
    date: str = ""
    diagram_type: str = ""
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
    direction: str = ""
    layout_engine: str = ""
    edge_routing: str = ""
    init_block: str = ""

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

    # Theme params (global, resolved from project files)
    theme: dict = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Parsing helpers
# ══════════════════════════════════════════════════════════════════════════════

def _parse_style_props(style_str: str) -> dict[str, str]:
    """Parse CSS-like props: 'fill:#abc,stroke:#def' → dict."""
    props: dict[str, str] = {}
    for part in style_str.split(","):
        part = part.strip()
        if ":" in part:
            k, v = part.split(":", 1)
            props[k.strip()] = v.strip()
    return props


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
    if arrow in ("-.->",):
        return "di_implements"
    if arrow == "==>":
        return "critical_data_flow"
    return "data_flow"


def _resolve_edge_display(edge: EdgeInfo) -> None:
    """Resolve edge_type, line_style, arrow_start, arrow_end from arrow_type syntax."""
    a = edge.arrow_type

    # Mermaid edge syntax:
    #  -->   solid line, filled arrow end
    #  --->  solid line, filled arrow end (longer)
    #  ---->  solid line, filled arrow end (longest)
    #  -.->  dashed line, filled arrow end
    #  ==>   thick line, filled arrow end
    #  --    solid line, no arrow
    #  --|   solid line, no arrow (with text block)
    #  -.-|  dashed line, no arrow (with text block)
    #  ->>   solid line, open arrow (sequence)
    #  -->>  dashed line, open arrow (sequence)
    #  -)    solid line, open arrow (sequence async)
    #  --)   dashed line, open arrow (sequence async)
    #  ->    solid line, open arrow (sequence)
    #  <|--  inheritance (class diagrams)
    #  <|..  implementation (class diagrams)
    #  ..    dotted line
    #  *--   composition
    #  o--   aggregation

    # Determine line_style / edge_type
    if "==" in a:
        edge.edge_type = "thick"
        edge.line_style = "solid"
    elif "-." in a or ".." in a or "-.." in a:
        edge.edge_type = "dashed"
        edge.line_style = "dashed"
    elif edge.stroke_dasharray:
        edge.edge_type = "dashed"
        edge.line_style = "dashed"
    else:
        edge.edge_type = "solid"
        edge.line_style = "solid"

    # Arrow end
    if a.endswith(">>"):
        edge.arrow_end = "open"
    elif a.endswith(">") or a.endswith("->"):
        edge.arrow_end = "filled"
    elif a.endswith("|"):
        edge.arrow_end = "none"
    elif a.endswith(")"):
        edge.arrow_end = "open"
    else:
        edge.arrow_end = "filled"

    # Arrow start
    if a.startswith("<|"):
        edge.arrow_start = "filled"
    elif a.startswith("*"):
        edge.arrow_start = "filled"  # composition
    elif a.startswith("o"):
        edge.arrow_start = "open"  # aggregation
    elif a.startswith("<"):
        edge.arrow_start = "open"
    else:
        edge.arrow_start = "none"


def _detect_diagram_type(lines: list[str]) -> str:
    """Detect diagram type from first non-comment content line."""
    for line in lines:
        s = line.strip()
        if not s or s.startswith("%%"):
            continue
        if _GRAPH_DIR_RE.match(s) or s.lower().startswith(("graph ", "flowchart ")):
            return "flowchart"
        if _CLASSDIAGRAM_RE.match(s):
            return "classDiagram"
        if _SEQUENCE_RE.match(s):
            return "sequenceDiagram"
        if _STATE_RE.match(s):
            return "stateDiagram"
        if _ER_RE.match(s):
            return "erDiagram"
        if _MINDMAP_RE.match(s):
            return "mindmap"
        # Not a known header line, skip
        break
    return ""


def _detect_shape_from_bracket(bracket: str) -> str:
    """Map opening bracket to shape name."""
    m = {
        '["': "rect", "[[": "subroutine", '>("': "flag", '>': "flag",
        '("': "rounded", "(": "rounded",
        '(["': "stadium", '([': "stadium",
        '(("': "double_circle", "((": "double_circle",
        '[("': "cylinder", "[(": "cylinder",
        '{{"': "hexagon", "{{": "hexagon",
        '{"': "diamond", "{": "diamond",
        "[": "rect",
    }
    return m.get(bracket, "rect")


def _parse_uniform(uniform_str: str) -> tuple[int | None, int | None]:
    """Parse @uniform annotation → (width, height) or None."""
    w_m = _UNIFORM_WIDTH_RE.search(uniform_str)
    h_m = _UNIFORM_HEIGHT_RE.search(uniform_str)
    w = int(w_m.group(1)) if w_m else None
    h = int(h_m.group(1)) if h_m else None
    return w, h


# ══════════════════════════════════════════════════════════════════════════════
# Flowchart parser
# ══════════════════════════════════════════════════════════════════════════════

def _parse_flowchart(
    rpt: DiagramReport,
    lines: list[str],
    class_defs: dict[str, ClassDefInfo],
    node_class_map: dict[str, str],
    node_style_map: dict[str, str],
    linkstyle_map: dict[int, str],
    linkstyle_default: str,
    theme: ThemeParams,
) -> None:
    """Parse flowchart/graph: nodes, edges, subgraphs."""
    nodes_map: dict[str, NodeInfo] = {}
    subgraphs: dict[str, SubgraphInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    # Parse @uniform
    uniform_w, uniform_h = _parse_uniform(rpt.uniform) if rpt.uniform else (None, None)

    reserved = {"subgraph", "end", "class", "classDef", "style", "linkStyle",
                "click", "direction", "graph", "flowchart"}

    sg_stack: list[str] = []

    for line in lines:
        s = line.strip()
        if not s or s.startswith("%%"):
            continue
        if s.startswith("linkStyle") or s.startswith("classDef") or s.startswith("class "):
            # handled separately
            if _CLASS_ASSIGN_RE.match(s):
                pass  # already parsed
            continue
        if s.startswith("style "):
            continue

        # Subgraph
        sm = _SUBGRAPH_LABEL_RE.match(s)
        if sm:
            sg_id = sm.group(1)
            sg_label = sm.group(2) or sg_id
            parent = sg_stack[-1] if sg_stack else ""
            depth = len(sg_stack)
            sg = SubgraphInfo(id=sg_id, label=sg_label, parent=parent, depth=depth)
            for layer_name in LAYER_PALETTE:
                if layer_name.lower() in sg_id.lower() or layer_name.lower() in sg_label.lower():
                    sg.resolved_layer = layer_name
                    break
            subgraphs[sg_id] = sg
            if parent and parent in subgraphs:
                subgraphs[parent].child_subgraphs.append(sg_id)
            sg_stack.append(sg_id)
            continue

        # Direction
        dm = _DIRECTION_RE.match(s)
        if dm:
            if sg_stack and sg_stack[-1] in subgraphs:
                subgraphs[sg_stack[-1]].direction = dm.group(1).upper()
            continue

        # End
        if _END_RE.match(s):
            if sg_stack:
                sg_stack.pop()
            continue

        # Edges — multi-target first
        mm = _MULTI_EDGE_RE.search(s)
        if mm:
            sources = [x.strip() for x in mm.group(1).split("&")]
            arrow = mm.group(2)
            label = mm.group(3) or ""
            target = mm.group(4)
            for src in sources:
                e = EdgeInfo(
                    index=edge_idx, source=src, target=target,
                    arrow_type=arrow, label=label.strip(),
                    semantic_type=_arrow_semantic(arrow, label),
                )
                _apply_linkstyle(e, edge_idx, linkstyle_map, linkstyle_default)
                edges.append(e)
                edge_idx += 1
                # auto-create stub nodes for edge-only references
                for nid in (src, target):
                    if nid not in nodes_map and nid not in reserved:
                        nodes_map[nid] = NodeInfo(id=nid, label=nid, subgraph=sg_stack[-1] if sg_stack else "")
                        if sg_stack and sg_stack[-1] in subgraphs:
                            subgraphs[sg_stack[-1]].child_nodes.append(nid)
            continue

        # Single edges
        found_edges = list(_FLOW_EDGE_RE.finditer(s))
        if found_edges:
            for em in found_edges:
                src, arrow, label, tgt = em.group(1), em.group(2), em.group(3) or "", em.group(4)
                e = EdgeInfo(
                    index=edge_idx, source=src, target=tgt,
                    arrow_type=arrow, label=label.strip(),
                    semantic_type=_arrow_semantic(arrow, label),
                )
                _apply_linkstyle(e, edge_idx, linkstyle_map, linkstyle_default)
                edges.append(e)
                edge_idx += 1
                # auto-create stub nodes
                for nid in (src, tgt):
                    if nid not in nodes_map and nid not in reserved:
                        nodes_map[nid] = NodeInfo(id=nid, label=nid, subgraph=sg_stack[-1] if sg_stack else "")
                        if sg_stack and sg_stack[-1] in subgraphs:
                            subgraphs[sg_stack[-1]].child_nodes.append(nid)

        # Node definitions — look for ID["..."] / ID(["..."]) / etc. patterns
        _node_opener_re = re.compile(
            r'([A-Za-z_][A-Za-z0-9_]*)\s*'
            r'(\[\("|\(\["|\(\("|\{\{"|\[\[|'
            r'\["|>"|' r'\("|\{"|'
            r'[(\[{>])',
        )
        for nm in _node_opener_re.finditer(s):
            nid = nm.group(1)
            bracket = nm.group(2)
            if nid in reserved:
                continue

            shape = _detect_shape_from_bracket(bracket)
            raw_label = _extract_label(s, nm.start(2), bracket)

            title, body = _split_br_label(raw_label)
            tail = s[nm.start():]
            size_m = _SIZE_TIER_RE.search(tail)
            size_tier = size_m.group(1) if size_m else ""

            icm = _INLINE_CLASS_RE.search(tail)
            inline_cls = icm.group(1) if icm else ""
            if inline_cls and inline_cls.startswith("size-"):
                size_tier = inline_cls.replace("size-", "")
                inline_cls = ""

            node = NodeInfo(
                id=nid, label=raw_label, shape=shape, size_tier=size_tier,
                title_text=title, body_text=body,
                subgraph=sg_stack[-1] if sg_stack else "",
                class_def=inline_cls,
                title_font_size=theme.node_text_font_size,
                body_font_size=theme.node_text_font_size,
                text_color=theme.node_text_color,
                text_align=theme.node_text_align,
            )

            w, h = _estimate_node_size(
                raw_label, shape, size_tier, uniform_w, uniform_h,
                "flowchart", theme,
            )
            node.est_width = w
            node.est_height = h

            if nid not in nodes_map or not nodes_map[nid].label or nodes_map[nid].label == nid:
                nodes_map[nid] = node
                if sg_stack and sg_stack[-1] in subgraphs and nid not in subgraphs[sg_stack[-1]].child_nodes:
                    subgraphs[sg_stack[-1]].child_nodes.append(nid)

    # Apply class assignments & styles
    for nid, cls_name in node_class_map.items():
        if nid in nodes_map and not nodes_map[nid].class_def:
            nodes_map[nid].class_def = cls_name
        elif nid not in nodes_map:
            nodes_map[nid] = NodeInfo(id=nid, class_def=cls_name)

    for nid, node in nodes_map.items():
        if node.class_def and node.class_def in class_defs:
            cd = class_defs[node.class_def]
            node.style = cd.other_props
            if not node.layer:
                node.layer = _resolve_layer_from_style(cd.fill, cd.stroke)
        if nid in node_style_map:
            props = _parse_style_props(node_style_map[nid])
            if not node.layer:
                node.layer = _resolve_layer_from_style(
                    props.get("fill", ""), props.get("stroke", ""),
                )

    # Resolve subgraph styles
    for sg in subgraphs.values():
        if sg.id in node_style_map and not sg.style_fill:
            props = _parse_style_props(node_style_map[sg.id])
            sg.style_fill = props.get("fill", "")
            sg.style_stroke = props.get("stroke", "")
            sg.style_stroke_width = props.get("stroke-width", "")
            sg.resolved_layer = _resolve_layer_from_style(sg.style_fill, sg.style_stroke)

    # Build layers
    used_layers = _build_layers(subgraphs, class_defs)

    rpt.subgraphs = [asdict(sg) for sg in subgraphs.values()]
    rpt.layers = list(used_layers.values())
    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


def _extract_label(line: str, bracket_start: int, bracket: str) -> str:
    """Extract node label text between bracket pair, handling nested quotes."""
    closer_map = {
        '["': '"]', "[[": "]]", '[("': '")]', '(["': '"])',
        '(("': '"))', "((": "))", '{{"': '"}}', "{{": "}}",
        '("': '")', "(": ")", '{"': '"}', "{": "}",
        '>"': '"]', ">": "]", "[": "]",
    }
    closer = closer_map.get(bracket, "]")
    start_pos = bracket_start + len(bracket)
    # Find closer
    idx = line.find(closer, start_pos)
    if idx == -1:
        # Try without quotes
        for c in ("]", ")", "}"):
            idx = line.find(c, start_pos)
            if idx != -1:
                break
    if idx == -1:
        return line[start_pos:].strip().strip('"')
    return line[start_pos:idx].strip().strip('"')


def _apply_linkstyle(
    edge: EdgeInfo, idx: int,
    linkstyle_map: dict[int, str],
    linkstyle_default: str,
) -> None:
    """Apply linkStyle CSS to edge."""
    css = linkstyle_map.get(idx, linkstyle_default)
    if css:
        edge.link_style = css
        props = _parse_style_props(css)
        edge.stroke_color = props.get("stroke", "")
        edge.stroke_width = props.get("stroke-width", "")
        edge.stroke_dasharray = props.get("stroke-dasharray", "")


def _build_layers(
    subgraphs: dict[str, SubgraphInfo],
    class_defs: dict[str, ClassDefInfo],
) -> dict[str, dict]:
    """Build unique layers from subgraphs and classDefs."""
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

    for cd in class_defs.values():
        layer = _resolve_layer_from_style(cd.fill, cd.stroke)
        if layer and layer not in used_layers:
            used_layers[layer] = {
                "name": layer, "fill": cd.fill, "stroke": cd.stroke,
                "class_def": cd.name, "subgraph_ids": [],
            }
        elif layer:
            used_layers[layer]["class_def"] = cd.name

    return used_layers


# ══════════════════════════════════════════════════════════════════════════════
# Class diagram parser
# ══════════════════════════════════════════════════════════════════════════════

def _parse_class_diagram(
    rpt: DiagramReport,
    lines: list[str],
    class_defs: dict[str, ClassDefInfo],
    node_class_map: dict[str, str],
    node_style_map: dict[str, str],
    theme: ThemeParams,
) -> None:
    """Parse classDiagram: classes, relations, styles."""
    nodes_map: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    uniform_w, uniform_h = _parse_uniform(rpt.uniform) if rpt.uniform else (None, None)

    current_class: str | None = None
    current_stereotype = ""
    current_attrs: list[str] = []
    current_methods: list[str] = []

    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        cm = _CD_CLASS_RE.match(s)
        if cm:
            current_class = cm.group(1)
            current_stereotype = ""
            current_attrs = []
            current_methods = []
            continue

        if current_class:
            if s == "}":
                # Build label for size estimation
                full_label_parts = [current_class]
                if current_stereotype:
                    full_label_parts.append(current_stereotype)
                full_label_parts.extend(current_attrs)
                full_label_parts.extend(current_methods)
                est_label = "<br/>".join(full_label_parts)

                w, h = _estimate_node_size(
                    est_label, "class_box", "", uniform_w, uniform_h,
                    "classDiagram", theme,
                )

                node = NodeInfo(
                    id=current_class, label=current_class, shape="class_box",
                    stereotype=current_stereotype,
                    attributes=list(current_attrs), methods=list(current_methods),
                    title_text=current_class,
                    body_text="\n".join(current_attrs + current_methods),
                    est_width=w, est_height=h,
                    title_font_size=theme.class_title_font_size,
                    body_font_size=theme.class_member_font_size,
                    text_color=theme.node_text_color,
                    text_align="left",  # class members are left-aligned
                )
                nodes_map[current_class] = node
                current_class = None
                continue

            if s.startswith("<<") and s.endswith(">>"):
                current_stereotype = s
                continue

            mm = _CD_MEMBER_RE.match(s)
            if mm:
                visibility = mm.group(1)
                member = mm.group(2).strip()
                if "(" in member:
                    current_methods.append(f"{visibility} {member}")
                else:
                    current_attrs.append(f"{visibility} {member}")
                continue
            continue

        rm = _CD_RELATION_RE.match(s)
        if rm:
            src, arrow, tgt = rm.group(1), rm.group(2), rm.group(3)
            label = rm.group(4) or ""
            e = EdgeInfo(
                index=edge_idx, source=src, target=tgt,
                arrow_type=arrow, label=label.strip(),
                semantic_type="inheritance" if "<|" in arrow else "association",
            )
            edges.append(e)
            edge_idx += 1

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

    used_layers: dict[str, dict] = {}
    for nid, css_str in node_style_map.items():
        props = _parse_style_props(css_str)
        layer = _resolve_layer_from_style(props.get("fill", ""), props.get("stroke", ""))
        if layer and layer not in used_layers:
            used_layers[layer] = {
                "name": layer, "fill": props.get("fill", ""),
                "stroke": props.get("stroke", ""),
                "class_def": "", "subgraph_ids": [],
            }

    rpt.layers = list(used_layers.values())
    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


# ══════════════════════════════════════════════════════════════════════════════
# Sequence diagram parser
# ══════════════════════════════════════════════════════════════════════════════

def _parse_sequence_diagram(
    rpt: DiagramReport,
    lines: list[str],
    theme: ThemeParams,
) -> None:
    """Parse sequenceDiagram: participants, messages."""
    nodes_map: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        pm = _SEQ_PARTICIPANT_RE.match(s)
        if pm:
            pid = pm.group(1)
            alias = pm.group(2) or pid
            nodes_map[pid] = NodeInfo(
                id=pid, label=alias, shape="actor",
                est_width=theme.seq_actor_width,
                est_height=theme.seq_actor_height,
                title_font_size=theme.global_font_size,
                body_font_size=theme.seq_message_font_size,
                text_color=theme.seq_actor_text_color,
                text_align=theme.seq_message_align,
            )
            continue

        mm = _SEQ_MESSAGE_RE.match(s)
        if mm:
            src, arrow, tgt, msg = mm.group(1), mm.group(2), mm.group(3), mm.group(4).strip()
            e = EdgeInfo(
                index=edge_idx, source=src, target=tgt,
                arrow_type=arrow, label=msg,
                semantic_type="sync_call" if ">>" in arrow else "async_call",
            )
            edges.append(e)
            edge_idx += 1
            for p in (src, tgt):
                if p not in nodes_map:
                    nodes_map[p] = NodeInfo(
                        id=p, label=p, shape="actor",
                        est_width=theme.seq_actor_width,
                        est_height=theme.seq_actor_height,
                        title_font_size=theme.global_font_size,
                        body_font_size=theme.seq_message_font_size,
                        text_color=theme.seq_actor_text_color,
                        text_align=theme.seq_message_align,
                    )

    rpt.nodes = [asdict(n) for n in nodes_map.values()]
    rpt.edges = [asdict(e) for e in edges]


# ══════════════════════════════════════════════════════════════════════════════
# State diagram parser (NEW — fixes 0-node bug)
# ══════════════════════════════════════════════════════════════════════════════

def _parse_state_diagram(
    rpt: DiagramReport,
    lines: list[str],
    theme: ThemeParams,
) -> None:
    """Parse stateDiagram-v2: states, transitions."""
    states: dict[str, NodeInfo] = {}
    edges: list[EdgeInfo] = []
    edge_idx = 0

    for line in lines:
        s = line.strip()
        if s.startswith("%%") or not s:
            continue

        # State declaration: state NAME {
        sm = _STATE_DECL_RE.match(s)
        if sm:
            sid = sm.group(1)
            if sid not in states and sid not in ("[*]",):
                states[sid] = NodeInfo(
                    id=sid, label=sid, shape="state",
                    title_font_size=theme.global_font_size,
                    body_font_size=theme.global_font_size,
                    text_color=theme.node_text_color,
                    text_align="center",
                )
            continue

        # State label: NAME : description
        lm = _STATE_LABEL_RE.match(s)
        if lm:
            sid = lm.group(1)
            desc = lm.group(2).strip()
            if sid == "[*]" or sid in ("state", "end"):
                continue
            if sid not in states:
                states[sid] = NodeInfo(
                    id=sid, label=desc, shape="state",
                    title_text=sid, body_text=desc,
                    title_font_size=theme.global_font_size,
                    body_font_size=theme.global_font_size,
                    text_color=theme.node_text_color,
                    text_align="center",
                )
            else:
                states[sid].body_text = (states[sid].body_text + "\n" + desc).strip()
                states[sid].label = desc
            continue

        # Transition: NAME --> NAME : label
        tm = _STATE_TRANS_RE.match(s)
        if tm:
            src, tgt = tm.group(1), tm.group(3)
            label = tm.group(4) or ""
            # Auto-create states from transitions
            for sid in (src, tgt):
                if sid not in states and sid != "[*]":
                    states[sid] = NodeInfo(
                        id=sid, label=sid, shape="state",
                        title_font_size=theme.global_font_size,
                        body_font_size=theme.global_font_size,
                        text_color=theme.node_text_color,
                        text_align="center",
                    )

            e = EdgeInfo(
                index=edge_idx, source=src, target=tgt,
                arrow_type="-->", label=label.strip(),
                semantic_type="transition",
            )
            edges.append(e)
            edge_idx += 1

    # Estimate sizes
    for node in states.values():
        w, h = _estimate_node_size(
            node.label, "state", "", None, None, "stateDiagram", theme,
        )
        node.est_width = w
        node.est_height = h

    rpt.nodes = [asdict(n) for n in states.values()]
    rpt.edges = [asdict(e) for e in edges]


# ══════════════════════════════════════════════════════════════════════════════
# Main parser
# ══════════════════════════════════════════════════════════════════════════════

def parse_diagram(path: Path, theme: ThemeParams) -> DiagramReport:
    """Parse a single Mermaid file and extract all parameters."""
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    rpt = DiagramReport()

    # ── Group 1: File info ────────────────────────────────────────────────
    rpt.file_path = str(path.relative_to(ROOT))
    rpt.file_name = path.name
    rpt.format = path.suffix
    rpt.directory = str(path.parent.relative_to(ROOT))
    rel = path.relative_to(DIAGRAM_BASE) if str(path).startswith(str(DIAGRAM_BASE)) else path
    rpt.catalog = rel.parts[0] if rel.parts else ""

    # ── Group 2: Metadata ─────────────────────────────────────────────────
    for line in lines:
        m = _TITLE_RE.match(line.strip())
        if m:
            rpt.title = m.group(1).strip()
            break
        m2 = _TITLE_ALT_RE.match(line.strip())
        if m2:
            rpt.title = m2.group(1).strip()
            break

    covers_lines: list[str] = []
    seen_title = False
    for line in lines:
        s = line.strip()
        if not s.startswith("%%"):
            break
        if s.startswith("%% @") or s.startswith("%%{"):
            continue
        if _TITLE_RE.match(s) or _TITLE_ALT_RE.match(s):
            seen_title = True
            continue
        if seen_title and _COVERS_RE.match(s):
            covers_lines.append(_COVERS_RE.match(s).group(1).strip())
            seen_title = False
    rpt.covers = " ".join(covers_lines) if covers_lines else ""
    rpt.idea = rpt.title or rpt.covers

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

    for line in lines:
        s = line.strip()
        if s.startswith("%%"):
            continue
        m = _GRAPH_DIR_RE.match(s)
        if m:
            rpt.direction = m.group(1).upper()
            break

    # Detect diagram type if not from @type metadata
    if not rpt.diagram_type:
        rpt.diagram_type = _detect_diagram_type(lines)

    # Direction from classDiagram/stateDiagram
    if not rpt.direction:
        for line in lines:
            dm = _DIRECTION_RE.match(line)
            if dm:
                rpt.direction = dm.group(1).upper()
                break

    # ── Parse global declarations ─────────────────────────────────────────
    class_defs: dict[str, ClassDefInfo] = {}
    for line in lines:
        m = _CLASSDEF_RE.match(line)
        if m:
            name = m.group(1)
            props = _parse_style_props(m.group(2))
            class_defs[name] = ClassDefInfo(
                name=name, fill=props.get("fill", ""),
                stroke=props.get("stroke", ""),
                stroke_width=props.get("stroke-width", ""),
                other_props=m.group(2),
            )

    node_class_map: dict[str, str] = {}
    for line in lines:
        m = _CLASS_ASSIGN_RE.match(line)
        if m:
            ids = [x.strip() for x in m.group(1).split(",")]
            cls_name = m.group(2)
            for nid in ids:
                if nid:
                    node_class_map[nid] = cls_name

    node_style_map: dict[str, str] = {}
    for line in lines:
        m = _STYLE_DIRECT_RE.match(line)
        if m:
            node_style_map[m.group(1)] = m.group(2)

    linkstyle_map: dict[int, str] = {}
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
    dtype = rpt.diagram_type

    if dtype == "classDiagram":
        _parse_class_diagram(rpt, lines, class_defs, node_class_map, node_style_map, theme)
    elif dtype == "sequenceDiagram":
        _parse_sequence_diagram(rpt, lines, theme)
    elif dtype == "stateDiagram":
        _parse_state_diagram(rpt, lines, theme)
    else:
        _parse_flowchart(
            rpt, lines, class_defs, node_class_map,
            node_style_map, linkstyle_map, linkstyle_default, theme,
        )

    # ── Resolve edge display properties (edge_type, line_style, arrows) ──
    for e_dict in rpt.edges:
        tmp = EdgeInfo(
            index=e_dict["index"], source=e_dict["source"], target=e_dict["target"],
            arrow_type=e_dict.get("arrow_type", ""),
            stroke_dasharray=e_dict.get("stroke_dasharray", ""),
        )
        _resolve_edge_display(tmp)
        e_dict["edge_type"] = tmp.edge_type
        e_dict["line_style"] = tmp.line_style
        e_dict["arrow_start"] = tmp.arrow_start
        e_dict["arrow_end"] = tmp.arrow_end

    # ── Estimate sizes for stub nodes (created from edge references) ─────
    uniform_w, uniform_h = _parse_uniform(rpt.uniform) if rpt.uniform else (None, None)
    for n_dict in rpt.nodes:
        if not n_dict.get("est_width") and not n_dict.get("est_height"):
            label = n_dict.get("label", n_dict.get("id", ""))
            w, h = _estimate_node_size(
                label, n_dict.get("shape", "rect"), n_dict.get("size_tier", ""),
                uniform_w, uniform_h, dtype, theme,
            )
            n_dict["est_width"] = w
            n_dict["est_height"] = h
            if not n_dict.get("title_font_size"):
                if dtype == "classDiagram":
                    n_dict["title_font_size"] = theme.class_title_font_size
                    n_dict["body_font_size"] = theme.class_member_font_size
                elif dtype == "sequenceDiagram":
                    n_dict["title_font_size"] = theme.global_font_size
                    n_dict["body_font_size"] = theme.seq_message_font_size
                else:
                    n_dict["title_font_size"] = theme.node_text_font_size
                    n_dict["body_font_size"] = theme.node_text_font_size
            if not n_dict.get("text_color"):
                n_dict["text_color"] = theme.node_text_color
            if not n_dict.get("text_align"):
                n_dict["text_align"] = "left" if dtype == "classDiagram" else theme.node_text_align

    # ── Resolve subgraph node_count and class_def ────────────────────────
    for sg_dict in rpt.subgraphs:
        sg_dict["node_count"] = len(sg_dict.get("child_nodes", []))
        # Resolve class_def from style maps
        sg_id = sg_dict.get("id", "")
        if not sg_dict.get("class_def") and sg_id in node_class_map:
            sg_dict["class_def"] = node_class_map[sg_id]
        # Populate style if empty but have resolved_layer
        if not sg_dict.get("style") and (sg_dict.get("style_fill") or sg_dict.get("style_stroke")):
            parts = []
            if sg_dict.get("style_fill"):
                parts.append(f"fill:{sg_dict['style_fill']}")
            if sg_dict.get("style_stroke"):
                parts.append(f"stroke:{sg_dict['style_stroke']}")
            if sg_dict.get("style_stroke_width"):
                parts.append(f"stroke-width:{sg_dict['style_stroke_width']}")
            sg_dict["style"] = ",".join(parts)

    # ── Group 3: Statistics ───────────────────────────────────────────────
    rpt.nodes_actual = len(rpt.nodes)
    rpt.edges_count = len(rpt.edges)
    edge_types = {e.get("semantic_type", "") for e in rpt.edges}
    rpt.edge_types_count = len(edge_types - {""})
    rpt.subgraphs_count = len(rpt.subgraphs)

    # ── Group 10: Quality metrics ─────────────────────────────────────────
    if rpt.nodes_actual > 0:
        rpt.edges_nodes_ratio = round(rpt.edges_count / rpt.nodes_actual, 2)

    conn_count: dict[str, int] = {}
    for e in rpt.edges:
        conn_count[e["source"]] = conn_count.get(e["source"], 0) + 1
        conn_count[e["target"]] = conn_count.get(e["target"], 0) + 1
    rpt.hub_nodes = [
        {"id": nid, "connections": cnt}
        for nid, cnt in sorted(conn_count.items(), key=lambda x: -x[1])
        if cnt >= 6
    ]

    connected = set()
    for e in rpt.edges:
        connected.add(e["source"])
        connected.add(e["target"])
    all_ids = {n["id"] for n in rpt.nodes}
    rpt.orphan_nodes = sorted(all_ids - connected)
    rpt.max_subgraph_depth = max(
        (s.get("depth", 0) for s in rpt.subgraphs), default=0,
    )
    rpt.class_defs = [asdict(cd) for cd in class_defs.values()]

    ls_list: list[dict] = []
    for idx, css in sorted(linkstyle_map.items()):
        props = _parse_style_props(css)
        ls_list.append({
            "edge_index": idx, "css": css,
            "stroke": props.get("stroke", ""),
            "stroke_width": props.get("stroke-width", ""),
            "stroke_dasharray": props.get("stroke-dasharray", ""),
        })
    if linkstyle_default:
        ls_list.insert(0, {"edge_index": "default", "css": linkstyle_default})
    rpt.link_styles = ls_list

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
            "font_size": theme.edge_label_font_size,
            "font_color": theme.edge_label_font_color,
        }
        for e in rpt.edges
        if e.get("label")
    ]

    # ── Theme snapshot ────────────────────────────────────────────────────
    rpt.theme = {
        "global_font_size": theme.global_font_size,
        "node_text_font_size": theme.node_text_font_size,
        "node_text_color": theme.node_text_color,
        "node_text_align": theme.node_text_align,
        "class_title_font_size": theme.class_title_font_size,
        "class_stereotype_font_size": theme.class_stereotype_font_size,
        "class_member_font_size": theme.class_member_font_size,
        "cluster_font_size": theme.cluster_font_size,
        "cluster_font_weight": theme.cluster_font_weight,
        "edge_label_font_size": theme.edge_label_font_size,
        "edge_label_font_color": theme.edge_label_font_color,
        "edge_label_bg_color": theme.edge_label_bg_color,
        "seq_message_font_size": theme.seq_message_font_size,
        "seq_message_align": theme.seq_message_align,
        "flowchart_padding": theme.flowchart_padding,
        "flowchart_node_spacing": theme.flowchart_node_spacing,
        "flowchart_rank_spacing": theme.flowchart_rank_spacing,
        "flowchart_wrapping_width": theme.flowchart_wrapping_width,
    }

    return rpt


# ══════════════════════════════════════════════════════════════════════════════
# File discovery
# ══════════════════════════════════════════════════════════════════════════════

def find_diagrams(targets: list[Path]) -> list[Path]:
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
                    if f not in seen and not f.name.startswith("_") and not EXCLUDED_PARTS.intersection(f.parts):
                        seen.add(f)
                        files.append(f)
    return sorted(files)


# ══════════════════════════════════════════════════════════════════════════════
# Output formatters
# ══════════════════════════════════════════════════════════════════════════════

def _to_json(reports: list[DiagramReport]) -> str:
    return json.dumps(
        {"total_diagrams": len(reports), "diagrams": [asdict(r) for r in reports]},
        indent=2, ensure_ascii=False,
    )


def _to_markdown(reports: list[DiagramReport]) -> str:
    lines: list[str] = []
    lines.append("# Diagram Parameters Inventory")
    lines.append(f"\nTotal diagrams: **{len(reports)}**\n")

    # Summary table
    lines.append("## Summary Table\n")
    lines.append("| # | File | Type | Nodes | Edges | E/N | Engine | Dir | Layers | SG |")
    lines.append("|---|------|------|-------|-------|-----|--------|-----|--------|----|")
    for i, r in enumerate(reports, 1):
        lines.append(
            f"| {i} | `{r.file_name}` | {r.diagram_type} | "
            f"{r.nodes_actual} | {r.edges_count} | {r.edges_nodes_ratio} | "
            f"{r.layout_engine} | {r.direction} | {len(r.layers)} | {r.subgraphs_count} |"
        )

    for i, r in enumerate(reports, 1):
        lines.append(f"\n---\n## {i}. {r.file_name}\n")

        lines.append("### 1. File Info\n")
        lines.append(f"- **Path**: `{r.file_path}`")
        lines.append(f"- **Format**: `{r.format}` | **Catalog**: `{r.catalog}`")
        lines.append(f"- **Idea**: {r.idea}")

        lines.append("\n### 2. Metadata\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        for k, v in [("Title", r.title), ("Covers", r.covers), ("@version", r.version),
                      ("@date", r.date), ("@type", r.diagram_type), ("@level", r.level),
                      ("@nodes", r.nodes_declared), ("@adr", r.adr)]:
            if v:
                lines.append(f"| {k} | {v} |")
        if r.view:
            lines.append(f"| View | {r.view} |")

        lines.append("\n### 3. Statistics\n")
        lines.append(f"Nodes: **{r.nodes_actual}** | Edges: **{r.edges_count}** | "
                     f"Types: **{r.edge_types_count}** | Subgraphs: **{r.subgraphs_count}**")

        lines.append("\n### 4. Layout\n")
        lines.append(f"Direction: `{r.direction}` | Engine: `{r.layout_engine}` | "
                     f"Edge routing: `{r.edge_routing}`")

        if r.layers:
            lines.append("\n### 5. Layers\n")
            lines.append("| Layer | Fill | Stroke | classDef |")
            lines.append("|-------|------|--------|----------|")
            for l in r.layers:
                lines.append(f"| {l['name']} | `{l['fill']}` | `{l['stroke']}` | `{l.get('class_def', '')}` |")

        if r.subgraphs:
            lines.append("\n### 6. Subgraphs\n")
            lines.append("| ID | Label | Parent | Depth | Layer | Nodes | Style | classDef |")
            lines.append("|----|-------|--------|-------|-------|-------|-------|----------|")
            for sg in r.subgraphs:
                lines.append(
                    f"| `{sg['id']}` | {sg['label']} | `{sg['parent']}` | "
                    f"{sg['depth']} | {sg['resolved_layer']} | {sg.get('node_count', len(sg.get('child_nodes', [])))} | "
                    f"`{sg.get('style', '')}` | `{sg.get('class_def', '')}` |"
                )

        if r.nodes:
            lines.append("\n### 7. Nodes\n")
            lines.append("| ID | Title | Shape | Layer | SG | classDef | W×H | TitleFont | BodyFont | Color | Align | Conn |")
            lines.append("|----|-------|-------|-------|----|----------|-----|-----------|----------|-------|-------|------|")
            for n in r.nodes:
                title = (n.get("title_text") or n.get("label", ""))[:25]
                lines.append(
                    f"| `{n['id']}` | {title} | {n['shape']} | "
                    f"{n['layer']} | `{n['subgraph']}` | `{n['class_def']}` | "
                    f"{n['est_width']}×{n['est_height']} | "
                    f"{n['title_font_size']}px | {n['body_font_size']}px | "
                    f"`{n['text_color']}` | {n['text_align']} | {n['connection_count']} |"
                )

        if r.edges:
            lines.append("\n### 8. Edges\n")
            lines.append("| # | Source→Target | Arrow | EdgeType | LineStyle | ArrowStart | ArrowEnd | Semantic | Label | Stroke | Width | Dash |")
            lines.append("|---|-------------|-------|----------|-----------|------------|----------|----------|-------|--------|-------|------|")
            for e in r.edges:
                lines.append(
                    f"| {e['index']} | `{e['source']}`→`{e['target']}` | "
                    f"`{e['arrow_type']}` | {e.get('edge_type', '')} | {e.get('line_style', '')} | "
                    f"{e.get('arrow_start', '')} | {e.get('arrow_end', '')} | {e['semantic_type']} | "
                    f"{e['label']} | `{e['stroke_color']}` | "
                    f"`{e['stroke_width']}` | `{e['stroke_dasharray']}` |"
                )

        if r.edge_labels:
            lines.append("\n### 9. Edge Labels\n")
            lines.append("| Edge | Label | Len | Font | Color |")
            lines.append("|------|-------|-----|------|-------|")
            for el in r.edge_labels:
                lines.append(
                    f"| {el['edge_index']} | {el['label']} | {el['label_length']} | "
                    f"{el['font_size']}px | `{el['font_color']}` |"
                )

        lines.append("\n### 10. Quality Metrics\n")
        lines.append(f"- **E/N ratio**: {r.edges_nodes_ratio}")
        if r.hub_nodes:
            hubs = ", ".join(f"`{h['id']}` ({h['connections']})" for h in r.hub_nodes)
            lines.append(f"- **Hub nodes**: {hubs}")
        if r.orphan_nodes:
            lines.append(f"- **Orphans**: {', '.join(f'`{o}`' for o in r.orphan_nodes)}")
        lines.append(f"- **Max depth**: {r.max_subgraph_depth}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# Main
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract comprehensive parameters from Mermaid diagrams.",
    )
    parser.add_argument("paths", nargs="*", help="Files/directories (default: all diagrams).")
    parser.add_argument("--out", help="Output file (default: stdout).")
    parser.add_argument("--markdown", action="store_true")
    parser.add_argument("--json", action="store_true", dest="json_out")

    args = parser.parse_args()
    targets = [Path(p) for p in args.paths] if args.paths else [DIAGRAM_BASE]
    diagrams = find_diagrams(targets)

    if not diagrams:
        print("No diagram files found.", file=sys.stderr)
        return 1

    theme = ThemeParams.load_from_project()
    reports: list[DiagramReport] = []
    for path in diagrams:
        try:
            reports.append(parse_diagram(path, theme))
        except Exception as exc:
            print(f"ERROR parsing {path}: {exc}", file=sys.stderr)

    output = _to_markdown(reports) if args.markdown else _to_json(reports)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Written {len(reports)} diagram reports to {args.out}", file=sys.stderr)
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
