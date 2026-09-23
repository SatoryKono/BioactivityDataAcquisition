"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.impact_analysis_context import _impact_analysis_context
from memory.graph.sync_pkg.mapping_io import _load_memory_mapping
from memory.graph.sync_pkg.run_impact_analysis_passes import _run_impact_analysis_passes

__all__ = [
    "_add_impact_analysis_surfaces",
]


def _add_impact_analysis_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    port_nodes, adapter_nodes, contract_nodes, pipeline_nodes = (
        _impact_analysis_context(
            snapshot,
            root,
            project,
            today,
            memory_mapping,
        )
    )
    _run_impact_analysis_passes(
        snapshot,
        root,
        project,
        today,
        memory_mapping=memory_mapping,
        port_nodes=port_nodes,
        adapter_nodes=adapter_nodes,
        contract_nodes=contract_nodes,
        pipeline_nodes=pipeline_nodes,
    )
