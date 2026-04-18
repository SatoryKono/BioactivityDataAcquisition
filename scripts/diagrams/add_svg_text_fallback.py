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
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .diagram_paths import SOURCE_FAMILIES, render_dir
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import SOURCE_FAMILIES, render_dir

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
_OBJECT_SUFFIX_SPACING_RE = re.compile(
    r"(?<=\S)(Mixin|Adapter|Port|Validator|Runer|Runner|Coordinator)\b"
)
_CLASS_METHOD_LINE_RE = re.compile(r"^\s*[+\-#~]\s*[A-Za-z_][A-Za-z0-9_]*\s*\(")

SVG_DIRS = [render_dir(family, "svg") for family in SOURCE_FAMILIES]


def _ensure_repo_path(path: Path) -> Path:
    resolved_root = REPO_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(
            f"refusing to process path outside {resolved_root}: {resolved_path}"
        )
    return resolved_path


def _write_repo_text(path: Path, content: str) -> None:
    """Write text only after resolving the target inside the repository root."""
    safe_path = _ensure_repo_path(path)
    safe_path.write_text(content, encoding="utf-8")


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
    """Extract collapsed single-line text from node tree."""
    return _normalize_text(" ".join(node.itertext()))


def _append_raw_text(parts: list[str], raw: str | None) -> None:
    if raw is None:
        return
    if raw:
        parts.append(raw)


def _extract_text_lines(node: ET.Element) -> list[str]:
    """Extract semantic text lines from foreignObject HTML content.

    Mermaid labels are rendered through foreignObject HTML with explicit <br/>
    markers. We preserve these line breaks and convert to compact plain-text
    lines for SVG fallback text.
    """

    parts: list[str] = []

    def visit(elem: ET.Element) -> None:
        _append_raw_text(parts, elem.text)
        for child in list(elem):
            child_name = _local_name(child.tag).lower()
            if child_name == "br":
                parts.append("\n")
            else:
                visit(child)
                if child_name in {"p", "div", "li"}:
                    parts.append("\n")
            _append_raw_text(parts, child.tail)

    visit(node)
    raw = "".join(parts)
    # Treat escaped '\n' from source labels as explicit line breaks (like <br>).
    raw = raw.replace("\\n", "\n")
    if not raw:
        return []

    normalized: list[str] = [_normalize_text(line) for line in raw.split("\n")]

    # Collapse large blank gaps from Mermaid padding (<br/><br/>...).
    compact: list[str] = []
    prev_blank = False
    for line in normalized:
        is_blank = not line
        if is_blank and prev_blank:
            continue
        compact.append(line)
        prev_blank = is_blank

    while compact and not compact[0]:
        compact.pop(0)
    while compact and not compact[-1]:
        compact.pop()

    return compact


def _class_tokens(node: ET.Element | None) -> set[str]:
    if node is None:
        return set()
    raw = node.attrib.get("class", "")
    return {token for token in raw.split() if token}


def _detect_label_kind(
    parent: ET.Element, parent_map: dict[ET.Element, ET.Element]
) -> str:
    """Infer semantic label kind from parent/ancestor class groups."""
    chain: list[ET.Element] = [parent]
    current = parent
    for _ in range(3):
        current = parent_map.get(current)
        if current is None:
            break
        chain.append(current)

    tokens = set().union(*(_class_tokens(node) for node in chain))

    if "methods-group" in tokens:
        return "methods"
    if "members-group" in tokens:
        return "members"
    if (
        "label-group" in tokens
        or "annotation-group" in tokens
        or "cluster-label" in tokens
    ):
        return "title"
    if "edgeLabel" in tokens:
        return "edge"
    return "generic"


def _is_method_signature_line(line: str) -> bool:
    return bool(_CLASS_METHOD_LINE_RE.match(line))


def _sanitize_label_line(line: str, label_kind: str) -> str:
    stripped = line.strip()
    if not stripped:
        return ""

    # Collapse decorative separators to a short neutral divider.
    if len(stripped) >= 6 and not any(ch.isalnum() for ch in stripped):
        glyphs = {ch for ch in stripped if not ch.isspace()}
        if len(glyphs) <= 3:
            return "--------"

    # Normalize slash separators for more readable fallback labels.
    stripped = re.sub(r"\s*/\s*", " / ", stripped)

    # Keep UML method signatures intact in methods-group:
    # "+fetch(entity_type)" must not become "+fetch (entity_type)".
    if label_kind != "methods" and not _is_method_signature_line(stripped):
        # Insert spacing around parentheses in glued tokens:
        # "Foo(bar)" -> "Foo (bar) ", "X)(Y" -> "X) (Y".
        stripped = re.sub(r"(?<=\S)\(", " (", stripped)
        stripped = re.sub(r"\)(?=\S)", ") ", stripped)

    # Improve wrapping for long PascalCase/camelCase identifiers.
    # humanized = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", stripped)
    # humanized = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", humanized)
    humanized = stripped
    return humanized


def _estimate_wrap_chars(width: float, font_size: float) -> int:
    # Approximate average glyph width for sans-serif text.
    avg_char_width = max(font_size * 0.56, 6.0)
    usable_width = max(width * 0.88, 40.0)
    estimate = int(usable_width / avg_char_width)
    return max(18, min(64, estimate))


def _add_suffix_spacing_for_long_object_name(
    line: str,
    max_chars: int,
    label_kind: str,
) -> str:
    """Insert split points before common object-type suffixes on long labels."""
    if len(line) <= max_chars:
        return line
    if label_kind == "methods" or _is_method_signature_line(line):
        return line
    return _OBJECT_SUFFIX_SPACING_RE.sub(r" \1", line)


def _wrap_label_lines(lines: list[str], max_chars: int, label_kind: str) -> list[str]:
    wrapped: list[str] = []
    for raw in lines:
        line = _sanitize_label_line(raw, label_kind=label_kind)
        line = _add_suffix_spacing_for_long_object_name(
            line,
            max_chars=max_chars,
            label_kind=label_kind,
        )
        if not line:
            if wrapped and wrapped[-1]:
                wrapped.append("")
            continue
        chunks = textwrap.wrap(
            line,
            width=max_chars,
            break_long_words=False,
            break_on_hyphens=False,
        )
        if not chunks:
            chunks = [line]

        # If a token still exceeds width (no spaces), hard-wrap it.
        # Method signatures should stay semantically intact: avoid splitting
        # identifiers like get_completed_stages into broken fragments.
        for chunk in chunks:
            if len(chunk) <= max_chars:
                wrapped.append(chunk)
                continue
            if label_kind == "methods" or _is_method_signature_line(chunk):
                wrapped.append(chunk)
                continue
            start = 0
            while start < len(chunk):
                wrapped.append(chunk[start : start + max_chars])
                start += max_chars

    while wrapped and not wrapped[0]:
        wrapped.pop(0)
    while wrapped and not wrapped[-1]:
        wrapped.pop()
    return wrapped


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


def _build_fallback_text(
    fo: ET.Element, label_kind: str = "generic"
) -> ET.Element | None:
    text_lines = _extract_text_lines(fo)
    if not text_lines:
        return None

    width = _parse_float(fo.attrib.get("width"))
    height = _parse_float(fo.attrib.get("height"))
    if width <= 0.0 and height <= 0.0:
        return None

    x = _parse_float(fo.attrib.get("x"))
    y = _parse_float(fo.attrib.get("y"))

    center_x = x + width / 2.0
    font_size = 14.0
    if label_kind == "methods":
        # Keep classDiagram method signatures on a single fallback line.
        # Mermaid already sized the original foreignObject for the unwrapped
        # method text, and post-wrap fallback labels cause vertical overlap
        # because sibling method slots keep Mermaid's original 24px spacing.
        wrapped_lines = [
            _sanitize_label_line(line, label_kind=label_kind)
            for line in text_lines
            if _sanitize_label_line(line, label_kind=label_kind)
        ]
    else:
        max_chars = _estimate_wrap_chars(width=width, font_size=font_size)
        wrapped_lines = _wrap_label_lines(
            text_lines,
            max_chars=max_chars,
            label_kind=label_kind,
        )
    if not wrapped_lines:
        return None

    # Keep fallback labels compact even for oversized node descriptions.
    max_lines = 12
    if len(wrapped_lines) > max_lines:
        wrapped_lines = wrapped_lines[: max_lines - 1] + ["..."]

    line_height = max(font_size * 1.2, 10.0)
    total_span = (len(wrapped_lines) - 1) * line_height
    first_line_y = y + (height - total_span) / 2.0

    text_elem = ET.Element(f"{{{SVG_NS}}}text")
    text_elem.set("x", _fmt_float(center_x))
    text_elem.set("y", _fmt_float(first_line_y))
    text_elem.set("text-anchor", "middle")
    text_elem.set("xml:space", "preserve")

    cls = fo.attrib.get("class", "").strip()
    text_elem.set("class", f"{cls} fo-fallback".strip())

    transform = fo.attrib.get("transform")
    if transform:
        text_elem.set("transform", transform)

    for idx, line in enumerate(wrapped_lines):
        tspan = ET.Element(f"{{{SVG_NS}}}tspan")
        tspan.set("x", _fmt_float(center_x))
        if idx > 0:
            tspan.set("dy", _fmt_float(line_height))
        tspan.text = line
        text_elem.append(tspan)

    return text_elem


def add_fallbacks(
    path: Path,
    *,
    write: bool = True,
    require_repo: bool = True,
) -> int:
    safe_path = _ensure_repo_path(path) if require_repo else path.resolve()
    tree = ET.parse(safe_path)
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

    parent_map = {child: parent for parent in root.iter() for child in parent}

    for parent in root.iter():
        children = list(parent)
        for idx, child in enumerate(children):
            if _local_name(child.tag) != "foreignObject":
                continue

            if idx > 0 and _is_fallback_text(children[idx - 1]):
                parent.remove(children[idx - 1])

            label_kind = _detect_label_kind(parent, parent_map)
            fallback = _build_fallback_text(child, label_kind=label_kind)
            if fallback is None:
                continue

            live_children = list(parent)
            child_index = live_children.index(child)
            parent.insert(child_index, fallback)
            inserted += 1

    if write and (inserted > 0 or removed_empty_edge_labels > 0):
        tree.write(safe_path, encoding="utf-8", xml_declaration=False)

    return inserted + removed_empty_edge_labels


def collect_svg_files(files: list[Path] | None, dirs: list[Path] | None) -> list[Path]:
    if files:
        return [_ensure_repo_path(path) for path in files]
    if dirs:
        selected: list[Path] = []
        for d in dirs:
            d = _ensure_repo_path(d)
            if d.is_dir():
                selected.extend(sorted(d.glob("*.svg")))
        return selected
    result: list[Path] = []
    for d in SVG_DIRS:
        if d.is_dir():
            result.extend(sorted(d.glob("*.svg")))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add fallback SVG text for Mermaid foreignObject labels.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--check", action="store_true", help="Exit 1 if fallback insertion needed"
    )
    group.add_argument("--fix", action="store_true", help="Write changes in place")
    group.add_argument("--dry-run", action="store_true", help="Show what would change")
    parser.add_argument(
        "-f", "--file", type=Path, action="append", help="Specific SVG file(s)"
    )
    parser.add_argument(
        "--dir", type=Path, action="append", help="Specific directory(ies)"
    )
    return parser.parse_args()


def process_files(files: list[Path], mode: str) -> int:
    changed = 0
    for path in files:
        safe_path = _ensure_repo_path(path)
        inserted = add_fallbacks(safe_path, write=mode == "fix")
        if inserted == 0:
            continue
        changed += 1

        if mode == "check":
            print(f"! {safe_path} (needs fallback text, +{inserted})")
        elif mode == "dry-run":
            print(f"~ {safe_path} (would add fallback text +{inserted})")
        else:
            print(f"+ {safe_path} (added fallback text +{inserted})")

    return changed


def main() -> int:
    args = parse_args()
    mode = "check" if args.check else ("dry-run" if args.dry_run else "fix")
    files = collect_svg_files(args.file, args.dir)

    if not files:
        print("No SVG files found.")
        return 0

    changed = process_files(files, mode)

    if mode == "check" and changed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
