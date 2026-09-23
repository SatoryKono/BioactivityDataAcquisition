"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.alert_rules_paths import (
    _alert_rules_paths,
    _alert_surface_context,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.sorted_provider_surface_nodes import (
    _add_alert_rule_file_surfaces,
)

__all__ = [
    "_add_alert_surfaces",
    "_provider_regression_provider_target",
]


def _provider_regression_provider_target(
    provider_name: object,
    raw_test_path: object,
) -> tuple[str, str] | None:
    if isinstance(provider_name, str) and isinstance(raw_test_path, str):
        return provider_name, raw_test_path
    return None


def _add_alert_surfaces(
    snapshot: GraphSnapshot,
    root: Path,
    project: NodeKey,
    today: str,
    pipeline_nodes: dict[str, NodeKey],
    contract_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    rules_root = root / "grafana" / "prometheus-rules"
    if not rules_root.is_dir():
        return

    dashboard_metrics, target_context = _alert_surface_context(
        snapshot,
        root,
        pipeline_nodes=pipeline_nodes,
        contract_nodes=contract_nodes,
        memory_mapping=memory_mapping,
    )
    for rules_path in _alert_rules_paths(rules_root):
        _add_alert_rule_file_surfaces(
            snapshot,
            root,
            project,
            today,
            rules_path,
            dashboard_metrics=dashboard_metrics,
            target_context=target_context,
            memory_mapping=memory_mapping,
        )
