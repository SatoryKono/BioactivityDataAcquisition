"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_adapter_impl_surface import _link_adapter_ports
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.process_adapter_module import (
    _add_adapter_package_impls,
    _add_adapter_package_surface,
)

__all__ = [
    "_process_adapter_package",
]


def _process_adapter_package(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    child: Path,
    *,
    adapter_family: NodeKey,
    adapter_nodes: dict[str, NodeKey],
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    fine_grained_enabled: bool,
) -> None:
    adapter = _add_adapter_package_surface(
        snapshot,
        root,
        project,
        adapter_family,
        child,
        today,
    )
    adapter_nodes[child.name] = adapter
    provider_key = NodeKey("provider_surface", child.name)
    if provider_key in snapshot.nodes:
        snapshot.add_relation(
            provider_key, "PROVIDES", adapter, provenance="impact_adapters"
        )
    imported_ports = _add_adapter_package_impls(
        snapshot,
        root,
        adapter,
        child,
        port_module_surfaces,
        port_symbol_index,
        port_names,
        today,
        fine_grained_enabled=fine_grained_enabled,
    )
    _link_adapter_ports(
        snapshot, adapter, imported_ports, port_names, provenance="impact_adapters"
    )
