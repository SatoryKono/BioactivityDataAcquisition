#!/usr/bin/env python3
"""Rewrite Silver schema modules to use arrow_typed wrappers (PD7-4 / #7083).

Replaces common ``pa.field`` / ``pa.string`` / … call sites with typed helpers
from ``bioetl.infrastructure.arrow_typed`` so basedpyright stops reporting
unknown member/type noise on schema sources.

Usage:
    python scripts/schema/generation/generate_typed_arrow_schema_sources.py
    python scripts/schema/generation/generate_typed_arrow_schema_sources.py --check
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "src" / "bioetl" / "infrastructure" / "schemas"

TARGETS = [
    "silver_chembl_core.py",
    "silver_chembl_extended.py",
    "silver_compounds.py",
    "silver_publication_field_blocks.py",
    "silver_common_field_blocks.py",
    "silver_publications.py",
    "silver_chembl.py",
]

IMPORT_LINE = "from bioetl.infrastructure import arrow_typed as _ta\n"

REPLACEMENTS: list[tuple[str, str]] = [
    (r"\bpa\.timestamp\b", "_ta.timestamp"),
    (r"\bpa\.float64\b", "_ta.float64"),
    (r"\bpa\.string\b", "_ta.string"),
    (r"\bpa\.int64\b", "_ta.int64"),
    (r"\bpa\.int32\b", "_ta.int32"),
    (r"\bpa\.bool_\b", "_ta.bool_"),
    (r"\bpa\.null\b", "_ta.null"),
    (r"\bpa\.list_\b", "_ta.list_"),
    (r"\bpa\.struct\b", "_ta.struct"),
    (r"\bpa\.schema\b", "_ta.schema"),
    (r"\bpa\.field\b", "_ta.field"),
]


def _module_docstring_end(lines: list[str], start: int) -> int:
    if start >= len(lines):
        return start
    stripped = lines[start].lstrip()
    if not stripped.startswith(('"""', "'''")):
        return start
    quote = '"""' if stripped.startswith('"""') else "'''"
    if lines[start].count(quote) >= 2 and lines[start].strip() != quote:
        return start + 1
    index = start + 1
    while index < len(lines) and quote not in lines[index]:
        index += 1
    return min(index + 1, len(lines))


def _skip_blank_lines(lines: list[str], start: int) -> int:
    index = start
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _skip_module_header(lines: list[str]) -> int:
    """Skip shebang, encoding, module docstring, and blank lines at top."""
    index = 0
    if index < len(lines) and lines[index].startswith("#!"):
        index += 1
    if index < len(lines) and re.match(r"^#.*coding[:=]", lines[index]):
        index += 1
    index = _module_docstring_end(lines, index)
    return _skip_blank_lines(lines, index)


def _multiline_import_end(lines: list[str], start: int) -> int:
    if "(" not in lines[start] or ")" in lines[start]:
        return start + 1
    index = start + 1
    while index < len(lines) and ")" not in lines[index]:
        index += 1
    return min(index + 1, len(lines))


def _next_nonblank_line(lines: list[str], start: int) -> int:
    index = start
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index


def _import_block_end(lines: list[str]) -> int:
    """Return index after future + import block (after module header)."""
    index = _skip_module_header(lines)
    last_end = index
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if stripped.startswith("from __future__"):
            last_end = index + 1
            index += 1
            continue
        if stripped.startswith(("import ", "from ")):
            last_end = _multiline_import_end(lines, index)
            index = last_end
            continue
        if stripped == "" or stripped.startswith("#"):
            # allow blank/comments only while still in import region
            # peek ahead: if next non-empty is import, continue
            next_line = _next_nonblank_line(lines, index + 1)
            if next_line < len(lines) and (
                lines[next_line].strip().startswith(("import ", "from ", "#"))
            ):
                index = next_line
                continue
        break
    return last_end


def transform(text: str) -> str:
    if not re.search(r"\bpa\.(field|string|schema|int64|bool_)\b", text):
        return text

    lines = text.splitlines(keepends=True)
    if not any("arrow_typed as _ta" in ln for ln in lines):
        insert_at = _import_block_end(lines)
        block = IMPORT_LINE
        if insert_at > 0 and lines[insert_at - 1].strip() != "":
            block = "\n" + block
        if insert_at < len(lines) and lines[insert_at].strip() != "":
            block = block + "\n"
        lines.insert(insert_at, block)
        text = "".join(lines)

    for pattern, repl in REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any target would change (CI drift check).",
    )
    args = parser.parse_args(argv)
    changed: list[str] = []
    for name in TARGETS:
        path = SCHEMAS / name
        if not path.exists():
            print(f"[skip] missing {path}")
            continue
        original = path.read_text(encoding="utf-8")
        updated = transform(original)
        if updated != original:
            changed.append(name)
            if not args.check:
                path.write_text(updated, encoding="utf-8")
                print(f"[updated] {name}")
            else:
                print(f"[drift] {name}")
        else:
            print(f"[ok] {name}")
    if args.check and changed:
        print(
            f"[fail] {len(changed)} schema module(s) out of sync with arrow_typed generator"
        )
        return 1
    print(f"[done] changed={len(changed)} targets={len(TARGETS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
