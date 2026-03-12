#!/usr/bin/env python3
"""Fix page breaks in *-with-descriptions.md bundles.

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

# Page break block that works for both DOCX (pandoc) and PDF (wkhtmltopdf)
PAGE_BREAK = (
    '\n\\newpage\n'
    '\n<div style="page-break-before: always;"></div>\n'
)


def fix_bundle(md_path: Path) -> int:
    text = md_path.read_text(encoding="utf-8")

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
        if 'page-break-after' in line:
            i += 1
            changes += 1
            continue

        # Detect diagram headings (## name, but not ## Table of Contents, ## Описание, ## Метаданные)
        heading_match = re.match(r'^## (.+)$', line)
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
                    re.match(r'^## (?!Table of Contents)', l)
                    for l in out
                    if l.startswith("## ")
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
        md_path.write_text(result, encoding="utf-8")
        print(f"[OK] Fixed {changes} items in {md_path.name}")
    else:
        print(f"[SKIP] No changes needed: {md_path.name}")
    return changes


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    mmd_dir = repo_root / "docs" / "02-architecture" / "mmd-diagrams"

    bundles = sorted(mmd_dir.glob("*-with-descriptions.md"))
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
