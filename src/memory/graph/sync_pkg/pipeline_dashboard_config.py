"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from dataclasses import dataclass

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.complexity_marker_buckets import _link_existing_targets
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "PipelineOperationalContext",
    "_link_pipeline_operational_targets",
    "_pipeline_dashboard_config",
    "_pipeline_kind_dashboards",
]


def _pipeline_dashboard_config(
    pipeline_ops: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    dashboards_cfg = pipeline_ops.get("dashboards")
    if not isinstance(dashboards_cfg, dict):
        dashboards_cfg = {}
    kind_dashboards = dashboards_cfg.get("by_kind")
    if not isinstance(kind_dashboards, dict):
        kind_dashboards = {}
    return dashboards_cfg, kind_dashboards


def _pipeline_kind_dashboards(
    pipeline_kind: object,
    *,
    entity_dashboards: list[NodeKey],
    composite_dashboards: list[NodeKey],
) -> list[NodeKey]:
    if pipeline_kind == "entity":
        return entity_dashboards
    if pipeline_kind == "composite":
        return composite_dashboards
    return []


@dataclass(frozen=True)
class PipelineOperationalContext:
    runtime_paths: list[NodeKey]
    validation_gates: list[NodeKey]
    common_dashboards: list[NodeKey]
    entity_dashboards: list[NodeKey]
    composite_dashboards: list[NodeKey]


def _link_pipeline_operational_targets(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    *,
    runtime_paths: list[NodeKey],
    validation_gates: list[NodeKey],
    common_dashboards: list[NodeKey],
    kind_dashboards: list[NodeKey],
) -> None:
    _link_existing_targets(
        snapshot,
        pipeline,
        "RUNS_VIA",
        runtime_paths,
        provenance="impact_pipeline_ops",
    )
    _link_existing_targets(
        snapshot,
        pipeline,
        "VALIDATED_BY",
        validation_gates,
        provenance="impact_pipeline_ops",
    )
    _link_existing_targets(
        snapshot,
        pipeline,
        "OBSERVED_BY",
        common_dashboards,
        provenance="impact_pipeline_ops",
    )
    if kind_dashboards:
        _link_existing_targets(
            snapshot,
            pipeline,
            "OBSERVED_BY",
            kind_dashboards,
            provenance="impact_pipeline_ops",
        )
