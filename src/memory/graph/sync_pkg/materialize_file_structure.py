"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.file_structure_zone_roots import _add_file_structure_zones
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_source_backed_file_node import (
    _link_relation_backed_file_structure,
)
from memory.graph.sync_pkg.link_source_backed_file_structure import (
    _link_source_backed_file_structure,
)

__all__ = [
    "_materialize_file_structure",
]


def _materialize_file_structure(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    _add_file_structure_zones(snapshot, root, project, today, zone_roots, config)
    _link_source_backed_file_structure(snapshot, root, today, zone_roots, config)
    _link_relation_backed_file_structure(snapshot, root, config)
