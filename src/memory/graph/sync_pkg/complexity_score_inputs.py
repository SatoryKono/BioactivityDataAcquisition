"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ComplexityScoreInputs
from memory.graph.sync_pkg.graph_contexts import SurfaceAnchorSets

__all__ = [
    "_complexity_score_inputs",
]


def _complexity_score_inputs(
    anchors: SurfaceAnchorSets,
    *,
    blocked_by_current_cycle: bool,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
) -> ComplexityScoreInputs:
    return ComplexityScoreInputs(
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        runtime_count=len(anchors.runtime),
        config_count=len(anchors.config),
        doc_count=len(anchors.docs),
        test_count=len(anchors.tests),
        blocked_by_current_cycle=blocked_by_current_cycle,
    )
