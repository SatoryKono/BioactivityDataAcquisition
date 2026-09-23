"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.provider_pipeline_index_key import (
    _provider_pipeline_index_key,
)

__all__ = [
    "_provider_pipeline_index_entries",
]


def _provider_pipeline_index_entries(
    snapshot: GraphSnapshot,
) -> tuple[tuple[str, NodeKey], ...]:
    return tuple(
        (provider, node.key)
        for node in snapshot.nodes.values()
        for provider in [_provider_pipeline_index_key(node)]
        if provider is not None
    )
