"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg.complexity_marker_buckets import _complexity_scores
from memory.graph.sync_pkg.complexity_score_inputs import _complexity_score_inputs
from memory.graph.sync_pkg.graph_contexts import (
    SurfaceAnchorSets,
    SurfaceComplexityMetrics,
)

__all__ = [
    "_complexity_surface_scores",
]


def _complexity_surface_scores(
    metrics: SurfaceComplexityMetrics,
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> tuple[float, float, float]:
    return _complexity_scores(
        metrics,
        _complexity_score_inputs(
            anchors,
            blocked_by_current_cycle=blocked_by_current_cycle,
            indirection_markers=indirection_markers,
            stateful_markers=stateful_markers,
            deprecation_markers=deprecation_markers,
        ),
    )
