"""Cypher statement builders extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Protocol

from memory.graph.sync_pkg._core_models import JsonScalar, JsonValue, NodeKey

__all__ = [
    "DEFAULT_INGEST_WAVE",
    "DEFAULT_MANAGED_BY",
    "_delete_managed_wave_nodes_statement",
    "_managed_properties",
    "_neo4j_property_value",
    "_node_statement",
    "_prune_legacy_unmanaged_nodes_statement",
    "_prune_stale_nodes_statement",
    "_prune_stale_relations_statement",
    "_relation_statement",
    "_reset_managed_relations_statement",
]

DEFAULT_INGEST_WAVE = "repo_sync_v1"
DEFAULT_MANAGED_BY = "neo4j_memory_sync"


class _NodeStatementSource(Protocol):
    key: NodeKey
    properties: dict[str, JsonValue]


class _RelationStatementSource(Protocol):
    source: NodeKey
    target: NodeKey
    relation_type: str
    properties: dict[str, JsonValue]


def _neo4j_property_value(value: JsonValue) -> JsonScalar | list[JsonScalar]:
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes):
        normalized_items: list[JsonScalar] = []
        for item in value:
            if isinstance(item, Mapping | Sequence) and not isinstance(
                item, str | bytes
            ):
                normalized_items.append(json.dumps(item, sort_keys=True))
            elif isinstance(item, str | int | float | bool) or item is None:
                normalized_items.append(item)
        return normalized_items
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def _managed_properties(
    properties: dict[str, JsonValue], sync_run: str
) -> dict[str, JsonValue]:
    managed: dict[str, JsonValue] = {
        key: _neo4j_property_value(value) for key, value in properties.items()
    }
    managed["managed_by"] = DEFAULT_MANAGED_BY
    managed["sync_run"] = sync_run
    managed.setdefault("ingest_wave", DEFAULT_INGEST_WAVE)
    return managed


def _node_statement(node: _NodeStatementSource, sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MERGE (n:`{node.key.label}` {{name: $name}}) SET n += $properties"
        ),
        "parameters": {
            "name": node.key.name,
            "properties": _managed_properties(node.properties, sync_run),
        },
    }


def _relation_statement(
    relation: _RelationStatementSource, sync_run: str
) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MATCH (a:`{relation.source.label}` {{name: $source_name}}) "
            f"MATCH (b:`{relation.target.label}` {{name: $target_name}}) "
            f"MERGE (a)-[r:`{relation.relation_type}`]->(b) "
            "SET r += $properties"
        ),
        "parameters": {
            "source_name": relation.source.name,
            "target_name": relation.target.name,
            "properties": _managed_properties(relation.properties, sync_run),
        },
    }


def _reset_managed_relations_statement(
    relation_types: list[str],
) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (a)-[r]->(b) "
            "WHERE type(r) IN $relation_types "
            "AND (r.managed_by = $managed_by "
            "OR (a.ingest_wave = $ingest_wave AND b.ingest_wave = $ingest_wave)) "
            "DELETE r"
        ),
        "parameters": {
            "relation_types": relation_types,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
    }


def _prune_stale_relations_statement(sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH ()-[r]->() "
            "WHERE (r.managed_by = $managed_by OR r.ingest_wave = $ingest_wave) "
            "AND coalesce(r.sync_run, '') <> $sync_run "
            "DELETE r"
        ),
        "parameters": {
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run,
        },
    }


def _prune_stale_nodes_statement(sync_run: str) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (n) "
            "WHERE n.ingest_wave = $ingest_wave "
            "AND coalesce(n.sync_run, '') <> $sync_run "
            "DETACH DELETE n"
        ),
        "parameters": {
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run,
        },
    }


def _delete_managed_wave_nodes_statement(
    label: str, limit: int
) -> dict[str, JsonValue]:
    return {
        "statement": (
            f"MATCH (n:`{label}`) "
            "WHERE n.ingest_wave = $ingest_wave "
            "AND coalesce(n.managed_by, $managed_by) = $managed_by "
            "WITH n LIMIT $limit "
            "DETACH DELETE n "
            "RETURN count(*) AS deleted"
        ),
        "parameters": {
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "managed_by": DEFAULT_MANAGED_BY,
            "limit": limit,
        },
    }


def _prune_legacy_unmanaged_nodes_statement(
    managed_labels: list[str],
) -> dict[str, JsonValue]:
    return {
        "statement": (
            "MATCH (n) "
            "WHERE any(label IN labels(n) WHERE label IN $managed_labels) "
            "AND coalesce(n.managed_by, '') = '' "
            "DETACH DELETE n"
        ),
        "parameters": {
            "managed_labels": managed_labels,
        },
    }
