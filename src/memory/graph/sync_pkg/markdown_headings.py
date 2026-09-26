"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterator

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.docs_reference_exact_candidates import (
    _docs_reference_exact_candidates,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_markdown_headings",
    "_resolve_docs_reference_target",
]


def _markdown_headings(text: str) -> Iterator[tuple[int, str]]:
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        stripped = line.lstrip(" \t")
        leading_indent = len(line) - len(stripped)
        if leading_indent > 3 or not stripped.startswith("#"):
            offset += len(raw_line)
            continue

        level = len(stripped) - len(stripped.lstrip("#"))
        if level < 1 or level > 6:
            offset += len(raw_line)
            continue

        if len(stripped) <= level or stripped[level] not in {" ", "\t"}:
            offset += len(raw_line)
            continue

        title = stripped[level:].strip()
        if title:
            yield offset, title
        offset += len(raw_line)


def _resolve_docs_reference_target(
    snapshot: GraphSnapshot,
    ref: str,
) -> tuple[NodeKey | None, str, str]:
    for candidate in _docs_reference_exact_candidates(ref):
        if candidate in snapshot.nodes:
            return candidate, "direct_path", "high"

    for node in tuple(snapshot.nodes.values()):
        source_path = node.properties.get("source_path")
        if isinstance(source_path, str) and source_path == ref:
            return node.key, "source_path_match", "medium"
    return None, "unresolved", "low"
