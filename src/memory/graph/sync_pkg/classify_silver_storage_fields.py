"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_group_field_entries import (
    _composite_group_field_entries,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_classify_gold_storage_fields",
    "_classify_silver_storage_fields",
    "_composite_group_fields",
]


def _classify_silver_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    for field_name, silver_field in silver_fields.items():
        silver_node = snapshot.nodes.get(silver_field)
        if silver_node is None:
            continue
        gold_field = gold_fields.get(field_name)
        if gold_field is not None:
            snapshot.add_relation(
                silver_field,
                "PROMOTES_FIELD_TO",
                gold_field,
                provenance="schema_fields",
            )
            silver_node.properties["drift_classification"] = "projected_to_gold"
            continue
        silver_node.properties["drift_classification"] = "silver_only"


def _classify_gold_storage_fields(
    snapshot: GraphSnapshot,
    silver_fields: dict[str, NodeKey],
    gold_fields: dict[str, NodeKey],
) -> None:
    for field_name, gold_field in gold_fields.items():
        gold_node = snapshot.nodes.get(gold_field)
        if gold_node is None:
            continue
        gold_node.properties["drift_classification"] = (
            "promoted_from_silver" if field_name in silver_fields else "gold_only"
        )


def _composite_group_fields(merge_payload: dict[str, object]) -> list[tuple[str, str]]:
    group_fields: list[tuple[str, str]] = []
    column_groups = merge_payload.get("column_groups")
    if not isinstance(column_groups, list):
        return group_fields
    for item in column_groups:
        group_fields.extend(_composite_group_field_entries(item))
    return group_fields
