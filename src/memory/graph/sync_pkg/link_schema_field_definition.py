"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_schema_field_definition",
]


def _link_schema_field_definition(
    snapshot: GraphSnapshot,
    field_node: NodeKey,
    config_artifact: NodeKey,
) -> None:
    if config_artifact in snapshot.nodes:
        snapshot.add_relation(
            field_node, "DEFINED_BY", config_artifact, provenance="schema_fields"
        )
