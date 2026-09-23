"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.classify_silver_storage_fields import (
    _classify_gold_storage_fields,
    _classify_silver_storage_fields,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_classify_projected_storage_fields",
    "_entity_storage_promotion_pairs",
    "_link_storage_layer_promotion",
]


def _entity_storage_promotion_pairs(
    layer_nodes: dict[str, NodeKey],
    *,
    bronze_fields: dict[str, NodeKey],
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> tuple[tuple[str, str, dict[str, NodeKey], dict[str, NodeKey]], ...]:
    pairs: list[tuple[str, str, dict[str, NodeKey], dict[str, NodeKey]]] = []
    if "bronze" in layer_nodes and "silver" in layer_nodes:
        pairs.append(("bronze", "silver", bronze_fields, silver_fields))
    if "silver" in layer_nodes and "gold" in layer_nodes:
        pairs.append(("silver", "gold", silver_fields, gold_fields))
    return tuple(pairs)


def _link_storage_layer_promotion(
    snapshot: GraphSnapshot,
    source_layer: NodeKey,
    target_layer: NodeKey,
    source_fields: dict[str, NodeKey],
    target_fields: dict[str, NodeKey],
) -> None:
    snapshot.add_relation(
        source_layer, "PROMOTES_TO", target_layer, provenance="storage_surfaces"
    )
    for field_name, source_field in source_fields.items():
        target_field = target_fields.get(field_name)
        if target_field is not None:
            snapshot.add_relation(
                source_field,
                "PROMOTES_FIELD_TO",
                target_field,
                provenance="schema_fields",
            )


def _classify_projected_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    _classify_silver_storage_fields(snapshot, silver_fields, gold_fields)
    _classify_gold_storage_fields(snapshot, silver_fields, gold_fields)
