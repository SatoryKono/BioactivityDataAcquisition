"""Graph-shaping helpers for lineage inspection."""

from __future__ import annotations

from bioetl.application.services.lineage.lineage_inspection_results import (
    LineageNodeRelationResult,
)
from bioetl.domain.lineage import (
    LineageEdgeType,
    LineageGraphFragment,
    LineageNodeRef,
    LineageNodeType,
)


def dedupe_nodes(nodes: list[LineageNodeRef]) -> tuple[LineageNodeRef, ...]:
    """Deduplicate nodes by canonical identifier while preserving order."""
    unique: dict[str, LineageNodeRef] = {}
    for node in nodes:
        unique.setdefault(node.node_id, node)
    return tuple(unique.values())


def dedupe_relations(
    relations: list[LineageNodeRelationResult],
) -> tuple[LineageNodeRelationResult, ...]:
    """Deduplicate relations by fragment, edge semantics, and related node id."""
    unique: dict[tuple[str, str, str, str | None], LineageNodeRelationResult] = {}
    for relation in relations:
        key = (
            relation.fragment_id,
            relation.edge_type,
            relation.node.node_id,
            relation.stored_fragment_id,
        )
        unique.setdefault(key, relation)
    return tuple(unique.values())


def relation_for_edge(
    *,
    fragment: LineageGraphFragment,
    edge_type: str,
    node: LineageNodeRef,
) -> LineageNodeRelationResult:
    """Build one canonical relation payload for trace results."""
    return LineageNodeRelationResult(
        fragment_id=fragment.fragment_id,
        stored_fragment_id=fragment.stored_fragment_id,
        edge_type=edge_type,
        node=node,
    )


def collect_nodes_by_type(
    *,
    fragments: tuple[LineageGraphFragment, ...],
    node_type: LineageNodeType,
) -> tuple[LineageNodeRef, ...]:
    """Collect nodes of one type across all fragments."""
    return dedupe_nodes(
        [
            node
            for fragment in fragments
            for node in fragment.nodes
            if node.node_type is node_type
        ]
    )


def resolve_produced_nodes(
    *,
    fragments: tuple[LineageGraphFragment, ...],
    node_type: LineageNodeType,
) -> tuple[LineageNodeRef, ...]:
    """Collect produced output nodes of one type across all fragments."""
    nodes: list[LineageNodeRef] = []
    for fragment in fragments:
        node_index = {node.node_id: node for node in fragment.nodes}
        for edge in fragment.edges:
            if edge.edge_type is not LineageEdgeType.PRODUCED_BY:
                continue
            node = node_index.get(edge.source.node_id, edge.source)
            if node.node_type is node_type:
                nodes.append(node)
    return dedupe_nodes(nodes)


__all__ = [
    "collect_nodes_by_type",
    "dedupe_relations",
    "relation_for_edge",
    "resolve_produced_nodes",
]
