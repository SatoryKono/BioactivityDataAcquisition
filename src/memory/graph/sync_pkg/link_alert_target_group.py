"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Mapping, Set

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.existing_snapshot_nodes import (
    _existing_snapshot_nodes,
    _selected_alert_dashboards,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_alert_observer_dashboards",
    "_link_alert_target_group",
]


def _link_alert_target_group(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    targets: tuple[NodeKey, ...],
) -> None:
    for target in targets:
        snapshot.add_relation(alert, "DEPENDS_ON", target, provenance="impact_alerts")


def _link_alert_observer_dashboards(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    expr: str,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    memory_mapping: dict[str, object],
) -> None:
    for dashboard in _existing_snapshot_nodes(
        snapshot,
        _selected_alert_dashboards(
            alert_name,
            group_name,
            expr,
            dashboard_metrics,
            memory_mapping,
        ),
    ):
        snapshot.add_relation(
            alert, "OBSERVED_BY", dashboard, provenance="impact_alerts"
        )
