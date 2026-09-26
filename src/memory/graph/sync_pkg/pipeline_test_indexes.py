"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.entity_pipeline_node_identity import (
    _provider_pipeline_test_index,
)
from memory.graph.sync_pkg.entity_pipeline_test_index import _entity_pipeline_test_index
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_pipeline_test_indexes",
]


def _pipeline_test_indexes(
    snapshot: GraphSnapshot,
) -> tuple[dict[tuple[str, str], NodeKey], dict[str, list[NodeKey]]]:
    return _entity_pipeline_test_index(snapshot), _provider_pipeline_test_index(
        snapshot
    )
