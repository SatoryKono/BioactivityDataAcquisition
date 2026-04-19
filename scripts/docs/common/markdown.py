"""Shared markdown helpers for docs tooling."""

from __future__ import annotations

import re
from pathlib import Path

MD_PATH_RE = re.compile(r"[A-Za-z0-9_./-]{1,512}\.md\b")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((?!https?://|mailto:)([^)#]+)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
PYTHON_FENCE_START_RE = re.compile(r"^\s*```(?:python|py|python3)\b", re.IGNORECASE)
FENCE_END_RE = re.compile(r"^\s*```")


def extract_md_heading(line: str) -> str | None:
    """Return markdown heading text when *line* is an ATX heading."""
    index = 0
    length = len(line)

    while index < length and index < 3 and line[index] in {" ", "\t"}:
        index += 1

    hash_start = index
    while index < length and line[index] == "#" and (index - hash_start) < 6:
        index += 1

    hash_count = index - hash_start
    if hash_count == 0 or (index < length and line[index] == "#"):
        return None

    space_start = index
    while index < length and line[index] in {" ", "\t"}:
        index += 1
    if index == space_start:
        return None

    heading = line[index:].strip().strip("#").strip()
    return heading or None


def load_nav_docs(mkdocs_file: Path) -> set[str]:
    """Return markdown docs referenced by MkDocs navigation."""
    text = mkdocs_file.read_text(encoding="utf-8", errors="replace")
    return set(MD_PATH_RE.findall(text))
