"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphRelation, GraphSnapshot
from memory.graph.sync_pkg.port_surfaces import PORTS_MODULE_PREFIX

__all__ = [
    "_SnapshotRelationIndex",
    "_build_snapshot_relation_index",
    "_has_inbound_relation",
    "_has_outbound_relation",
    "_missing_required_population",
    "_nodes_with_label",
    "_port_and_contract_metadata_issues",
    "_protocol_class_ports",
    "_rich_contract_surfaces",
]


@dataclass(frozen=True)
class _SnapshotRelationIndex:
    outbound_by_source: dict[NodeKey, tuple[GraphRelation, ...]]
    inbound_by_target: dict[NodeKey, tuple[GraphRelation, ...]]


def _build_snapshot_relation_index(
    relations: tuple[GraphRelation, ...],
) -> _SnapshotRelationIndex:
    outbound: dict[NodeKey, list[GraphRelation]] = {}
    inbound: dict[NodeKey, list[GraphRelation]] = {}
    for relation in relations:
        outbound.setdefault(relation.source, []).append(relation)
        inbound.setdefault(relation.target, []).append(relation)
    return _SnapshotRelationIndex(
        outbound_by_source={key: tuple(value) for key, value in outbound.items()},
        inbound_by_target={key: tuple(value) for key, value in inbound.items()},
    )


def _has_inbound_relation(
    relation_index: _SnapshotRelationIndex,
    key: NodeKey,
    relation_types: set[str],
    *,
    source_labels: set[str] | None = None,
) -> bool:
    return any(
        rel.target == key
        and rel.relation_type in relation_types
        and (source_labels is None or rel.source.label in source_labels)
        for rel in relation_index.inbound_by_target.get(key, ())
    )


def _has_outbound_relation(
    relation_index: _SnapshotRelationIndex,
    key: NodeKey,
    relation_types: set[str],
    *,
    target_labels: set[str] | None = None,
) -> bool:
    return any(
        rel.source == key
        and rel.relation_type in relation_types
        and (target_labels is None or rel.target.label in target_labels)
        for rel in relation_index.outbound_by_source.get(key, ())
    )


def _missing_required_population(
    counts: object,
    names: Iterable[str],
    kind: str,
) -> list[str]:
    if not isinstance(counts, dict):
        return [f"missing required {kind} population: {name}" for name in names]
    return [
        f"missing required {kind} population: {name}"
        for name in names
        if _coerce_int(counts.get(name, 0), 0) <= 0
    ]


def _nodes_with_label(snapshot: GraphSnapshot, label: str) -> list[GraphNode]:
    return [node for node in snapshot.nodes.values() if node.key.label == label]


def _protocol_class_ports(snapshot: GraphSnapshot) -> list[GraphNode]:
    return [
        node
        for node in _nodes_with_label(snapshot, "port_surface")
        if node.properties.get("granularity") == "protocol_class"
    ]


def _rich_contract_surfaces(snapshot: GraphSnapshot) -> list[GraphNode]:
    return [
        node
        for node in _nodes_with_label(snapshot, "contract_surface")
        if node.properties.get("dq_policy_ref")
        and node.properties.get("schema_classes")
    ]


def _port_and_contract_metadata_issues(snapshot: GraphSnapshot) -> list[str]:
    issues: list[str] = []
    if NodeKey("port_surface", PORTS_MODULE_PREFIX) not in snapshot.nodes:
        issues.append(f"missing {PORTS_MODULE_PREFIX} facade port surface")

    if not _protocol_class_ports(snapshot):
        issues.append("missing protocol-class port surfaces")

    if not _rich_contract_surfaces(snapshot):
        issues.append("missing rich contract metadata on contract surfaces")

    return issues
