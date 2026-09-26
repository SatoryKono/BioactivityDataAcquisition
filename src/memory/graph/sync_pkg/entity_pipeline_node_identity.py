"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.provider_pipeline_index_entries import (
    _provider_pipeline_index_entries,
)

__all__ = [
    "_entity_pipeline_node_identity",
    "_provider_pipeline_test_index",
]


def _entity_pipeline_node_identity(node: GraphNode) -> tuple[str, str] | None:
    if (
        node.key.label != "pipeline_surface"
        or node.properties.get("pipeline_kind") != "entity"
    ):
        return None
    return str(node.properties.get("provider")), str(node.properties.get("entity"))


def _provider_pipeline_test_index(snapshot: GraphSnapshot) -> dict[str, list[NodeKey]]:
    provider_pipeline_index: dict[str, list[NodeKey]] = {}
    for provider, node_key in _provider_pipeline_index_entries(snapshot):
        provider_pipeline_index.setdefault(provider, []).append(node_key)
    return provider_pipeline_index
