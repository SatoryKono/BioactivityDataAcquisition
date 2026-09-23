"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _as_string_list
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_file_structure_zone import _add_file_structure_zone
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_file_structure_zones",
    "_file_structure_zone_roots",
]


def _file_structure_zone_roots(config: dict[str, object]) -> dict[str, tuple[str, ...]]:
    raw_zones = config.get("repo_zones")
    if not isinstance(raw_zones, dict):
        return {}
    return {
        str(name): tuple(_as_string_list(paths)) for name, paths in raw_zones.items()
    }


def _add_file_structure_zones(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    zone_roots: dict[str, tuple[str, ...]],
    config: dict[str, object],
) -> None:
    for zone_name, relative_roots in zone_roots.items():
        _add_file_structure_zone(
            snapshot,
            root,
            project,
            today,
            zone_name,
            relative_roots,
            config,
        )
