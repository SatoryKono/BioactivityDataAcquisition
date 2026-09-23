"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Sequence

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.complexity_marker_buckets import _configured_node_keys
from memory.graph.sync_pkg.default_batch_size import (
    DEFAULT_COMMON_PIPELINE_DASHBOARDS,
    DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS,
    DEFAULT_ENTITY_PIPELINE_DASHBOARDS,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _mapping_section
from memory.graph.sync_pkg.pipeline_dashboard_config import _pipeline_dashboard_config

__all__ = [
    "_alert_surface_nodes",
    "_governance_target_groups",
    "_link_policy_governance_group",
    "_pipeline_dashboard_targets",
    "_pipeline_operational_section",
]


def _governance_target_groups(
    target_group: Sequence[NodeKey],
    extra_target_group: Sequence[NodeKey] | None = None,
) -> tuple[Sequence[NodeKey], ...]:
    return (
        (target_group,)
        if extra_target_group is None
        else (target_group, extra_target_group)
    )


def _link_policy_governance_group(
    snapshot: GraphSnapshot,
    policy: NodeKey,
    *target_groups: Sequence[NodeKey],
) -> None:
    if policy not in snapshot.nodes:
        return
    for targets in target_groups:
        for target in targets:
            snapshot.add_relation(
                policy, "GOVERNS", target, provenance="impact_governance"
            )


def _alert_surface_nodes(snapshot: GraphSnapshot) -> list[NodeKey]:
    return [
        node_key
        for node_key in sorted(snapshot.nodes, key=lambda node: (node.label, node.name))
        if node_key.label == "alert_surface"
    ]


def _pipeline_operational_section(
    memory_mapping: dict[str, object],
) -> dict[str, object]:
    return _mapping_section(memory_mapping, "pipeline_operational")


def _pipeline_dashboard_targets(
    pipeline_ops: dict[str, object],
) -> tuple[list[NodeKey], list[NodeKey], list[NodeKey]]:
    dashboards_cfg, kind_dashboards = _pipeline_dashboard_config(pipeline_ops)

    common_dashboards = _configured_node_keys(
        "dashboard_surface",
        dashboards_cfg.get("common"),
        DEFAULT_COMMON_PIPELINE_DASHBOARDS,
    )
    entity_dashboards = _configured_node_keys(
        "dashboard_surface",
        kind_dashboards.get("entity"),
        DEFAULT_ENTITY_PIPELINE_DASHBOARDS,
    )
    composite_dashboards = _configured_node_keys(
        "dashboard_surface",
        kind_dashboards.get("composite"),
        DEFAULT_COMPOSITE_PIPELINE_DASHBOARDS,
    )
    return common_dashboards, entity_dashboards, composite_dashboards
