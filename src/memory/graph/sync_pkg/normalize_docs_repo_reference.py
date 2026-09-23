"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalize_docs_glob_candidate
from memory.graph.sync_pkg.docs_reference_allowed_prefixes import (
    _DOCS_REFERENCE_ALLOWED_PREFIXES,
    _heading_anchor_slug,
    _trim_docs_reference_candidate,
)
from memory.graph.sync_pkg.markdown_headings import _markdown_headings

__all__ = [
    "_markdown_heading_context",
    "_normalize_docs_repo_reference",
]


def _normalize_docs_repo_reference(raw_ref: str) -> str | None:
    candidate = _trim_docs_reference_candidate(raw_ref)
    if not candidate:
        return None
    candidate = _normalize_docs_glob_candidate(candidate)
    candidate = candidate.rstrip("/")
    if candidate in {"README.md", "mkdocs.yml"}:
        return candidate
    if any(candidate.startswith(prefix) for prefix in _DOCS_REFERENCE_ALLOWED_PREFIXES):
        return candidate
    return None


def _markdown_heading_context(text: str, offset: int) -> tuple[str | None, str | None]:
    current_title: str | None = None
    current_anchor: str | None = None
    for line_start, title in _markdown_headings(text):
        if line_start > offset:
            break
        current_title = title
        current_anchor = _heading_anchor_slug(current_title)
    return current_title, current_anchor
