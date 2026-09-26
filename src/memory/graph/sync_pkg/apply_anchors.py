"""Targeted-apply anchor checks extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.live_queries import _live_managed_node_counts
from memory.graph.sync_pkg.neo4j_statements import (
    DEFAULT_INGEST_WAVE,
    DEFAULT_MANAGED_BY,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

if TYPE_CHECKING:
    from memory.graph.sync_pkg._core import GraphSnapshot

__all__ = [
    "_anchor_count_rows",
    "_ensure_targeted_apply_prerequisites",
    "_missing_anchor_keys_in_chunk",
    "_missing_anchor_keys_message",
    "_missing_anchor_labels",
    "_missing_anchor_labels_message",
    "_missing_managed_anchor_keys",
    "_targeted_apply_external_anchor_keys",
    "_targeted_apply_required_anchor_labels",
]


def _targeted_apply_required_anchor_labels(snapshot: GraphSnapshot) -> tuple[str, ...]:
    present_labels = {node.key.label for node in snapshot.nodes.values()}
    required_labels = {
        relation.source.label
        for relation in snapshot.relations.values()
        if relation.source.label not in present_labels
    }
    required_labels |= {
        relation.target.label
        for relation in snapshot.relations.values()
        if relation.target.label not in present_labels
    }
    return tuple(sorted(required_labels))


def _targeted_apply_external_anchor_keys(
    snapshot: GraphSnapshot,
) -> tuple[NodeKey, ...]:
    present_keys = set(snapshot.nodes)
    external_anchor_keys: set[NodeKey] = set()
    for relation in snapshot.relations.values():
        if relation.source not in present_keys:
            external_anchor_keys.add(relation.source)
        if relation.target not in present_keys:
            external_anchor_keys.add(relation.target)
    return tuple(sorted(external_anchor_keys, key=lambda key: (key.label, key.name)))


def _missing_managed_anchor_keys(
    client: Neo4jHttpClient,
    anchor_keys: tuple[NodeKey, ...],
    *,
    context: str,
) -> tuple[NodeKey, ...]:
    if not anchor_keys:
        return ()

    missing_keys: list[NodeKey] = []
    chunk_size = 250
    for start in range(0, len(anchor_keys), chunk_size):
        chunk = anchor_keys[start : start + chunk_size]
        missing_keys.extend(
            _missing_anchor_keys_in_chunk(client, chunk, context=context)
        )
    return tuple(missing_keys)


def _missing_anchor_keys_in_chunk(
    client: Neo4jHttpClient,
    chunk: tuple[NodeKey, ...],
    *,
    context: str,
) -> list[NodeKey]:
    rows = client.query(
        (
            "UNWIND $anchors AS anchor "
            "OPTIONAL MATCH (n) "
            "WHERE anchor.label IN labels(n) "
            "AND n.name = anchor.name "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "RETURN anchor.label AS label, anchor.name AS name, count(n) AS count "
            "ORDER BY label, name"
        ),
        {
            "anchors": [{"label": key.label, "name": key.name} for key in chunk],
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context=context,
    )
    live_counts = _anchor_count_rows(rows)
    return [key for key in chunk if live_counts.get(key, 0) == 0]


def _anchor_count_rows(rows: list[dict[str, JsonValue]]) -> dict[NodeKey, int]:
    return {
        NodeKey(str(row["label"]), str(row["name"])): _coerce_int(row["count"])
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("name"), str)
        and isinstance(row.get("count"), (int, float))
    }


def _ensure_targeted_apply_prerequisites(
    client: Neo4jHttpClient,
    snapshot: GraphSnapshot,
    *,
    mode_description: str,
) -> None:
    required_anchor_labels = _targeted_apply_required_anchor_labels(snapshot)
    if not required_anchor_labels:
        return
    live_anchor_counts = _live_managed_node_counts(
        client,
        required_anchor_labels,
        context=f"{mode_description} prerequisite anchor check",
    )
    missing_labels = _missing_anchor_labels(required_anchor_labels, live_anchor_counts)
    if missing_labels:
        raise RuntimeError(
            _missing_anchor_labels_message(mode_description, missing_labels)
        )
    external_anchor_keys = _targeted_apply_external_anchor_keys(snapshot)
    missing_anchor_keys = _missing_managed_anchor_keys(
        client,
        external_anchor_keys,
        context=f"{mode_description} prerequisite anchor node check",
    )
    if missing_anchor_keys:
        raise RuntimeError(
            _missing_anchor_keys_message(mode_description, missing_anchor_keys)
        )


def _missing_anchor_labels(
    required_anchor_labels: tuple[str, ...],
    live_anchor_counts: dict[str, int],
) -> list[str]:
    return [
        label
        for label in required_anchor_labels
        if live_anchor_counts.get(label, 0) == 0
    ]


def _missing_anchor_labels_message(
    mode_description: str,
    missing_labels: list[str],
) -> str:
    missing_summary = ", ".join(f"`{label}`" for label in missing_labels)
    return (
        f"{mode_description} requires pre-existing managed anchor labels in the live graph, "
        f"but these labels are missing or empty: {missing_summary}. "
        "Run a base sync first (for example `python -m scripts.memory sync --apply --prune-stale`)."
    )


def _missing_anchor_keys_message(
    mode_description: str,
    missing_anchor_keys: tuple[NodeKey, ...],
) -> str:
    sample = ", ".join(f"`{key.label}:{key.name}`" for key in missing_anchor_keys[:10])
    remainder = len(missing_anchor_keys) - min(len(missing_anchor_keys), 10)
    remainder_suffix = f" and {remainder} more" if remainder > 0 else ""
    return (
        f"{mode_description} requires pre-existing managed anchor nodes in the live graph, "
        f"but these nodes are missing: {sample}{remainder_suffix}. "
        "Run a base sync first (for example `python -m scripts.memory sync --apply --prune-stale`)."
    )
