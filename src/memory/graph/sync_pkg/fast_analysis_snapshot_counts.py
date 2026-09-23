"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue
from memory.graph.sync_pkg.live_queries import (
    _audit_live_summary,
    _live_managed_node_counts,
    _live_managed_relation_counts,
    _managed_label_summary_from_counts,
    _managed_relation_summary_from_counts,
    _snapshot_subset_count_map,
)
from memory.graph.sync_pkg.transport import Neo4jHttpClient

__all__ = [
    "_active_critical_names",
    "_fast_analysis_live_counts",
    "_fast_analysis_live_summary",
    "_fast_analysis_snapshot_counts",
    "_fast_audit_snapshot_payload",
]


def _fast_analysis_snapshot_counts(
    snapshot_stats: dict[str, JsonValue],
    active_labels: tuple[str, ...],
    active_relation_types: tuple[str, ...],
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _snapshot_subset_count_map(snapshot_stats, "labels", active_labels),
        _snapshot_subset_count_map(
            snapshot_stats, "relation_types", active_relation_types
        ),
    )


def _fast_analysis_live_counts(
    client: Neo4jHttpClient,
    active_labels: tuple[str, ...],
    active_relation_types: tuple[str, ...],
) -> tuple[dict[str, int], dict[str, int]]:
    return (
        _live_managed_node_counts(
            client,
            active_labels,
            context="fast audit label summary",
        ),
        _live_managed_relation_counts(
            client,
            active_relation_types,
            context="fast audit relation summary",
        ),
    )


def _fast_analysis_live_summary(
    live_managed_label_counts: dict[str, int],
    live_managed_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return _audit_live_summary(
        managed_node_total=sum(live_managed_label_counts.values()),
        managed_relation_total=sum(live_managed_relation_counts.values()),
        unmanaged_repo_node_total=0,
        label_summary=_managed_label_summary_from_counts(live_managed_label_counts),
        managed_relation_summary=_managed_relation_summary_from_counts(
            live_managed_relation_counts
        ),
        orphan_summary=[],
        unmanaged_summary=[],
    )


def _active_critical_names(
    snapshot_stats: dict[str, JsonValue],
    key: str,
    critical_names: Iterable[str],
) -> tuple[str, ...]:
    raw_counts = snapshot_stats.get(key)
    if not isinstance(raw_counts, dict):
        return ()
    return tuple(
        name for name in critical_names if _coerce_int(raw_counts.get(name, 0)) > 0
    )


def _fast_audit_snapshot_payload(
    snapshot_label_counts: dict[str, int],
    snapshot_relation_counts: dict[str, int],
) -> dict[str, JsonValue]:
    return {
        "node_count": sum(snapshot_label_counts.values()),
        "relation_count": sum(snapshot_relation_counts.values()),
        "labels": snapshot_label_counts,
        "relation_types": snapshot_relation_counts,
    }
