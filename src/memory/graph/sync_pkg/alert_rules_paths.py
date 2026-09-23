"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_target_context import _alert_target_context
from memory.graph.sync_pkg.dashboard_metrics import _dashboard_metric_index
from memory.graph.sync_pkg.graph_contexts import AlertTargetContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_alert_rules_paths",
    "_alert_surface_context",
]


def _alert_rules_paths(rules_root: Path) -> tuple[Path, ...]:
    return tuple(sorted(rules_root.glob("*.y*ml")))


def _alert_surface_context(
    snapshot: GraphSnapshot,
    root: Path,
    *,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> tuple[dict[NodeKey, set[str]], AlertTargetContext]:
    return (
        _dashboard_metric_index(root),
        _alert_target_context(
            snapshot,
            pipeline_nodes=pipeline_nodes,
            contract_nodes=contract_nodes,
            memory_mapping=memory_mapping,
        ),
    )
