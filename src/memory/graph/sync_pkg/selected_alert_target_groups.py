"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_runbook_context import _alert_runbook_context
from memory.graph.sync_pkg.alert_runbook_path import _add_alert_runbook_doc
from memory.graph.sync_pkg.alerttargetselection import AlertTargetSelection
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_link_alert_runbook",
    "_selected_alert_target_groups",
]


def _selected_alert_target_groups(
    selection: AlertTargetSelection,
) -> tuple[tuple[NodeKey, ...], ...]:
    return tuple(
        targets
        for targets in (
            selection.selected_pipelines,
            selection.selected_providers,
            selection.selected_contracts,
        )
        if targets
    )


def _link_alert_runbook(
    snapshot: GraphSnapshot,
    root: Path,
    alert: NodeKey,
    alert_name: str,
    annotations: dict[str, object],
    today: str,
) -> None:
    runbook_context = _alert_runbook_context(root, annotations)
    if runbook_context is None:
        return
    doc = _add_alert_runbook_doc(snapshot, alert_name, runbook_context.runbook, today)
    snapshot.add_relation(alert, "DESCRIBED_IN", doc, provenance="impact_alerts")
