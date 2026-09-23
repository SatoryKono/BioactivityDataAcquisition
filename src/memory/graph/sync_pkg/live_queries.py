"""Live Neo4j audit queries extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.neo4j_statements import (
    DEFAULT_INGEST_WAVE,
    DEFAULT_MANAGED_BY,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

__all__ = [
    "_audit_live_summary",
    "_build_diff_entries",
    "_count_rows_by_key",
    "_live_managed_node_count",
    "_live_managed_node_counts",
    "_live_managed_relation_count",
    "_live_managed_relation_counts",
    "_live_managed_relation_rows",
    "_live_orphan_rows",
    "_live_repo_label_rows",
    "_live_scalar",
    "_live_unmanaged_repo_rows",
    "_managed_label_counts_from_rows",
    "_managed_label_summary_from_counts",
    "_managed_relation_counts_from_rows",
    "_managed_relation_summary_from_counts",
    "_managed_sync_run_clause",
    "_row_int_total",
    "_snapshot_count_map",
    "_snapshot_subset_count_map",
]


def _live_managed_node_count(client: Neo4jHttpClient, label: str) -> int:
    return _live_managed_node_counts(
        client,
        (label,),
        context=f"managed node count for label `{label}`",
    ).get(label, 0)


def _live_managed_relation_count(client: Neo4jHttpClient, relation_type: str) -> int:
    return _live_managed_relation_counts(
        client,
        (relation_type,),
        context=f"managed relation count for type `{relation_type}`",
    ).get(relation_type, 0)


def _managed_sync_run_clause(
    alias: str,
    sync_run: str | None,
) -> str:
    return f"AND coalesce({alias}.sync_run, '') = $sync_run " if sync_run else ""


def _count_rows_by_key(
    rows: list[dict[str, JsonValue]],
    keys: tuple[str, ...],
    key_field: str,
) -> dict[str, int]:
    counts = dict.fromkeys(keys, 0)
    for row in rows:
        key_value = row.get(key_field)
        count = row.get("count")
        if isinstance(key_value, str) and isinstance(count, (int, float)):
            counts[key_value] = _coerce_int(count)
    return counts


def _live_managed_node_counts(
    client: Neo4jHttpClient,
    labels: tuple[str, ...],
    *,
    context: str,
    sync_run: str | None = None,
) -> dict[str, int]:
    if not labels:
        return {}
    rows = client.query(
        (
            "UNWIND $labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            f"{_managed_sync_run_clause('n', sync_run)}"
            "RETURN label, count(n) AS count "
            "ORDER BY label"
        ),
        {
            "labels": list(labels),
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run or "",
        },
        context=context,
    )
    return _count_rows_by_key(rows, labels, "label")


def _live_managed_relation_counts(
    client: Neo4jHttpClient,
    relation_types: tuple[str, ...],
    *,
    context: str,
    sync_run: str | None = None,
) -> dict[str, int]:
    if not relation_types:
        return {}
    rows = client.query(
        (
            "UNWIND $relation_types AS relation_type "
            "OPTIONAL MATCH ()-[r]->() "
            "WHERE type(r) = relation_type "
            "AND coalesce(r.managed_by, '') = $managed_by "
            "AND coalesce(r.ingest_wave, '') = $ingest_wave "
            f"{_managed_sync_run_clause('r', sync_run)}"
            "RETURN relation_type, count(r) AS count "
            "ORDER BY relation_type"
        ),
        {
            "relation_types": list(relation_types),
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
            "sync_run": sync_run or "",
        },
        context=context,
    )
    return _count_rows_by_key(rows, relation_types, "relation_type")


def _build_diff_entries(
    snapshot_counts: dict[str, int], live_counts: dict[str, int]
) -> list[dict[str, JsonValue]]:
    entries: list[dict[str, JsonValue]] = []
    for name in sorted(set(snapshot_counts) | set(live_counts)):
        snapshot_value = snapshot_counts.get(name, 0)
        live_value = live_counts.get(name, 0)
        entries.append(
            {
                "name": name,
                "snapshot": snapshot_value,
                "live_managed": live_value,
                "delta": live_value - snapshot_value,
            }
        )
    return entries


def _live_repo_label_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "WITH label, count(n) AS total "
            "OPTIONAL MATCH (managed_node) "
            "WHERE label IN labels(managed_node) "
            "AND coalesce(managed_node.managed_by, '') = $managed_by "
            "AND coalesce(managed_node.ingest_wave, '') = $ingest_wave "
            "WITH label, total, count(managed_node) AS managed "
            "OPTIONAL MATCH (unmanaged_node) "
            "WHERE label IN labels(unmanaged_node) "
            "AND coalesce(unmanaged_node.managed_by, '') = '' "
            "RETURN label, total, managed, count(unmanaged_node) AS unmanaged "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context="full audit label summary",
    )
    return [
        {
            "label": str(row["label"]),
            "total": _coerce_int(row["total"]),
            "managed": _coerce_int(row["managed"]),
            "unmanaged": _coerce_int(row["unmanaged"]),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("total"), (int, float))
        and isinstance(row.get("managed"), (int, float))
        and isinstance(row.get("unmanaged"), (int, float))
    ]


def _live_managed_relation_rows(
    client: Neo4jHttpClient,
    relation_types: list[str],
) -> list[dict[str, JsonValue]]:
    counts = _live_managed_relation_counts(
        client,
        tuple(relation_types),
        context="full audit relation summary",
    )
    return [
        {"relation_type": relation_type, "total": total}
        for relation_type, total in sorted(counts.items())
    ]


def _live_orphan_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = $managed_by "
            "AND coalesce(n.ingest_wave, '') = $ingest_wave "
            "AND NOT (n)--() "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
            "managed_by": DEFAULT_MANAGED_BY,
            "ingest_wave": DEFAULT_INGEST_WAVE,
        },
        context="full audit orphan summary",
    )
    return [
        {
            "label": str(row["label"]),
            "count": _coerce_int(row["count"]),
            "samples": row.get("samples", []),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("count"), (int, float))
        and _coerce_int(row["count"]) > 0
    ]


def _live_unmanaged_repo_rows(
    client: Neo4jHttpClient, managed_labels: list[str]
) -> list[dict[str, JsonValue]]:
    if not managed_labels:
        return []
    rows = client.query(
        (
            "UNWIND $managed_labels AS label "
            "OPTIONAL MATCH (n) "
            "WHERE label IN labels(n) "
            "AND coalesce(n.managed_by, '') = '' "
            "RETURN label, count(n) AS count, collect(n.name)[0..10] AS samples "
            "ORDER BY label"
        ),
        {
            "managed_labels": managed_labels,
        },
        context="full audit unmanaged summary",
    )
    return [
        {
            "label": str(row["label"]),
            "count": _coerce_int(row["count"]),
            "samples": row.get("samples", []),
        }
        for row in rows
        if isinstance(row.get("label"), str)
        and isinstance(row.get("count"), (int, float))
        and _coerce_int(row["count"]) > 0
    ]


def _live_scalar(
    client: Neo4jHttpClient, statement: str, parameters: dict[str, JsonValue]
) -> int:
    rows = client.query(statement, parameters)
    if not rows:
        return 0
    value = next(iter(rows[0].values()), 0)
    return int(value) if isinstance(value, (int, float)) else 0


def _row_int_total(rows: list[dict[str, JsonValue]], key: str) -> int:
    return sum(
        _coerce_int(row[key]) for row in rows if isinstance(row.get(key), (int, float))
    )


def _managed_label_counts_from_rows(
    rows: list[dict[str, JsonValue]],
) -> dict[str, int]:
    return {
        str(row["label"]): _coerce_int(row["managed"])
        for row in rows
        if isinstance(row.get("label"), str)
    }


def _managed_relation_counts_from_rows(
    rows: list[dict[str, JsonValue]],
) -> dict[str, int]:
    return {
        str(row["relation_type"]): _coerce_int(row["total"])
        for row in rows
        if isinstance(row.get("relation_type"), str)
    }


def _snapshot_count_map(
    snapshot_stats: dict[str, JsonValue],
    key: str,
) -> dict[str, int]:
    raw_counts = snapshot_stats[key]
    if not isinstance(raw_counts, dict):
        return {}
    return {str(name): _coerce_int(count) for name, count in raw_counts.items()}


def _snapshot_subset_count_map(
    snapshot_stats: dict[str, JsonValue],
    key: str,
    names: tuple[str, ...],
) -> dict[str, int]:
    raw_counts = snapshot_stats[key]
    if not isinstance(raw_counts, dict):
        return {}
    return {name: _coerce_int(raw_counts.get(name, 0)) for name in names}


def _managed_label_summary_from_counts(
    label_counts: dict[str, int],
) -> list[dict[str, JsonValue]]:
    return [
        {
            "label": label,
            "managed": count,
            "count": count,
            "unmanaged": 0,
        }
        for label, count in label_counts.items()
    ]


def _managed_relation_summary_from_counts(
    relation_counts: dict[str, int],
) -> list[dict[str, JsonValue]]:
    return [
        {"relation_type": relation_type, "total": total}
        for relation_type, total in relation_counts.items()
    ]


def _audit_live_summary(
    *,
    managed_node_total: int,
    managed_relation_total: int,
    unmanaged_repo_node_total: int,
    label_summary: list[dict[str, JsonValue]],
    managed_relation_summary: list[dict[str, JsonValue]],
    orphan_summary: list[dict[str, JsonValue]],
    unmanaged_summary: list[dict[str, JsonValue]],
) -> dict[str, JsonValue]:
    return {
        "managed_node_total": managed_node_total,
        "managed_relation_total": managed_relation_total,
        "unmanaged_repo_node_total": unmanaged_repo_node_total,
        "label_summary": label_summary,
        "managed_relation_summary": managed_relation_summary,
        "orphan_summary": {
            "total": _row_int_total(orphan_summary, "count"),
            "by_label": orphan_summary,
        },
        "unmanaged_summary": {
            "total": unmanaged_repo_node_total,
            "by_label": unmanaged_summary,
        },
    }
