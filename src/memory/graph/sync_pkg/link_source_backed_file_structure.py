"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_source_backed_node_structure import (
    _link_source_backed_node_structure,
)
from memory.graph.sync_pkg.source_backed_path_kind import (
    _source_backed_file_structure_labels,
)

__all__ = [
    "_link_source_backed_file_structure",
]


def _link_source_backed_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    source_backed_labels = _source_backed_file_structure_labels()
    path_kind_cache: dict[str, str | None] = {}
    for node in tuple(snapshot.nodes.values()):
        _link_source_backed_node_structure(
            snapshot,
            root,
            node,
            source_backed_labels=source_backed_labels,
            path_kind_cache=path_kind_cache,
            today=today,
            zone_roots=zone_roots,
            config=config,
        )
