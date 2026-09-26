"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _module_dotted_name
from memory.graph.sync_pkg._core_models import (
    AnalysisLabelSets,
    ComplexityAnalysisConfig,
    NodeKey,
)
from memory.graph.sync_pkg.analysis_source import _build_surface_relation_indexes
from memory.graph.sync_pkg.complexity_analysis_label_sets import (
    _complexity_analysis_label_sets,
)
from memory.graph.sync_pkg.complexity_marker_buckets import _complexity_marker_buckets
from memory.graph.sync_pkg.complexity_surface_scores import _complexity_surface_scores
from memory.graph.sync_pkg.curated_quality_gates import _collect_analysis_anchor_nodes
from memory.graph.sync_pkg.graph_contexts import (
    ComplexityAnalysisContext,
    SurfaceAnchorSets,
    SurfaceComplexityMetrics,
    SurfaceRelationIndexes,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.int_node_property import (
    _aggregate_surface_complexity_metrics,
)

__all__ = [
    "_complexity_analysis_context",
    "_complexity_surface_measurements",
]


def _complexity_analysis_context(
    snapshot: GraphSnapshot,
    config: ComplexityAnalysisConfig,
) -> ComplexityAnalysisContext:
    return ComplexityAnalysisContext(
        family_names=set(config.family_names),
        label_sets=_complexity_analysis_label_sets(),
        indexes=_build_surface_relation_indexes(snapshot),
    )


def _complexity_surface_measurements(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    source_path: str,
    module_key: NodeKey,
    source_text: str,
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    config: ComplexityAnalysisConfig,
) -> tuple[
    SurfaceAnchorSets,
    tuple[str, ...],
    tuple[str, ...],
    tuple[str, ...],
    SurfaceComplexityMetrics,
    bool,
    float,
    float,
    float,
]:
    anchors = _collect_analysis_anchor_nodes(
        snapshot, indexes, node.key, module_key, label_sets
    )
    symbol_name = node.key.name.removeprefix(f"{_module_dotted_name(source_path)}.")
    indirection_markers, stateful_markers, deprecation_markers = (
        _complexity_marker_buckets(
            config,
            source_path,
            symbol_name,
            source_text,
        )
    )
    metrics = _aggregate_surface_complexity_metrics(snapshot, indexes, node.key)
    blocked_by_current_cycle = bool(node.properties.get("current_cycle_status"))
    complexity_score, simplification_score, removable_score = (
        _complexity_surface_scores(
            metrics,
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        )
    )
    return (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    )
