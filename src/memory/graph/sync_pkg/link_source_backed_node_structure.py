"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.link_source_backed_file_node import (
    _link_source_backed_file_node,
)
from memory.graph.sync_pkg.python_paths import _is_excluded_file_structure_path
from memory.graph.sync_pkg.source_backed_path_kind import (
    _link_source_backed_directory_structure,
    _source_backed_path_kind,
)

__all__ = [
    "_link_source_backed_node_structure",
]


def _link_source_backed_node_structure(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    source_backed_labels: set[str],
    path_kind_cache: dict[str, str | None],
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    if node.key.label not in source_backed_labels:
        return
    source_path_value = node.properties.get("source_path")
    if not isinstance(source_path_value, str) or not source_path_value:
        return
    if _is_excluded_file_structure_path(source_path_value, config):
        return

    path_kind = _source_backed_path_kind(snapshot, source_path_value, path_kind_cache)
    if path_kind == "directory":
        _link_source_backed_directory_structure(
            snapshot,
            node.key,
            source_path_value=source_path_value,
            config=config,
        )
        return
    if path_kind != "file":
        return
    _link_source_backed_file_node(
        snapshot,
        root,
        node.key,
        root / source_path_value,
        source_path_value=source_path_value,
        today=today,
        zone_roots=zone_roots,
        config=config,
    )
