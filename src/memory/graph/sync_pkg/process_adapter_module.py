"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _is_ignored_repo_path, _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_adapter_impl_surface import (
    _add_adapter_impl_surface,
    _add_adapter_module_surface,
    _link_adapter_ports,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import _imported_port_surfaces
from memory.graph.sync_pkg.python_paths import INIT_PY

__all__ = [
    "_add_adapter_package_impls",
    "_add_adapter_package_surface",
    "_process_adapter_module",
]


def _process_adapter_module(
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
) -> None:
    adapter = _add_adapter_module_surface(
        snapshot,
        root,
        project,
        adapter_family,
        child,
        today,
    )
    adapter_nodes[child.stem] = adapter
    imported_ports = _imported_port_surfaces(
        child, port_module_surfaces, port_symbol_index
    )
    _link_adapter_ports(
        snapshot, adapter, imported_ports, port_names, provenance="impact_adapters"
    )


def _add_adapter_package_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    adapter_family: NodeKey,
    child: Path,
    today: str,
) -> NodeKey:
    relative_path = _rel_path(root, child)
    surface_name = relative_path.replace("/", ".").removeprefix("src.")
    adapter = snapshot.add_node(
        "adapter_surface",
        surface_name,
        summary=f"Immediate adapter package surface `{surface_name}`.",
        source_path=relative_path,
        source_kind="adapter_package",
        adapter_kind="package",
        granularity="immediate_child",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_ADAPTER", adapter, provenance="impact_adapters")
    if adapter_family in snapshot.nodes:
        snapshot.add_relation(
            adapter_family, "CONTAINS", adapter, provenance="impact_adapters"
        )
    return adapter


def _add_adapter_package_impls(
    snapshot: GraphSnapshot,
    root: Path,
    adapter: NodeKey,
    child: Path,
    port_module_surfaces: dict[str, set[str]],
    port_symbol_index: dict[str, dict[str, str]],
    port_names: set[str],
    today: str,
    *,
    fine_grained_enabled: bool,
) -> set[str]:
    imported_ports: set[str] = set()
    for module_path in sorted(child.rglob("*.py")):
        if _is_ignored_repo_path(module_path):
            continue
        module_ports = _imported_port_surfaces(
            module_path, port_module_surfaces, port_symbol_index
        )
        if fine_grained_enabled and module_path.name != INIT_PY:
            impl_node = _add_adapter_impl_surface(
                snapshot, root, adapter, module_path, today
            )
            _link_adapter_ports(
                snapshot,
                impl_node,
                module_ports,
                port_names,
                provenance="impact_adapter_impls",
            )
        imported_ports.update(module_ports)
    return imported_ports
