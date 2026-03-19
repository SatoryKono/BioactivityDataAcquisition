#!/usr/bin/env python3
"""Strip Mermaid foreignObject labels from rendered SVG files.

Use-case:
  In fallback-only mode we keep plain SVG <text class="fo-fallback"> labels
  and remove HTML-based foreignObject labels to avoid duplicate text rendering
  in viewers that support both layers.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from .diagram_paths import SOURCE_FAMILIES, render_dir
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import SOURCE_FAMILIES, render_dir

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

SVG_DIRS = [
    render_dir(family, "svg")
    for family in SOURCE_FAMILIES
]


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def strip_foreign_objects(path: Path) -> int:
    tree = ET.parse(path)
    root = tree.getroot()
    removed = 0

    for parent in root.iter():
        for child in list(parent):
            if _local_name(child.tag) != "foreignObject":
                continue
            parent.remove(child)
            removed += 1

    if removed > 0:
        tree.write(path, encoding="utf-8", xml_declaration=False)
    return removed


def collect_svg_files(files: list[Path] | None, dirs: list[Path] | None) -> list[Path]:
    if files:
        return files
    if dirs:
        selected: list[Path] = []
        for d in dirs:
            if d.is_dir():
                selected.extend(sorted(d.glob("*.svg")))
        return selected
    result: list[Path] = []
    for d in SVG_DIRS:
        if d.is_dir():
            result.extend(sorted(d.glob("*.svg")))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Remove foreignObject elements from Mermaid SVG files.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="Exit 1 if stripping is needed")
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
        original = path.read_text(encoding="utf-8")
        removed = strip_foreign_objects(path)
        if removed == 0:
            continue
        changed += 1
        if mode == "check":
            print(f"! {path} (needs foreignObject strip, -{removed})")
            path.write_text(original, encoding="utf-8")
        elif mode == "dry-run":
            print(f"~ {path} (would remove foreignObject -{removed})")
            path.write_text(original, encoding="utf-8")
        else:
            print(f"+ {path} (removed foreignObject -{removed})")

    if mode == "check" and changed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
