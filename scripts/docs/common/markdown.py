"""Shared markdown helpers for docs tooling."""

from __future__ import annotations

import re
from pathlib import Path

MD_PATH_RE = re.compile(r"[A-Za-z0-9_./-]{1,512}\.md\b")
MD_LINK_RE = re.compile(r"\[([^\]]*)\]\((?!https?://|mailto:)([^)#]+)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MD_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+([^\n]*\S)[ \t]*$")
PYTHON_FENCE_START_RE = re.compile(r"^\s*```(?:python|py|python3)\b", re.IGNORECASE)
FENCE_END_RE = re.compile(r"^\s*```")


def load_nav_docs(mkdocs_file: Path) -> set[str]:
    """Return markdown docs referenced by MkDocs navigation."""
    text = mkdocs_file.read_text(encoding="utf-8", errors="replace")
    return set(MD_PATH_RE.findall(text))
