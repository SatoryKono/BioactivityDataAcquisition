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


def _bundle_relative_path(path: Path) -> Path:
    safe_path = _safe_bundle_path(path)
    return safe_path.relative_to(DIAGRAM_ROOT.resolve())


def _normalize_bundle_relative_path(path: Path) -> Path:
    """Normalize and validate a DIAGRAM_ROOT-relative path."""
    if path.is_absolute():
        raise ValueError(f"expected bundle-relative path, got absolute path: {path}")

    normalized_parts: list[str] = []
    for part in path.parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise ValueError(f"refusing parent traversal path: {path}")
        normalized_parts.append(part)

    if not normalized_parts:
        raise ValueError("refusing empty bundle-relative path")
    return Path(*normalized_parts)


def _write_bundle_text(relative_path: Path, content: str) -> None:
    """Write bundle content via a DIAGRAM_ROOT-relative path."""
    safe_relative_path = _normalize_bundle_relative_path(relative_path)
    target_path = _safe_bundle_path(DIAGRAM_ROOT / safe_relative_path)
    target_path.write_text(content, encoding="utf-8")


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
        heading_match = re.match(r"^## (.+)$", line)
        if heading_match:
            heading_text = heading_match.group(1).strip()

            # Normalise sub-headings to ###
            if heading_text in ("Описание", "Метаданные"):
                out.append(f"### {heading_text}")
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
                if any(
                    re.match(r"^## (?!Table of Contents)", existing_line)
                    for existing_line in out
                    if existing_line.startswith("## ")
                ):
                    # Remove trailing blank lines before inserting page break
                    while out and out[-1].strip() == "":
                        out.pop()
                    # Remove trailing --- separators
                    while out and out[-1].strip() == "---":
                        out.pop()
                    while out and out[-1].strip() == "":
                        out.pop()
                    out.append(PAGE_BREAK)
                    changes += 1

        out.append(line)
        i += 1

    if changes > 0:
        result = "\n".join(out) + "\n"
        _write_bundle_text(_bundle_relative_path(safe_path), result)
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
