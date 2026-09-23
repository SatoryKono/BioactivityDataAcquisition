"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_alert_rule_group_surfaces import (
    _add_alert_rule_group_surfaces,
)
from memory.graph.sync_pkg.alert_rule_file_payload import _alert_rule_groups
from memory.graph.sync_pkg.alertrulefilecontext import _alert_rule_file_context
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_alert_rule_file_surfaces",
    "_sorted_provider_surface_nodes",
]


def _sorted_provider_surface_nodes(snapshot: GraphSnapshot) -> list[NodeKey]:
    return sorted(
        (key for key in snapshot.nodes if key.label == "provider_surface"),
        key=lambda node: node.name,
    )


def _add_alert_rule_file_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    rules_path: Path,
    *,
    dashboard_metrics: dict[NodeKey, set[str]],
    target_context: AlertTargetContext,
    memory_mapping: dict[str, object],
) -> None:
    file_context = _alert_rule_file_context(snapshot, root, today, rules_path)
    for group in _alert_rule_groups(file_context.payload):
        _add_alert_rule_group_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            file_context.artifact,
            group,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )
