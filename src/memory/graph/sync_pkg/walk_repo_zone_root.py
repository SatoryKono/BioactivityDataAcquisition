"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.walk_repo_zone_file_structure import (
    _walk_repo_zone_file_structure,
)

__all__ = [
    "_walk_repo_zone_root",
]


def _walk_repo_zone_root(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    zone: NodeKey,
    today: str,
    *,
    zone_name: str,
    relative_root: str,
    config: dict[str, object],
) -> None:
    zone_root = root / relative_root
    if not zone_root.is_dir():
        return
    _walk_repo_zone_file_structure(
        snapshot,
        root,
        project,
        zone,
        today,
        zone_name=zone_name,
        relative_root=relative_root,
        zone_root=zone_root,
        config=config,
    )
