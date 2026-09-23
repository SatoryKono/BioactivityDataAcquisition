"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alerttargetselection import AlertTargetSelection
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_alert_target_group import _link_alert_target_group
from memory.graph.sync_pkg.selected_alert_target_groups import (
    _selected_alert_target_groups,
)

__all__ = [
    "_alert_annotations",
    "_alert_dimension_text",
    "_alert_labels",
    "_link_selected_alert_targets",
]


def _alert_annotations(rule: dict[str, object]) -> dict[str, object]:
    annotations = rule.get("annotations")
    return annotations if isinstance(annotations, dict) else {}


def _alert_labels(rule: dict[str, object]) -> dict[str, object]:
    labels = rule.get("labels")
    return labels if isinstance(labels, dict) else {}


def _alert_dimension_text(annotations: dict[str, object]) -> str:
    return " ".join(str(value) for value in annotations.values())


def _link_selected_alert_targets(
    snapshot: GraphSnapshot,
    alert: NodeKey,
    selection: AlertTargetSelection,
) -> None:
    for target_group in _selected_alert_target_groups(selection):
        _link_alert_target_group(snapshot, alert, target_group)
