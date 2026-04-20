#!/usr/bin/env python3
"""Fix page breaks in diagram Markdown bundles.

Ensures each diagram section (## Name) starts on a new page by inserting
both \\newpage (for pandoc DOCX) and <div style="page-break-before: always;">
(for wkhtmltopdf PDF) before each diagram heading.

Also normalises sub-headings: Описание/Метаданные should be ### not ##.
Removes old page-break-after divs.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from .diagram_paths import DIAGRAM_ROOT
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import DIAGRAM_ROOT

# Page break block that works for both DOCX (pandoc) and PDF (wkhtmltopdf)
PAGE_BREAK = '\n\\newpage\n\n<div style="page-break-before: always;"></div>\n'


def _safe_bundle_path(path: Path) -> Path:
    resolved_root = DIAGRAM_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to modify file outside {resolved_root}: {resolved_path}")
    return resolved_path


def _write_bundle_text(path: Path, content: str) -> None:
    """Write bundle content to a previously validated DIAGRAM_ROOT path."""
    path.write_text(content, encoding="utf-8")


def _heading_text(line: str) -> str | None:
    match = re.match(r"^## (.+)$", line)
    if match is None:
        return None
    return match.group(1).strip()


def _normalized_subheading(heading_text: str) -> str | None:
    if heading_text in ("Описание", "Метаданные"):
        return f"### {heading_text}"
    return None


def _is_diagram_heading(heading_text: str) -> bool:
    return heading_text not in {"Table of Contents", "Описание", "Метаданные"}


def _already_has_diagram_heading(lines: list[str]) -> bool:
    return any(
        re.match(r"^## (?!Table of Contents)", existing_line)
        for existing_line in lines
        if existing_line.startswith("## ")
    )


def _trim_trailing_pagebreak_context(lines: list[str]) -> None:
    while lines and lines[-1].strip() == "":
        lines.pop()
    while lines and lines[-1].strip() == "---":
        lines.pop()
    while lines and lines[-1].strip() == "":
        lines.pop()


def fix_bundle(md_path: Path) -> int:
    safe_path = _safe_bundle_path(md_path)
    text = safe_path.read_text(encoding="utf-8")

    # Skip files that already have \newpage markers
    if "\\newpage" in text:
        print(f"[SKIP] Already has \\newpage: {md_path.name}")
        return 0

    lines = text.splitlines()
    out: list[str] = []
    changes = 0
    first_diagram_heading_seen = False
    is_toc_or_header = True  # Skip page breaks before TOC/header area

    i = 0
    while i < len(lines):
        line = lines[i]

        # Remove old page-break-after divs
        if "page-break-after" in line:
            i += 1
            changes += 1
            continue

        # Detect diagram headings (## name, but not ## Table of Contents, ## Описание, ## Метаданные)
        heading_text = _heading_text(line)
        if heading_text is not None:
            normalized_subheading = _normalized_subheading(heading_text)

            # Normalise sub-headings to ###
            if normalized_subheading is not None:
                out.append(normalized_subheading)
                i += 1
                changes += 1
                continue

            if heading_text == "Table of Contents":
                out.append(line)
                i += 1
                continue

            # This is a diagram heading
            if is_toc_or_header:
                is_toc_or_header = False
                first_diagram_heading_seen = True

            if first_diagram_heading_seen and not is_toc_or_header:
                # Insert page break before this heading (except very first)
                if _already_has_diagram_heading(out):
                    _trim_trailing_pagebreak_context(out)
                    out.append(PAGE_BREAK)
                    changes += 1

        out.append(line)
        i += 1

    if changes > 0:
        result = "\n".join(out) + "\n"
        _write_bundle_text(safe_path, result)
        print(f"[OK] Fixed {changes} items in {safe_path.name}")
    else:
        print(f"[SKIP] No changes needed: {safe_path.name}")
    return changes


def main() -> int:
    bundles_dir = DIAGRAM_ROOT / "bundles"
    if bundles_dir.exists():
        bundles = sorted(bundles_dir.glob("*.bundle.md"))
    else:
        bundles = sorted(DIAGRAM_ROOT.glob("*-with-descriptions.md"))
    if not bundles:
        print("[ERROR] No bundles found")
        return 1

    total = 0
    for b in bundles:
        total += fix_bundle(b)

    print(f"[INFO] Total changes: {total} across {len(bundles)} bundles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
