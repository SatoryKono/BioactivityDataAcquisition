#!/usr/bin/env python3
"""
inject_svg_styles.py — Inject CSS overrides into rendered Mermaid SVG files.

Mermaid generates ID-scoped CSS rules that make edge labels semi-transparent:
  #my-svg .edgeLabel rect { opacity: .5 }
  #my-svg .labelBkg { background-color: rgba(255,255,255,.5) }

The custom.css !important overrides are stripped by mmdc during SVG extraction.
This post-processor re-injects those rules into the SVG <style> block with
proper ID-scoped specificity.

Usage:
    # Check all SVGs (exit 1 if injection needed)
    python scripts/diagrams/fix/fix_svg_styles.py --check

    # Fix all SVGs in-place
    python scripts/diagrams/fix/fix_svg_styles.py --fix

    # Dry-run: show what would change
    python scripts/diagrams/fix/fix_svg_styles.py --dry-run

    # Process specific files
    python scripts/diagrams/fix/fix_svg_styles.py --fix -f docs/.../svg/10-resilience-patterns.svg

    # Process specific directory
    python scripts/diagrams/fix/fix_svg_styles.py --fix --dir docs/.../architecture/svg
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from scripts.diagrams.core.diagram_paths import render_dir
except ImportError:  # pragma: no cover - direct script execution
    from scripts.diagrams.core.diagram_paths import render_dir

# ── Defaults ────────────────────────────────────────────────────────────────

SVG_DIRS = [
    render_dir("architecture", "svg"),
    render_dir("class-diagrams", "svg"),
    render_dir("foundation", "svg"),
]

# ── ANSI colours ────────────────────────────────────────────────────────────

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

# ── Sentinel ────────────────────────────────────────────────────────────────

SENTINEL = "/* bioetl-inject */"

# ── Regex patterns ──────────────────────────────────────────────────────────

_SVG_ID_RE = re.compile(r'<svg[^>]+\bid="([^"]+)"')
_STYLE_CLOSE_RE = re.compile(r"(\]\]></style>|</style>)")


# ── CSS rules to inject ────────────────────────────────────────────────────


def _build_css_rules(svg_id: str) -> str:
    """Build ID-scoped CSS override rules for edge label readability."""
    return (
        f"{SENTINEL}"
        f"#{svg_id} .edgeLabel rect{{opacity:1!important;fill:#ffffff!important}}"
        f"#{svg_id} .labelBkg{{background-color:#ffffff!important;opacity:1!important}}"
        f"#{svg_id} .edgeLabel .labelBkg{{background-color:#ffffff!important;opacity:1!important}}"
        f"#{svg_id} .edgeLabel{{font-size:12px;line-height:1.1;padding:1px 3px}}"
        f"#{svg_id} .edgeLabel span{{color:#111827!important;fill:#111827!important;opacity:1!important;line-height:1.1;margin:0;padding:0}}"
        f"#{svg_id} .edgeLabel p{{color:#111827!important;fill:#111827!important;opacity:1!important;line-height:1.1;margin:0;padding:0}}"
        f"#{svg_id} text.fo-fallback{{color:#111827!important;fill:#111827!important;opacity:1!important}}"
    )


# ── Core logic ──────────────────────────────────────────────────────────────


def needs_injection(content: str) -> bool:
    """Check if SVG content already has injected styles."""
    return SENTINEL not in content


def inject_styles(content: str) -> str | None:
    """Inject CSS overrides into SVG <style> block.

    Returns modified content, or None if no changes needed.
    """
    if not needs_injection(content):
        return None

    # Extract SVG id
    id_match = _SVG_ID_RE.search(content)
    if not id_match:
        return None
    svg_id = id_match.group(1)

    # Find style closing tag
    close_match = _STYLE_CLOSE_RE.search(content)
    if not close_match:
        return None

    css_rules = _build_css_rules(svg_id)
    insert_pos = close_match.start()
    return content[:insert_pos] + css_rules + content[insert_pos:]


# ── File processing ─────────────────────────────────────────────────────────


def collect_svg_files(
    files: list[Path] | None,
    dirs: list[Path] | None,
) -> list[Path]:
    """Collect SVG files from explicit files list or directories."""
    result: list[Path] = []
    if files:
        result.extend(files)
    elif dirs:
        for d in dirs:
            if d.is_dir():
                result.extend(sorted(d.glob("*.svg")))
    else:
        for d in SVG_DIRS:
            if d.is_dir():
                result.extend(sorted(d.glob("*.svg")))
    return result


def process_file(
    path: Path,
    *,
    mode: str,
) -> bool:
    """Process a single SVG file. Returns True if changes were made/needed."""
    content = path.read_text(encoding="utf-8")

    new_content = inject_styles(content)
    if new_content is None:
        return False

    name = path.name
    if mode == "check":
        print(f"  {YELLOW}!{NC} {name}  (needs injection)")
        return True
    elif mode == "dry-run":
        print(f"  {CYAN}~{NC} {name}  (would inject)")
        return True
    else:  # fix
        path.write_text(new_content, encoding="utf-8")
        print(f"  {GREEN}+{NC} {name}  (injected)")
        return True


# ── CLI ─────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inject CSS overrides into Mermaid SVG files for edge label readability.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check", action="store_true", help="Check mode (exit 1 if injection needed)"
    )
    group.add_argument("--fix", action="store_true", help="Fix SVGs in-place")
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
    svg_files = collect_svg_files(args.file, args.dir)

    if not svg_files:
        print(f"{YELLOW}No SVG files found.{NC}")
        return 0

    print(f"{BOLD}inject_svg_styles{NC} [{mode}]  ({len(svg_files)} files)")

    changed = 0
    for path in svg_files:
        if process_file(path, mode=mode):
            changed += 1

    if changed == 0:
        print(f"\n{GREEN}All files OK — no injection needed.{NC}")
        return 0

    if mode == "check":
        print(f"\n{RED}{changed} file(s) need CSS injection. Run with --fix.{NC}")
        return 1

    if mode == "dry-run":
        print(f"\n{YELLOW}{changed} file(s) would be modified.{NC}")
        return 0

    print(f"\n{GREEN}{changed} file(s) injected.{NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
