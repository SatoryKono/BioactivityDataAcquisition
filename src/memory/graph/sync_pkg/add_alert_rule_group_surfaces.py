"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Mapping, Set
from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_single_alert_surface import _add_alert_surface_from_rule
from memory.graph.sync_pkg.alert_group_name import _alert_rule_group_context
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_alert_rule_group_surfaces",
]


def _add_alert_rule_group_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    artifact: NodeKey,
    group: dict[str, object],
    *,
    dashboard_metrics: Mapping[NodeKey, Set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    group_context = _alert_rule_group_context(group, rules_path)
    for rule in group_context.rules:
        _add_alert_surface_from_rule(
            snapshot,
            root,
            project,
            today,
            rules_path,
            artifact,
            group_name=group_context.group_name,
            rule=rule,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )
