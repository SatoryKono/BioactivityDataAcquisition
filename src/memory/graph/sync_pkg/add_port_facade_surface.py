"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey, PortSurfaceDescriptor
from memory.graph.sync_pkg.default_batch_size import PORTS_FACADE_SOURCE_PATH
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import PORTS_MODULE_PREFIX
from memory.graph.sync_pkg.python_paths import INIT_PY

__all__ = [
    "_add_port_facade_surface",
    "_add_protocol_port_surface",
]


def _add_port_facade_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    family: NodeKey,
    today: str,
) -> NodeKey:
    facade = snapshot.add_node(
        "port_surface",
        PORTS_MODULE_PREFIX,
        summary="Canonical facade exporting stable domain port protocols.",
        source_path=f"src/bioetl/domain/ports/{INIT_PY}",
        source_kind="domain_port_facade",
        granularity="facade",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_PORT", facade, provenance="impact_ports")
    if family in snapshot.nodes:
        snapshot.add_relation(family, "CONTAINS", facade, provenance="impact_ports")
    facade_module = NodeKey("module_surface", PORTS_FACADE_SOURCE_PATH)
    if facade_module in snapshot.nodes:
        snapshot.add_relation(
            facade, "BACKED_BY", facade_module, provenance="impact_ports"
        )
    return facade


def _add_protocol_port_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    facade: NodeKey,
    family: NodeKey,
    descriptor: PortSurfaceDescriptor,
    today: str,
) -> NodeKey:
    port = snapshot.add_node(
        "port_surface",
        descriptor.surface_name,
        summary=f"Domain port protocol `{descriptor.class_name}`.",
        source_path=descriptor.source_path,
        source_kind="domain_port_protocol",
        port_name=descriptor.class_name,
        port_module=descriptor.module_name,
        granularity="protocol_class",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(project, "HAS_PORT", port, provenance="impact_ports")
    snapshot.add_relation(facade, "CONTAINS", port, provenance="impact_ports")
    if family in snapshot.nodes:
        snapshot.add_relation(family, "CONTAINS", port, provenance="impact_ports")
    module_key = NodeKey("module_surface", descriptor.source_path)
    if module_key in snapshot.nodes:
        snapshot.add_relation(port, "BACKED_BY", module_key, provenance="impact_ports")
    return port
