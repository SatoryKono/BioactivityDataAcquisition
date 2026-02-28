#!/usr/bin/env python3
"""
Add plain SVG <text> fallbacks for Mermaid <foreignObject> labels.

Why:
  Some SVG/PNG renderers ignore foreignObject (HTML labels), which makes
  node and edge text invisible. This script keeps foreignObject in place and
  adds a fallback <text> element underneath it.

Behavior:
  - Does not remove/alter foreignObject (safe for layout and arrows)
  - Skips empty/zero-size labels
  - Idempotent per file (avoids duplicate fallback text)
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

SVG_DIRS = [
    Path("docs/02-architecture/mmd-diagrams/architecture/svg"),
    Path("docs/02-architecture/mmd-diagrams/class-diagrams/svg"),
    Path("docs/02-architecture/mmd-diagrams/foundation/svg"),
    Path("docs/02-architecture/mmd-diagrams/views/svg"),
]


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _parse_float(raw: str | None, default: float = 0.0) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _fmt_float(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".") or "0"


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_text(node: ET.Element) -> str:
    return _normalize_text(" ".join(node.itertext()))


def _is_empty_edge_label_group(node: ET.Element) -> bool:
    """Detect Mermaid-generated empty edgeLabel containers.

    Some Mermaid outputs include <g class="edgeLabel"> wrappers with a zero-sized
    foreignObject and no text content. These render as white rectangles in certain
    viewers and should be removed.
    """
    if _local_name(node.tag) != "g":
        return False
    classes = node.attrib.get("class", "")
    if "edgeLabel" not in classes.split():
        return False
    if _extract_text(node):
        return False

    # Keep group if any foreignObject is non-zero (potentially meaningful label).
    for child in node.iter():
        if _local_name(child.tag) != "foreignObject":
            continue
        width = _parse_float(child.attrib.get("width"))
        height = _parse_float(child.attrib.get("height"))
        if width > 0.0 or height > 0.0:
            return False
    return True


def _is_fallback_text(node: ET.Element) -> bool:
    if _local_name(node.tag) != "text":
        return False
    classes = node.attrib.get("class", "")
    return "fo-fallback" in classes.split()


def _build_fallback_text(fo: ET.Element) -> ET.Element | None:
    text_value = _extract_text(fo)
    if not text_value:
        return None

    width = _parse_float(fo.attrib.get("width"))
    height = _parse_float(fo.attrib.get("height"))
    if width <= 0.0 and height <= 0.0:
        return None

    x = _parse_float(fo.attrib.get("x"))
    y = _parse_float(fo.attrib.get("y"))

    text_elem = ET.Element(f"{{{SVG_NS}}}text")
    text_elem.set("x", _fmt_float(x + width / 2.0))
    text_elem.set("y", _fmt_float(y + height / 2.0))
    text_elem.set("text-anchor", "middle")
    text_elem.set("dominant-baseline", "middle")
    text_elem.set("xml:space", "preserve")

    cls = fo.attrib.get("class", "").strip()
    text_elem.set("class", f"{cls} fo-fallback".strip())

    transform = fo.attrib.get("transform")
    if transform:
        text_elem.set("transform", transform)

    text_elem.text = text_value
    return text_elem


def _process_tree(tree: ET.ElementTree) -> int:
    """Modify tree in-memory: add fallbacks and remove empty edge labels. Returns change count."""
    root = tree.getroot()

    inserted = 0
    removed_empty_edge_labels = 0
    for parent in root.iter():
        children = list(parent)
        for child in children:
            if not _is_empty_edge_label_group(child):
                continue
            parent.remove(child)
            removed_empty_edge_labels += 1

    for parent in root.iter():
        children = list(parent)
        for idx, child in enumerate(children):
            if _local_name(child.tag) != "foreignObject":
                continue

            if idx > 0 and _is_fallback_text(children[idx - 1]):
                continue

            fallback = _build_fallback_text(child)
            if fallback is None:
                continue

            parent.insert(idx, fallback)
            inserted += 1

    return inserted + removed_empty_edge_labels


def add_fallbacks(path: Path, *, write: bool = True) -> int:
    """Add fallback text to an SVG file. Only writes to disk when write=True."""
    tree = ET.parse(path)
    changes = _process_tree(tree)
    if changes > 0 and write:
        tree.write(path, encoding="utf-8", xml_declaration=False)
    return changes


def collect_svg_files(files: list[Path] | None, dirs: list[Path] | None) -> list[Path]:
    if files:
        return files
    if dirs:
        result: list[Path] = []
        for d in dirs:
            if d.is_dir():
                result.extend(sorted(d.glob("*.svg")))
        return result
    result: list[Path] = []
    for d in SVG_DIRS:
        if d.is_dir():
            result.extend(sorted(d.glob("*.svg")))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add fallback SVG text for Mermaid foreignObject labels.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Exit 1 if fallback insertion needed")
    group.add_argument("--fix", action="store_true", help="Write changes in place")
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument("-f", "--file", type=Path, action="append", help="Specific SVG file(s)")
    parser.add_argument("--dir", type=Path, action="append", help="Specific directory(ies)")
    args = parser.parse_args()

    mode = "check" if args.check else ("dry-run" if args.dry_run else "fix")
    files = collect_svg_files(args.file, args.dir)
    if not files:
        print("No SVG files found.")
        return 0

    changed = 0
    for path in files:
        if mode == "fix":
            inserted = add_fallbacks(path, write=True)
        else:
            inserted = add_fallbacks(path, write=False)
        if inserted == 0:
            continue
        changed += 1
        if mode == "check":
            print(f"! {path} (needs fallback text, +{inserted})")
        elif mode == "dry-run":
            print(f"~ {path} (would add fallback text +{inserted})")
        else:
            print(f"+ {path} (added fallback text +{inserted})")

    if mode == "check" and changed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
