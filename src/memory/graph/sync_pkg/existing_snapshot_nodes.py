"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_targets import _select_alert_dashboards
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_existing_snapshot_nodes",
    "_selected_alert_dashboards",
]


def _existing_snapshot_nodes(
    snapshot: GraphSnapshot,
    nodes: Iterable[NodeKey],
) -> tuple[NodeKey, ...]:
    return tuple(node for node in nodes if node in snapshot.nodes)


def _selected_alert_dashboards(
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    memory_mapping: dict[str, object],
) -> tuple[NodeKey, ...]:
    return tuple(
        _select_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        )
    )
