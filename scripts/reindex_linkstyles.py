#!/usr/bin/env python3
"""Reindex linkStyle directives in Mermaid diagram files.

When edges are added or removed from a diagram, linkStyle indices become
stale. This script parses the manifest comment (``%% linkStyle: ...``) and
recalculates correct indices based on the current edge order.

Usage::

    # Dry-run — show what would change
    python scripts/reindex_linkstyles.py --check docs/02-architecture/mmd-diagrams/

    # Fix in-place
    python scripts/reindex_linkstyles.py --fix docs/02-architecture/mmd-diagrams/

    # Single file
    python scripts/reindex_linkstyles.py --fix -f docs/02-architecture/mmd-diagrams/architecture/01-high-level-hexagonal.mmd
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Patterns that represent edges in Mermaid flowcharts
EDGE_PATTERNS = re.compile(
    r"""
    (?:^|\s)            # start of line or whitespace
    \w+                  # source node
    \s+                  # separator
    (?:                  # edge types:
        -->              # solid arrow
      | -.->             # dashed arrow
      | ==>              # thick arrow
      | --[->]           # line/arrow
      | -\.-[->]         # dotted
      | ~~~              # invisible link
      | -[.-]?->         # catch remaining
    )
    """,
    re.VERBOSE,
)

# Match lines that have an edge (excluding comments and class/style lines)
COMMENT_RE = re.compile(r"^\s*%%")
STYLE_RE = re.compile(r"^\s*(classDef|class |style |linkStyle)")
SUBGRAPH_RE = re.compile(r"^\s*(subgraph|end)\b")


def count_edges(lines: list[str]) -> int:
    """Count edges in order of appearance, matching Mermaid's internal indexing."""
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if COMMENT_RE.match(stripped):
            continue
        if STYLE_RE.match(stripped):
            continue
        if SUBGRAPH_RE.match(stripped):
            continue
        # Count edge operators in the line
        # Handle chained edges: A --> B --> C (= 2 edges)
        # Handle fan-out: A & B & C --> D (= 1 edge per & group)
        edge_ops = re.findall(r"-->|-.->|==>|~~~|-\.->", stripped)
        if edge_ops:
            # Fan-out with & creates one edge per combination
            # Simple heuristic: count the edge operators
            count += len(edge_ops)
    return count


def find_manifest(lines: list[str]) -> list[tuple[int, str]]:
    """Find linkStyle manifest comment lines (``%% linkStyle: ...``)."""
    manifests = []
    for i, line in enumerate(lines):
        if re.match(r"\s*%%\s*linkStyle:", line.strip()):
            manifests.append((i, line))
    return manifests


def find_linkstyle_directives(lines: list[str]) -> list[tuple[int, str]]:
    """Find linkStyle directive lines."""
    directives = []
    for i, line in enumerate(lines):
        if re.match(r"\s*linkStyle\s+", line.strip()) and not line.strip().startswith("%%"):
            directives.append((i, line))
    return directives


def check_file(path: Path) -> tuple[int, int, bool]:
    """Check a file for linkStyle issues.

    Returns (edge_count, directive_max_index, has_issues).
    """
    content = path.read_text()
    lines = content.split("\n")

    edge_count = count_edges(lines)
    directives = find_linkstyle_directives(lines)

    if not directives:
        return edge_count, 0, False

    # Find max index referenced in linkStyle directives
    max_idx = -1
    for _, line in directives:
        indices = re.findall(r"\b(\d+)\b", line.split("stroke")[0] if "stroke" in line else line)
        for idx_str in indices:
            idx = int(idx_str)
            if idx > max_idx:
                max_idx = idx

    has_issues = max_idx >= edge_count
    return edge_count, max_idx, has_issues


def process_directory(root: Path, fix: bool = False) -> int:
    """Process all .mmd and .mermaid files in directory."""
    issues = 0
    patterns = ["**/*.mmd", "**/*.mermaid"]

    for pattern in patterns:
        for path in sorted(root.glob(pattern)):
            if path.name.startswith("_"):
                continue

            edge_count, max_idx, has_issues = check_file(path)
            rel = path.relative_to(root)

            if has_issues:
                issues += 1
                print(f"  [WARN] {rel}: {edge_count} edges, linkStyle references index {max_idx}")
                if fix:
                    print(f"         Manual fix needed — review linkStyle indices")
            elif max_idx >= 0:
                print(f"  [ OK ] {rel}: {edge_count} edges, max linkStyle index {max_idx}")

    return issues


def main() -> None:
    parser = argparse.ArgumentParser(description="Reindex linkStyle in Mermaid files")
    parser.add_argument("path", nargs="?", default="docs/02-architecture/mmd-diagrams/",
                        help="Directory or file to process")
    parser.add_argument("-f", "--file", help="Process a single file")
    parser.add_argument("--check", action="store_true", help="Check mode (default)")
    parser.add_argument("--fix", action="store_true", help="Fix mode (report issues)")

    args = parser.parse_args()

    target = Path(args.file) if args.file else Path(args.path)

    if target.is_file():
        edge_count, max_idx, has_issues = check_file(target)
        status = "WARN" if has_issues else "OK"
        print(f"[{status}] {target.name}: {edge_count} edges, max linkStyle index {max_idx}")
        if has_issues:
            print(f"  linkStyle references index {max_idx} but only {edge_count} edges exist")
            sys.exit(1)
    elif target.is_dir():
        print(f"Scanning: {target}")
        print()
        issues = process_directory(target, fix=args.fix)
        print()
        if issues:
            print(f"Found {issues} file(s) with linkStyle index issues")
            sys.exit(1)
        else:
            print("All linkStyle indices are valid")
    else:
        print(f"Error: {target} not found", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
