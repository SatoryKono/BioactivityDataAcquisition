"""Analysis source-text readers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import os
import queue
import threading
from pathlib import Path

from memory.graph.sync_pkg._core_convert import _read_text
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_contexts import SurfaceRelationIndexes
from memory.graph.sync_pkg.graph_snapshot import GraphRelation, GraphSnapshot

__all__ = [
    "ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS",
    "_analysis_read_source_text",
    "_build_surface_relation_indexes",
    "_read_analysis_source_text",
]

ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS = 2.0


def _build_surface_relation_indexes(snapshot: GraphSnapshot) -> SurfaceRelationIndexes:
    incoming: dict[NodeKey, list[GraphRelation]] = {}
    outgoing: dict[NodeKey, list[GraphRelation]] = {}
    declared_children: dict[NodeKey, list[NodeKey]] = {}
    for relation in snapshot.relations.values():
        incoming.setdefault(relation.target, []).append(relation)
        outgoing.setdefault(relation.source, []).append(relation)
        if relation.relation_type == "DECLARES":
            declared_children.setdefault(relation.source, []).append(relation.target)
    return SurfaceRelationIndexes(
        incoming=incoming,
        outgoing=outgoing,
        declared_children=declared_children,
    )


def _analysis_read_source_text(
    root: Path, relative_path: str, text_cache: dict[str, str]
) -> str:
    if relative_path not in text_cache:
        path = root / relative_path
        try:
            text_cache[relative_path] = _read_analysis_source_text(path).casefold()
        except (OSError, TimeoutError):
            text_cache[relative_path] = ""
    return text_cache[relative_path]


def _read_analysis_source_text(
    path: Path,
    *,
    timeout_seconds: float = ANALYSIS_SOURCE_READ_TIMEOUT_SECONDS,
    os_name: str = os.name,
) -> str:
    """Read optional source text for marker analysis without blocking Windows runs."""
    if os_name != "nt":
        return _read_text(path)

    result: queue.Queue[tuple[str, str | BaseException]] = queue.Queue(maxsize=1)

    def _read() -> None:
        try:
            result.put(("ok", _read_text(path)))
        except (OSError, UnicodeError, ValueError) as exc:  # pragma: no cover
            result.put(("error", exc))

    thread = threading.Thread(
        target=_read,
        name=f"memory-analysis-read:{path.name}",
        daemon=True,
    )
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        raise TimeoutError(f"Timed out reading analysis source text: {path}")

    status, payload = result.get_nowait()
    if status == "error":
        if isinstance(payload, BaseException):
            raise payload
        raise RuntimeError(str(payload))
    return str(payload)
