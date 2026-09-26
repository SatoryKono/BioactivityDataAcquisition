"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Mapping, Set

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_annotations import _link_selected_alert_targets
from memory.graph.sync_pkg.alert_target_inputs import _alert_target_inputs
from memory.graph.sync_pkg.alert_targets import _select_alert_targets
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_alert_target_group import (
    _link_alert_observer_dashboards,
)

__all__ = [
    "_link_alert_targets",
]


def _link_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    alert_name: str,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    expr, dimensions = _alert_target_inputs(rule)
    selection = _select_alert_targets(
        target_context,
        alert_name,
        group_name,
        expr,
        dimensions,
    )
    _link_selected_alert_targets(snapshot, alert, selection)
    _link_alert_observer_dashboards(
        snapshot,
        alert,
        alert_name,
        group_name,
        expr,
        dashboard_metrics,
        memory_mapping,
    )
