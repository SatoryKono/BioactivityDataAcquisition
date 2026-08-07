#!/usr/bin/env python3
"""Strip Mermaid foreignObject labels from rendered SVG files.

Use-case:
  In fallback-only mode we keep plain SVG <text class="fo-fallback"> labels
  and remove HTML-based foreignObject labels to avoid duplicate text rendering
  in viewers that support both layers.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
for import_root in (REPO_ROOT, SCRIPT_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

try:
    from scripts.diagrams.core.diagram_paths import SOURCE_FAMILIES, render_dir
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import SOURCE_FAMILIES, render_dir

SVG_DIRS = [render_dir(family, "svg") for family in SOURCE_FAMILIES]

FOREIGN_OBJECT_PATTERN = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?foreignObject\b[^>]*>.*?"
    r"</(?:[A-Za-z_][\w.-]*:)?foreignObject\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)
SELF_CLOSING_FOREIGN_OBJECT_PATTERN = re.compile(
    r"<(?:[A-Za-z_][\w.-]*:)?foreignObject\b[^>]*/\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)


def _write_text_atomic(path: Path, payload: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(payload)
        temp_path = Path(temp_file.name)
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=REPO_ROOT)
    temp_path.replace(path)


def _strip_foreign_objects_payload(payload: str) -> tuple[str, int]:
    """Remove Mermaid label elements without requiring XML-valid XHTML content."""
    payload, paired_count = FOREIGN_OBJECT_PATTERN.subn("", payload)
    payload, self_closing_count = SELF_CLOSING_FOREIGN_OBJECT_PATTERN.subn("", payload)
    return payload, paired_count + self_closing_count


def strip_foreign_objects(path: Path) -> int:
    payload = resolve_output_path(path).read_text(encoding="utf-8")
    stripped, removed = _strip_foreign_objects_payload(payload)
    if removed > 0:
        _write_text_atomic(path, stripped)
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
    group.add_argument(
        "--check", action="store_true", help="Exit 1 if stripping is needed"
    )
    group.add_argument("--fix", action="store_true", help="Write changes in place")
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument(
        "-f", "--file", type=Path, action="append", help="Specific SVG file(s)"
    )
    parser.add_argument(
        "--dir", type=Path, action="append", help="Specific directory(ies)"
    )
    args = parser.parse_args()

    if args.check:
        mode = "check"
    elif args.dry_run:
        mode = "dry-run"
    else:
        mode = "fix"
    files = collect_svg_files(args.file, args.dir)
    if not files:
        print("No SVG files found.")
        return 0

    changed = 0
    for path in files:
        payload = resolve_output_path(path).read_text(encoding="utf-8")
        stripped, removed = _strip_foreign_objects_payload(payload)
        if removed == 0:
            continue
        changed += 1
        if mode == "check":
            print(f"! {path} (needs foreignObject strip, -{removed})")
        elif mode == "dry-run":
            print(f"~ {path} (would remove foreignObject -{removed})")
        else:
            _write_text_atomic(path, stripped)
            print(f"+ {path} (removed foreignObject -{removed})")

    if mode == "check" and changed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
