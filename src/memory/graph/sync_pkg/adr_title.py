"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.adr_constraint_candidates import _adr_constraint_candidates
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.markdown_headings import _markdown_headings
from memory.graph.sync_pkg.normalize_docs_repo_reference import (
    _markdown_heading_context,
)

__all__ = [
    "_adr_title",
    "_doc_reference_context",
    "_resolve_adr_constraint_target",
]


def _adr_title(adr_path: Path) -> str:
    text = _read_text(adr_path)
    for _offset, title in _markdown_headings(text):
        return title
    return adr_path.stem


def _resolve_adr_constraint_target(
    snapshot: GraphSnapshot, normalized_ref: str
) -> NodeKey | None:
    for candidate in _adr_constraint_candidates(normalized_ref):
        if candidate in snapshot.nodes:
            return candidate
    return None


def _doc_reference_context(
    text: str, offset: int
) -> tuple[str | None, str | None, int]:
    section_title, section_anchor = _markdown_heading_context(text, offset)
    line_number = text.count("\n", 0, offset) + 1
    return section_title, section_anchor, line_number
