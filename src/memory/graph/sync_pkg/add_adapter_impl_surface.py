"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import _rel_path
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.python_paths import _python_surface_name

__all__ = [
    "_add_adapter_impl_surface",
    "_add_adapter_module_surface",
    "_link_adapter_ports",
]


def _add_adapter_impl_surface(
    snapshot: GraphSnapshot,
    root: Path,
    adapter: NodeKey,
    module_path: Path,
    today: str,
) -> NodeKey:
    impl_relative_path = _rel_path(root, module_path)
    impl_surface_name = _python_surface_name(impl_relative_path)
    impl_node = snapshot.add_node(
        "adapter_impl_surface",
        impl_surface_name,
        summary=f"Concrete adapter implementation `{impl_surface_name}`.",
        source_path=impl_relative_path,
        source_kind="adapter_impl_module",
        adapter_kind="implementation_module",
        granularity="concrete_module",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        adapter, "CONTAINS", impl_node, provenance="impact_adapter_impls"
    )
    impl_module_key = NodeKey("module_surface", impl_relative_path)
    if impl_module_key in snapshot.nodes:
        snapshot.add_relation(
            impl_node, "BACKED_BY", impl_module_key, provenance="impact_adapter_impls"
        )
    return impl_node


def _add_adapter_module_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    adapter_family: NodeKey,
    child: Path,
    today: str,
) -> NodeKey:
    relative_path = _rel_path(root, child)
    surface_name = _python_surface_name(relative_path)
    adapter = snapshot.add_node(
        "adapter_surface",
        surface_name,
        summary=f"Immediate adapter module surface `{surface_name}`.",
        source_path=relative_path,
        source_kind="adapter_module",
        adapter_kind="module",
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
    module_key = NodeKey("module_surface", relative_path)
    if module_key in snapshot.nodes:
        snapshot.add_relation(
            adapter, "BACKED_BY", module_key, provenance="impact_adapters"
        )
    return adapter


def _link_adapter_ports(
    snapshot: GraphSnapshot,
    source: NodeKey,
    imported_ports: set[str],
    port_names: set[str],
    *,
    provenance: str,
) -> None:
    for port_name in sorted(imported_ports):
        if port_name in port_names:
            snapshot.add_relation(
                source,
                "DEPENDS_ON",
                NodeKey("port_surface", port_name),
                provenance=provenance,
            )
