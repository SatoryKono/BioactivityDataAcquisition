"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.entity_storage_promotion_pairs import (
    _classify_projected_storage_fields,
    _entity_storage_promotion_pairs,
    _link_storage_layer_promotion,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_entity_storage_promotions",
]


def _link_entity_storage_promotions(
    snapshot: GraphSnapshot,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    bronze_fields = field_nodes_by_layer.get("bronze", {})
    silver_fields = field_nodes_by_layer.get("silver", {})
    gold_fields = field_nodes_by_layer.get("gold", {})
    for (
        source_name,
        target_name,
        source_fields,
        target_fields,
    ) in _entity_storage_promotion_pairs(
        layer_nodes,
        bronze_fields=bronze_fields,
        silver_fields=silver_fields,
        gold_fields=gold_fields,
    ):
        _link_storage_layer_promotion(
            snapshot,
            layer_nodes[source_name],
            layer_nodes[target_name],
            source_fields,
            target_fields,
        )
    if "silver" in layer_nodes and "gold" in layer_nodes:
        _classify_projected_storage_fields(snapshot, silver_fields, gold_fields)
