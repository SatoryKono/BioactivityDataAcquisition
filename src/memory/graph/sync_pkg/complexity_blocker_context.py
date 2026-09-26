"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_entity_pipeline_surfaces import (
    _add_composite_pipeline_surfaces,
    _add_entity_pipeline_surfaces,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot

__all__ = [
    "_add_pipeline_surfaces",
    "_complexity_blocker_context",
]


def _complexity_blocker_context(
    node: GraphNode,
    *,
    blocked_by_current_cycle: bool,
) -> dict[str, object]:
    if not blocked_by_current_cycle:
        return {"target_name": None, "score": None, "wip_markers": None}
    return {
        "target_name": node.key.name,
        "score": node.properties.get("current_cycle_score"),
        "wip_markers": node.properties.get("current_cycle_wip_markers"),
    }


def _add_pipeline_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    contract_nodes: dict[str, NodeKey],
    adapter_nodes: dict[str, NodeKey],
) -> dict[str, NodeKey]:
    pipeline_nodes: dict[str, NodeKey] = {}
    _add_entity_pipeline_surfaces(
        snapshot,
        root,
        project,
        today,
        contract_nodes,
        adapter_nodes,
        pipeline_nodes,
    )
    _add_composite_pipeline_surfaces(
        snapshot,
        root,
        project,
        today,
        pipeline_nodes,
    )
    return pipeline_nodes
