"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Mapping, Set
from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_rule_context import _alert_rule_context
from memory.graph.sync_pkg.alert_rule_file_payload import _add_alert_surface_node
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_alert_targets import _link_alert_targets
from memory.graph.sync_pkg.selected_alert_target_groups import _link_alert_runbook

__all__ = [
    "_add_alert_surface_from_rule",
    "_add_single_alert_surface",
]


def _add_single_alert_surface(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group_name: str,
    rule: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    alert_context = _alert_rule_context(rule)
    if alert_context is None:
        return
    alert = _add_alert_surface_node(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        alert_context.alert_name,
        alert_context.annotations,
        alert_context.labels,
    )
    _link_alert_targets(
        snapshot,
        alert,
        alert_context.alert_name,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )
    _link_alert_runbook(
        snapshot,
        root,
        alert,
        alert_context.alert_name,
        alert_context.annotations,
        today,
    )


def _add_alert_surface_from_rule(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    *,
    group_name: str,
    rule: dict[str, object],
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    _add_single_alert_surface(
        snapshot,
        root,
        project,
        today,
        rules_path,
        artifact,
        group_name,
        rule,
        dashboard_metrics=dashboard_metrics,
        target_context=target_context,
        memory_mapping=memory_mapping,
    )
