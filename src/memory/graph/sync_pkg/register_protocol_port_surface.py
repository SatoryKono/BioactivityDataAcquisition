"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey, PortSurfaceDescriptor
from memory.graph.sync_pkg.add_port_facade_surface import _add_protocol_port_surface
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import _build_port_surface_catalog
from memory.graph.sync_pkg.process_adapter_root_child import _process_adapter_root_child

__all__ = [
    "_add_adapter_surfaces",
    "_register_protocol_port_surface",
]


def _register_protocol_port_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    facade: NodeKey,
    family: NodeKey,
    descriptor: PortSurfaceDescriptor,
    today: str,
    *,
    port_nodes: set[NodeKey],
) -> None:
    port = _add_protocol_port_surface(
        snapshot,
        project,
        facade,
        family,
        descriptor,
        today,
    )
    port_nodes.add(port)


def _add_adapter_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    port_nodes: set[NodeKey],
    memory_mapping: dict[str, object],
) -> dict[str, NodeKey]:
    adapters_root = root / "src" / "bioetl" / "infrastructure" / "adapters"
    if not adapters_root.is_dir():
        return {}

    adapter_family = NodeKey("package_family", "infrastructure/adapters")
    port_names = {node.name for node in port_nodes}
    _, port_module_surfaces, port_symbol_index = _build_port_surface_catalog(root)
    adapter_nodes: dict[str, NodeKey] = {}
    adapter_mapping = memory_mapping.get("adapters")
    fine_grained_enabled = (
        bool(adapter_mapping.get("fine_grained_enabled", True))
        if isinstance(adapter_mapping, dict)
        else True
    )

    for child in sorted(adapters_root.iterdir()):
        _process_adapter_root_child(
            snapshot,
            root,
            project,
            today,
            child,
            adapter_family=adapter_family,
            adapter_nodes=adapter_nodes,
            port_module_surfaces=port_module_surfaces,
            port_symbol_index=port_symbol_index,
            port_names=port_names,
            fine_grained_enabled=fine_grained_enabled,
        )

    return adapter_nodes
