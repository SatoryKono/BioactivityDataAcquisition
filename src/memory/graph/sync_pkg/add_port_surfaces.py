"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_port_facade_surface import _add_port_facade_surface
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import _build_port_surface_catalog
from memory.graph.sync_pkg.register_protocol_port_surface import (
    _register_protocol_port_surface,
)

__all__ = [
    "_add_port_surfaces",
]


def _add_port_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
) -> set[NodeKey]:
    ports_root = root / "src" / "bioetl" / "domain" / "ports"
    if not ports_root.is_dir():
        return set()

    family = NodeKey("package_family", "domain/ports")
    port_nodes: set[NodeKey] = set()
    facade = _add_port_facade_surface(snapshot, project, family, today)
    port_nodes.add(facade)

    descriptors, _, _ = _build_port_surface_catalog(root)
    for descriptor in descriptors:
        _register_protocol_port_surface(
            snapshot,
            project,
            facade,
            family,
            descriptor,
            today,
            port_nodes=port_nodes,
        )
    return port_nodes
