"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.entity_pipeline_node_identity import (
    _entity_pipeline_node_identity,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_entity_pipeline_test_index",
]


def _entity_pipeline_test_index(
    snapshot: GraphSnapshot,
) -> dict[tuple[str, str], NodeKey]:
    return {
        identity: node.key
        for node in snapshot.nodes.values()
        for identity in [_entity_pipeline_node_identity(node)]
        if identity is not None
    }
