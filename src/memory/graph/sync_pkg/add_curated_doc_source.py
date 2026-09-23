"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_curated_doc_artifact import _link_curated_doc_artifact

__all__ = [
    "_add_curated_doc_source",
]


def _add_curated_doc_source(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    entry: dict[str, str],
) -> None:
    source_name = entry["name"]
    source_path = entry["path"]
    summary = entry["summary"]
    source_node = snapshot.add_node(
        "doc_source_surface",
        source_name,
        summary=summary,
        source_path=source_path,
        source_kind="doc_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_DOC_SOURCE_SURFACE", source_node, provenance="curated_docs"
    )
    _link_curated_doc_artifact(
        snapshot,
        root,
        source_node,
        source_path=source_path,
        summary=summary,
        today=today,
    )
