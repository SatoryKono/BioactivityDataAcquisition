"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_port_surfaces import _add_port_surfaces
from memory.graph.sync_pkg.complexity_blocker_context import _add_pipeline_surfaces
from memory.graph.sync_pkg.contract_registry_entries import _add_contract_surfaces
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.register_protocol_port_surface import _add_adapter_surfaces

__all__ = [
    "_impact_analysis_context",
]


def _impact_analysis_context(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    memory_mapping: dict[str, object],
) -> tuple[set[NodeKey], dict[str, NodeKey], dict[str, NodeKey], dict[str, NodeKey]]:
    port_nodes = _add_port_surfaces(snapshot, root, project, today)
    adapter_nodes = _add_adapter_surfaces(
        snapshot, root, project, today, port_nodes, memory_mapping
    )
    contract_nodes = _add_contract_surfaces(
        snapshot, root, project, today, memory_mapping
    )
    pipeline_nodes = _add_pipeline_surfaces(
        snapshot, root, project, today, contract_nodes, adapter_nodes
    )
    return port_nodes, adapter_nodes, contract_nodes, pipeline_nodes
