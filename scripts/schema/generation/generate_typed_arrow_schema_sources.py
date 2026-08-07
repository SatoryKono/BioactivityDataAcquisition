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


def _skip_module_header(lines: list[str]) -> int:
    """Skip shebang, encoding, module docstring, and blank lines at top."""
    i = 0
    n = len(lines)
    if i < n and lines[i].startswith("#!"):
        i += 1
    if i < n and re.match(r"^#.*coding[:=]", lines[i]):
        i += 1
    # module docstring
    if i < n and (
        lines[i].lstrip().startswith('"""') or lines[i].lstrip().startswith("'''")
    ):
        quote = '"""' if '"""' in lines[i] else "'''"
        if lines[i].count(quote) >= 2 and lines[i].strip() != quote:
            i += 1
        else:
            i += 1
            while i < n and quote not in lines[i]:
                i += 1
            if i < n:
                i += 1
    while i < n and lines[i].strip() == "":
        i += 1
    return i


def _import_block_end(lines: list[str]) -> int:
    """Return index after future + import block (after module header)."""
    i = _skip_module_header(lines)
    n = len(lines)
    last_end = i
    # future must come first among imports
    while i < n:
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("from __future__"):
            last_end = i + 1
            i += 1
            continue
        if stripped.startswith(("import ", "from ")):
            if "(" in line and ")" not in line:
                j = i + 1
                while j < n and ")" not in lines[j]:
                    j += 1
                last_end = min(j + 1, n)
                i = last_end
                continue
            last_end = i + 1
            i += 1
            continue
        if stripped == "" or stripped.startswith("#"):
            # allow blank/comments only while still in import region
            # peek ahead: if next non-empty is import, continue
            k = i + 1
            while k < n and lines[k].strip() == "":
                k += 1
            if k < n and (
                lines[k].strip().startswith(("import ", "from "))
                or lines[k].strip().startswith("#")
            ):
                i = k
                continue
            break
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
