#!/usr/bin/env python3
"""
uniform_diagram_sizes.py — Normalize object sizes in Mermaid diagrams.

For each diagram file, determines the maximum width (by longest visible text
line) and maximum height (by most content lines) across all objects, then
pads every object to those dimensions using &nbsp; characters.

Supports two diagram types:
  - classDiagram:  class Name { ... } blocks
  - flowchart/graph:  ID["Label<br/>line2<br/>..."] nodes

Usage:
    # Check all diagrams (exit 1 on drift)
    python scripts/uniform_diagram_sizes.py --check

    # Fix all diagrams in-place
    python scripts/uniform_diagram_sizes.py --fix

    # Dry-run: show diff without writing
    python scripts/uniform_diagram_sizes.py --dry-run

    # Process specific files
    python scripts/uniform_diagram_sizes.py --fix -f docs/.../01-domain-ports.mmd

    # Process specific directory
    python scripts/uniform_diagram_sizes.py --fix --dir docs/.../class-diagrams
"""
from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── Defaults ────────────────────────────────────────────────────────────────

DIAGRAM_DIRS = [
    Path("docs/02-architecture/mmd-diagrams/architecture"),
    Path("docs/02-architecture/mmd-diagrams/class-diagrams"),
    Path("docs/02-architecture/mmd-diagrams/foundation"),
]
SUPPORTED_SUFFIXES = {".mmd", ".mermaid"}

# ── ANSI colours ────────────────────────────────────────────────────────────

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
NC = "\033[0m"

# ── Regex patterns ──────────────────────────────────────────────────────────

_CLASS_DIAGRAM_RE = re.compile(r"^\s*classDiagram\b", re.IGNORECASE)
_FLOWCHART_RE = re.compile(r"^\s*(graph|flowchart)\b", re.IGNORECASE)
_CLASS_BLOCK_START_RE = re.compile(r"^\s+class\s+(\w+)\s*\{")
_CLASS_BLOCK_END_RE = re.compile(r"^\s+\}")
_UNIFORM_TAG_RE = re.compile(
    r"^(%% @uniform\b).*$"
)
_NBSP = "&nbsp;"

# Flowchart node patterns:
#   ID["Label text"]         — rectangle
#   ID(["Label text"])       — rounded
#   ID[("Label text")]       — cylinder
#   ID(("Label text"))       — circle
#   ID{{"Label text"}}       — hexagon
# We capture: ID, opening bracket sequence, label content, closing bracket sequence
_FLOWCHART_NODE_RE = re.compile(
    r'^(\s+)'                       # leading indent
    r'(\w+)'                        # node ID
    r'(\["|\(\["|\[\("|\(\("|\{\{")'  # opening brackets
    r'(.+?)'                        # label content (non-greedy)
    r'("\]|"\)\]|"\)\]|"\)\)|"\}\})'  # closing brackets
    r'\s*$'                         # trailing whitespace
)


# ── Data structures ─────────────────────────────────────────────────────────

@dataclass
class ClassBlock:
    """A parsed class block from a classDiagram."""

    name: str
    start_line: int  # index in file lines (0-based), the `class Name {` line
    end_line: int  # index of the closing `}`
    stereotype_line: str | None  # e.g. "<<Protocol>>" with existing padding
    content_lines: list[str]  # real content lines (stripped of padding &nbsp;)
    padding_lines: int  # count of trailing &nbsp;-only lines
    raw_lines: list[str]  # original lines between { and } (exclusive)
    indent: str  # whitespace prefix for body lines


@dataclass
class FlowchartNode:
    """A parsed flowchart node."""

    node_id: str
    line_index: int
    indent: str
    open_bracket: str
    close_bracket: str
    label_parts: list[str]  # split by <br/>
    content_parts: list[str]  # label_parts stripped of &nbsp; padding
    raw_label: str


@dataclass
class UniformStats:
    """Computed uniform dimensions for a diagram."""

    max_visible_width: int  # in characters (longest line across all objects)
    max_total_body: int  # total body lines (stereotype + content) max
    max_title_len: int  # longest class/node name


# ── Helpers ─────────────────────────────────────────────────────────────────

def _strip_nbsp(text: str) -> str:
    """Remove trailing &nbsp; sequences from text."""
    while text.endswith(_NBSP):
        text = text[: -len(_NBSP)]
    return text.rstrip()


def _count_visual_chars(text: str) -> int:
    """Count visual character width, treating &nbsp; as 1 char."""
    clean = text.replace(_NBSP, " ")
    return len(clean)


def _is_nbsp_only(text: str) -> bool:
    """Check if line consists only of &nbsp; and whitespace."""
    return text.strip().replace(_NBSP, "").strip() == ""


def _pad_width(text: str, target_width: int) -> str:
    """Pad text with &nbsp; to reach target visual width."""
    current = _count_visual_chars(text)
    if current >= target_width:
        return text
    needed = target_width - current
    return text + _NBSP * needed


# ── Class diagram parser ───────────────────────────────────────────────────

def _detect_diagram_type(lines: list[str]) -> str | None:
    """Detect whether file is classDiagram or flowchart."""
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            if stripped.startswith("%%{"):
                continue
            continue
        if _CLASS_DIAGRAM_RE.match(stripped):
            return "class"
        if _FLOWCHART_RE.match(stripped):
            return "flowchart"
        return None
    return None


def _parse_class_blocks(lines: list[str]) -> list[ClassBlock]:
    """Parse all class blocks from classDiagram lines."""
    blocks: list[ClassBlock] = []
    i = 0
    while i < len(lines):
        m = _CLASS_BLOCK_START_RE.match(lines[i])
        if m:
            name = m.group(1)
            start = i
            # Detect indent from body lines
            indent = "        "  # default 8 spaces
            # Find closing brace
            j = i + 1
            body_lines: list[str] = []
            while j < len(lines):
                if _CLASS_BLOCK_END_RE.match(lines[j]):
                    break
                body_lines.append(lines[j])
                j += 1
            end = j

            # Detect actual indent
            for bl in body_lines:
                if bl.strip():
                    indent = bl[: len(bl) - len(bl.lstrip())]
                    break

            # Separate stereotype, content, and padding
            stereotype_line: str | None = None
            content_lines: list[str] = []
            padding_count = 0

            for bl in body_lines:
                stripped = bl.strip()
                if stereotype_line is None and stripped.startswith("<<"):
                    stereotype_line = stripped
                elif _is_nbsp_only(stripped):
                    padding_count += 1
                else:
                    # If we had padding lines before content, they were
                    # actually content separators — treat them as content
                    if padding_count > 0 and content_lines:
                        content_lines.extend([""] * padding_count)
                        padding_count = 0
                    if stripped:
                        content_lines.append(stripped)

            blocks.append(
                ClassBlock(
                    name=name,
                    start_line=start,
                    end_line=end,
                    stereotype_line=stereotype_line,
                    content_lines=content_lines,
                    padding_lines=padding_count,
                    raw_lines=body_lines,
                    indent=indent,
                )
            )
            i = end + 1
        else:
            i += 1

    return blocks


def _compute_class_uniform(blocks: list[ClassBlock]) -> UniformStats:
    """Compute uniform dimensions across all class blocks.

    Height is computed as total body lines (stereotype + content), so
    classes with and without stereotypes get the same rendered height.
    """
    max_title = 0
    max_total_body = 0
    max_width = 0

    for b in blocks:
        # Title length (class name)
        max_title = max(max_title, len(b.name))

        # Total body = stereotype (0 or 1) + content lines
        stripped_content = [_strip_nbsp(c) for c in b.content_lines]
        total_body = (1 if b.stereotype_line else 0) + len(stripped_content)
        max_total_body = max(max_total_body, total_body)

        # Max visible width across all visible lines in block
        all_visible: list[str] = []
        if b.stereotype_line:
            all_visible.append(_strip_nbsp(b.stereotype_line))
        all_visible.extend(stripped_content)

        for line in all_visible:
            max_width = max(max_width, _count_visual_chars(line))

    return UniformStats(
        max_visible_width=max_width,
        max_total_body=max_total_body,
        max_title_len=max_title,
    )


def _rebuild_class_block(
    block: ClassBlock,
    stats: UniformStats,
) -> list[str]:
    """Rebuild a class block with uniform padding.

    Total body lines = stereotype (0 or 1) + content + padding = max_total_body.
    """
    result: list[str] = []

    # Stereotype line (pad width)
    if block.stereotype_line:
        stripped_stereo = _strip_nbsp(block.stereotype_line)
        padded = _pad_width(stripped_stereo, stats.max_visible_width)
        result.append(f"{block.indent}{padded}")

    # Content lines (pad width)
    stripped_content = [_strip_nbsp(c) for c in block.content_lines]
    for line in stripped_content:
        if line:
            padded = _pad_width(line, stats.max_visible_width)
            result.append(f"{block.indent}{padded}")
        else:
            result.append(f"{block.indent}{_NBSP}")

    # Height padding: total body (stereo + content + padding) = max_total_body
    current_body = (1 if block.stereotype_line else 0) + len(stripped_content)
    pad_needed = stats.max_total_body - current_body
    for _ in range(pad_needed):
        result.append(f"{block.indent}{_NBSP}")

    return result


def _normalize_class_diagram(lines: list[str]) -> list[str]:
    """Normalize all class blocks in a classDiagram to uniform sizes."""
    blocks = _parse_class_blocks(lines)
    if not blocks:
        return lines

    stats = _compute_class_uniform(blocks)

    # Rebuild file, replacing block bodies
    result: list[str] = []
    block_map: dict[int, ClassBlock] = {b.start_line: b for b in blocks}
    skip_until: int | None = None

    for i, line in enumerate(lines):
        if skip_until is not None:
            if i <= skip_until:
                continue
            skip_until = None

        if i in block_map:
            b = block_map[i]
            # Write the class header line
            result.append(line)
            # Write rebuilt body
            result.extend(_rebuild_class_block(b, stats))
            # Write closing brace
            result.append(lines[b.end_line])
            skip_until = b.end_line
        else:
            result.append(line)

    # Update @uniform tag
    result = _update_uniform_tag(result, stats, "class")

    return result


# ── Flowchart parser ────────────────────────────────────────────────────────

def _parse_flowchart_nodes(lines: list[str]) -> list[FlowchartNode]:
    """Parse flowchart nodes that use multi-line labels (with <br/>)."""
    nodes: list[FlowchartNode] = []

    for i, line in enumerate(lines):
        m = _FLOWCHART_NODE_RE.match(line)
        if m:
            indent = m.group(1)
            node_id = m.group(2)
            open_br = m.group(3)
            raw_label = m.group(4)
            close_br = m.group(5)

            # Split by <br/> (case insensitive)
            parts = re.split(r"<br/?>", raw_label, flags=re.IGNORECASE)
            content_parts = [_strip_nbsp(p) for p in parts]

            nodes.append(
                FlowchartNode(
                    node_id=node_id,
                    line_index=i,
                    indent=indent,
                    open_bracket=open_br,
                    close_bracket=close_br,
                    label_parts=parts,
                    content_parts=content_parts,
                    raw_label=raw_label,
                )
            )

    return nodes


def _compute_flowchart_uniform(nodes: list[FlowchartNode]) -> UniformStats:
    """Compute uniform dimensions for flowchart nodes."""
    max_title = 0
    max_lines = 0
    max_width = 0

    for n in nodes:
        # First part is typically the title
        if n.content_parts:
            max_title = max(max_title, _count_visual_chars(n.content_parts[0]))

        # Number of <br/> parts
        max_lines = max(max_lines, len(n.content_parts))

        # Width of each part
        for part in n.content_parts:
            max_width = max(max_width, _count_visual_chars(part))

    return UniformStats(
        max_visible_width=max_width,
        max_total_body=max_lines,
        max_title_len=max_title,
    )


def _rebuild_flowchart_node(
    node: FlowchartNode,
    stats: UniformStats,
) -> str:
    """Rebuild a flowchart node with uniform padding."""
    # Pad each content part to max width
    padded_parts: list[str] = []
    for part in node.content_parts:
        if part:
            padded_parts.append(_pad_width(part, stats.max_visible_width))
        else:
            padded_parts.append(_NBSP)

    # Height padding: add <br/>&nbsp; lines
    while len(padded_parts) < stats.max_total_body:
        padded_parts.append(_NBSP)

    label = "<br/>".join(padded_parts)
    return (
        f"{node.indent}{node.node_id}"
        f"{node.open_bracket}{label}{node.close_bracket}"
    )


def _normalize_flowchart(lines: list[str]) -> list[str]:
    """Normalize all flowchart nodes to uniform sizes."""
    nodes = _parse_flowchart_nodes(lines)
    if not nodes:
        return lines

    stats = _compute_flowchart_uniform(nodes)

    # Build index of lines to replace
    replacements: dict[int, str] = {}
    for n in nodes:
        replacements[n.line_index] = _rebuild_flowchart_node(n, stats)

    result: list[str] = []
    for i, line in enumerate(lines):
        if i in replacements:
            result.append(replacements[i])
        else:
            result.append(line)

    result = _update_uniform_tag(result, stats, "flowchart")

    return result


# ── @uniform tag management ─────────────────────────────────────────────────

def _update_uniform_tag(
    lines: list[str],
    stats: UniformStats,
    diagram_type: str,
) -> list[str]:
    """Update or insert the @uniform metadata tag.

    Pixel estimates use heuristics calibrated to existing diagrams:
      Class name rendered at 15px bold ≈ 10px/char.
      Body text rendered at 12-13px ≈ 7px/char.
      Box width = max(title_width, body_width).
      height ≈ max_total_body * 18 + 36 (18px per line + 36px header).
    """
    title_char_px = 10  # 15px bold font
    body_char_px = 7  # 12-13px regular font
    line_px = 18
    header_px = 36  # class name header height

    # Box width is max of title and body widths
    title_px = stats.max_title_len * title_char_px
    body_px = stats.max_visible_width * body_char_px
    est_width = max(title_px, body_px)
    est_height = stats.max_total_body * line_px + header_px

    # Round to nearest 8px for clean values
    est_width = ((est_width + 7) // 8) * 8
    est_height = ((est_height + 7) // 8) * 8

    if diagram_type == "class":
        tag = (
            f"%% @uniform class "
            f"width={est_width} height={est_height} "
            f"max_title_len={stats.max_title_len} "
            f"max_desc_lines={stats.max_total_body}"
        )
    else:
        tag = (
            f"%% @uniform "
            f"width={est_width} height={est_height} "
            f"max_title_len={stats.max_title_len} "
            f"max_desc_lines={stats.max_total_body}"
        )

    # Find and replace existing @uniform, or insert before diagram declaration
    for i, line in enumerate(lines):
        if _UNIFORM_TAG_RE.match(line.strip()):
            lines[i] = tag
            return lines

    # Insert before first diagram declaration line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if (
            _CLASS_DIAGRAM_RE.match(stripped)
            or _FLOWCHART_RE.match(stripped)
            or stripped.startswith("%%{init")
        ):
            lines.insert(i, tag)
            return lines

    return lines


# ── Main processing ─────────────────────────────────────────────────────────

def normalize_file(path: Path) -> tuple[str, str, bool]:
    """Normalize a single diagram file.

    Returns (original_content, normalized_content, changed).
    """
    content = path.read_text(encoding="utf-8")
    lines = content.splitlines()

    dtype = _detect_diagram_type(lines)
    if dtype == "class":
        normalized = _normalize_class_diagram(lines)
    elif dtype == "flowchart":
        normalized = _normalize_flowchart(lines)
    else:
        return content, content, False

    new_content = "\n".join(normalized)
    # Preserve trailing newline
    if content.endswith("\n"):
        new_content += "\n"

    return content, new_content, content != new_content


def find_diagram_files(targets: list[Path]) -> list[Path]:
    """Find all supported diagram files from target paths."""
    files: list[Path] = []
    seen: set[Path] = set()

    for target in targets:
        if target.is_file():
            if target.suffix in SUPPORTED_SUFFIXES and target not in seen:
                seen.add(target)
                files.append(target)
            continue

        for suffix in SUPPORTED_SUFFIXES:
            for f in sorted(target.rglob(f"*{suffix}")):
                if not f.name.startswith("_") and f not in seen:
                    seen.add(f)
                    files.append(f)

    return sorted(files)


def show_diff(path: Path, original: str, normalized: str) -> None:
    """Print a unified diff for a file."""
    import io

    # Force UTF-8 output to avoid Windows cp1251 encoding errors
    out = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        normalized.splitlines(keepends=True),
        fromfile=f"a/{path.name}",
        tofile=f"b/{path.name}",
        n=2,
    )
    for line in diff:
        if line.startswith("+") and not line.startswith("+++"):
            out.write(f"{GREEN}{line}{NC}")
        elif line.startswith("-") and not line.startswith("---"):
            out.write(f"{RED}{line}{NC}")
        elif line.startswith("@@"):
            out.write(f"{CYAN}{line}{NC}")
        else:
            out.write(line)
    out.flush()
    out.detach()  # prevent closing sys.stdout


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize object sizes in Mermaid diagrams. "
            "Pads all objects to uniform width (by max name length) "
            "and height (by max description lines)."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--check",
        action="store_true",
        help="Check for drift (exit 1 if any file needs normalization)",
    )
    mode.add_argument(
        "--fix",
        action="store_true",
        help="Fix files in-place",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Show diffs without writing",
    )
    parser.add_argument(
        "-f",
        "--files",
        nargs="+",
        type=Path,
        help="Specific files to process",
    )
    parser.add_argument(
        "--dir",
        nargs="+",
        type=Path,
        dest="dirs",
        help="Specific directories to process",
    )

    args = parser.parse_args()

    # Determine targets
    if args.files:
        targets = args.files
    elif args.dirs:
        targets = args.dirs
    else:
        targets = [d for d in DIAGRAM_DIRS if d.exists()]

    files = find_diagram_files(targets)
    if not files:
        print(f"{YELLOW}No diagram files found.{NC}")
        return 0

    print(f"{BOLD}Uniform Diagram Sizer{NC}")
    print(f"  Files: {len(files)}")
    print()

    changed_count = 0
    checked_count = 0
    error_count = 0

    for path in files:
        try:
            original, normalized, changed = normalize_file(path)
        except Exception as e:
            print(f"  {RED}ERROR{NC}  {path.name}: {e}")
            error_count += 1
            continue

        checked_count += 1

        if not changed:
            if not args.check:
                print(f"  {GREEN}OK{NC}     {path}")
            continue

        changed_count += 1

        if args.check:
            print(f"  {RED}DRIFT{NC}  {path}")
        elif args.dry_run:
            print(f"  {YELLOW}DIFF{NC}   {path}")
            show_diff(path, original, normalized)
            print()
        else:
            path.write_text(normalized, encoding="utf-8")
            print(f"  {GREEN}FIXED{NC}  {path}")

    # Summary
    print()
    print(f"  Checked: {checked_count}")
    if args.fix:
        print(f"  {GREEN}Fixed:   {changed_count}{NC}")
    elif args.check:
        print(f"  Drifted: {changed_count}")
    else:
        print(f"  Would fix: {changed_count}")
    if error_count:
        print(f"  {RED}Errors:  {error_count}{NC}")

    if args.check and changed_count > 0:
        print()
        print(
            f"  {RED}FAIL{NC}: {changed_count} file(s) need normalization. "
            f"Run with --fix to correct."
        )
        return 1

    return 1 if error_count > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
