"""Post-render SVG harmonization of link styles across diagram types.

Applies the canonical BioETL semantic link palette to rendered SVG files,
colouring edges by their semantic role. This bridges the gap between
flowchart (which supports inline linkStyle) and other diagram types
(sequence, class, state, ER) that lack native per-edge styling.

Works as a post-processing step after mmdc renders SVG.

Usage:
    python scripts/diagrams/harmonize_link_styles.py [--dry-run] [--dir DIR]
    python -m scripts.diagrams harmonize-link-styles --dry-run

ADR-040 D9: Cross-Diagram Link Harmonization.
"""

from __future__ import annotations

import argparse
import re
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import TypedDict
from urllib.parse import urlunsplit
from xml.etree import ElementTree as ET

if isinstance(sys.stdout, TextIOWrapper):
    sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parents[2]

# ── Canonical semantic palette ────────────────────────────────────────────────

class PaletteStyle(TypedDict):
    """One canonical SVG stroke style."""

    stroke: str
    width: str
    dash: str | None


PALETTE: dict[str, PaletteStyle] = {
    "data": {"stroke": "#1E293B", "width": "2", "dash": None},
    "orchestration": {"stroke": "#2e7d32", "width": "2", "dash": None},
    "di": {"stroke": "#6a1b9a", "width": "1.5", "dash": "5"},
    "observability": {"stroke": "#94A3B8", "width": "1", "dash": None},
    "error": {"stroke": "#c62828", "width": "2", "dash": "4 3"},
    "baseline": {"stroke": "#475569", "width": "2", "dash": None},
}

# SVG namespace
SVG_NS = urlunsplit(("http", "www.w3.org", "/2000/svg", "", ""))
NS = {"svg": SVG_NS}

# ── Diagram type detection ────────────────────────────────────────────────────


def detect_diagram_type(svg_root: ET.Element) -> str | None:
    """Detect Mermaid diagram type from SVG class attributes."""
    svg_text = ET.tostring(svg_root, encoding="unicode")

    if "sequenceDiagram" in svg_text or "messageLine" in svg_text:
        return "sequence"
    if "statediagram" in svg_text or "stateGroup" in svg_text:
        return "state"
    if "classGroup" in svg_text or "classDiagram" in svg_text:
        return "class"
    if "er " in svg_text or "entityBox" in svg_text:
        return "er"
    if "flowchart" in svg_text or "edgePath" in svg_text:
        return "flowchart"
    return None


# ── Style application per diagram type ────────────────────────────────────────


def _set_style(elem: ET.Element, palette_key: str) -> None:
    """Apply palette style to an SVG element."""
    style = PALETTE[palette_key]
    elem.set("stroke", style["stroke"])
    elem.set("stroke-width", style["width"])
    dash = style["dash"]
    if dash:
        elem.set("stroke-dasharray", dash)
    else:
        # Remove dasharray if present — force solid
        if "stroke-dasharray" in elem.attrib:
            existing = elem.get("stroke-dasharray", "")
            # Preserve intentional dashes from Mermaid (e.g., -- dashed arrows)
            if existing and existing != "none":
                pass  # keep Mermaid's own dashing
            else:
                del elem.attrib["stroke-dasharray"]


def harmonize_sequence(root: ET.Element) -> int:
    """Harmonize sequenceDiagram link colours."""
    changes = 0

    # messageLine0 = sync calls (solid) → baseline
    for elem in root.iter():
        cls = elem.get("class", "")
        if "messageLine0" in cls:
            _set_style(elem, "baseline")
            changes += 1
        elif "messageLine1" in cls:
            _set_style(elem, "observability")
            changes += 1

    return changes


def _svg_tag_name(elem: ET.Element) -> str:
    """Return local SVG tag name without namespace."""
    return elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag


def _style_class_relation(elem: ET.Element) -> bool:
    """Apply palette styling to a class-diagram relation line."""
    cls = elem.get("class", "")
    if "relation" not in cls or _svg_tag_name(elem) not in ("path", "line"):
        return False
    style_attr = elem.get("style", "")
    if "stroke-dasharray" in (elem.get("stroke-dasharray", "") + style_attr):
        _set_style(elem, "di")
    else:
        _set_style(elem, "baseline")
    return True


def _style_extension_group(elem: ET.Element) -> int:
    """Color inheritance markers embedded inside extension groups."""
    if "extension" not in elem.get("class", "").lower():
        return 0
    changes = 0
    for child in elem.iter():
        if _svg_tag_name(child) != "path":
            continue
        child.set("fill", PALETTE["di"]["stroke"])
        child.set("stroke", PALETTE["di"]["stroke"])
        changes += 1
    return changes


def _style_marker_path(marker_id: str, path: ET.Element) -> bool:
    """Apply marker-specific arrowhead styling for class diagrams."""
    if "extension" in marker_id.lower():
        path.set("fill", PALETTE["di"]["stroke"])
        path.set("stroke", PALETTE["di"]["stroke"])
        return True
    if "composition" in marker_id.lower():
        path.set("fill", PALETTE["baseline"]["stroke"])
        path.set("stroke", PALETTE["baseline"]["stroke"])
        return True
    if "aggregation" in marker_id.lower():
        path.set("fill", "white")
        path.set("stroke", PALETTE["baseline"]["stroke"])
        return True
    return False


def harmonize_class(root: ET.Element) -> int:
    """Harmonize classDiagram relation colours."""
    changes = 0

    for elem in root.iter():
        if _style_class_relation(elem):
            changes += 1
        changes += _style_extension_group(elem)

    # Marker elements (arrowheads)
    for marker in root.iter():
        if _svg_tag_name(marker) != "marker":
            continue
        marker_id = marker.get("id", "")
        for path in marker.iter():
            if _svg_tag_name(path) != "path":
                continue
            if _style_marker_path(marker_id, path):
                changes += 1

    return changes


def harmonize_state(root: ET.Element) -> int:
    """Harmonize stateDiagram transition colours."""
    changes = 0

    for elem in root.iter():
        cls = elem.get("class", "")
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if "transition" in cls and tag == "path":
            _set_style(elem, "orchestration")
            changes += 1

    return changes


def harmonize_er(root: ET.Element) -> int:
    """Harmonize erDiagram relationship colours."""
    changes = 0

    for elem in root.iter():
        cls = elem.get("class", "")
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if "relationshipLine" in cls and tag in ("path", "line"):
            dash = elem.get("stroke-dasharray", "")
            if dash and dash != "none" and dash != "0":
                _set_style(elem, "di")
            else:
                _set_style(elem, "data")
            changes += 1

    return changes


# ── Dispatcher ────────────────────────────────────────────────────────────────

HARMONIZERS = {
    "sequence": harmonize_sequence,
    "class": harmonize_class,
    "state": harmonize_state,
    "er": harmonize_er,
}


def process_svg(fpath: Path, dry_run: bool) -> tuple[bool, str]:
    """Process one SVG file. Returns (modified, reason)."""
    try:
        ET.register_namespace("", SVG_NS)
        tree = ET.parse(fpath)
    except ET.ParseError as e:
        return False, f"XML parse error: {e}"

    root = tree.getroot()
    dtype = detect_diagram_type(root)

    if dtype is None:
        return False, "unknown diagram type"

    if dtype == "flowchart":
        return False, "flowchart (uses inline linkStyle)"

    harmonizer = HARMONIZERS.get(dtype)
    if harmonizer is None:
        return False, f"no harmonizer for {dtype}"

    changes = harmonizer(root)
    if changes == 0:
        return False, f"{dtype}: no matching elements"

    if not dry_run:
        tree.write(fpath, encoding="unicode", xml_declaration=True)

    return True, f"{dtype}: {changes} elements harmonized"


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harmonize link styles in rendered SVG diagrams (ADR-040 D9)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print plan without modifying files",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        action="append",
        dest="dirs",
        help="SVG directory to process (repeatable; default: all svg/ dirs under docs)",
    )
    parser.add_argument(
        "--fail-on-errors",
        action="store_true",
        help="Exit with code 1 if any SVG processing errors are detected",
    )
    args = parser.parse_args()

    # Collect SVG directories
    if args.dirs:
        svg_dirs = [d for d in args.dirs if d.is_dir()]
    else:
        svg_dirs = sorted(REPO_ROOT.glob("docs/**/svg"))

    if not svg_dirs:
        print("No SVG directories found.")
        return 0

    svg_files: list[Path] = []
    for d in svg_dirs:
        svg_files.extend(sorted(d.glob("*.svg")))

    print("=" * 65)
    print(
        f"LINK HARMONIZATION {'(DRY RUN) ' if args.dry_run else ''}| "
        f"files={len(svg_files)} | dirs={len(svg_dirs)}"
    )
    print("=" * 65)

    modified = skipped = errors = 0

    for f in svg_files:
        ok, reason = process_svg(f, args.dry_run)
        if ok:
            modified += 1
            print(f"  [OK]   {f.name}  ({reason})")
        elif "error" in reason.lower():
            errors += 1
            print(f"  [ERR]  {f.name}  ({reason})")
        else:
            skipped += 1

    print(f"\n{'=' * 65}")
    print(f"Modified:  {modified}")
    print(f"Skipped:   {skipped}")
    print(f"Errors:    {errors}")
    if args.fail_on_errors and errors > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
