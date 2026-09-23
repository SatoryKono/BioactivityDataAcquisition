"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from typing import cast

from memory.graph.sync_pkg._core_convert import _coerce_float
from memory.graph.sync_pkg._core_models import ComplexityAnalysisConfig, NodeKey
from memory.graph.sync_pkg.alerttargetselection import ComplexityCandidateContext
from memory.graph.sync_pkg.complexity_candidate_anchor_slices import (
    _add_complexity_candidate_node,
    _complexity_candidate_anchor_slices,
    _link_complexity_candidate,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot

__all__ = [
    "_complexity_candidate_context",
    "_emit_complexity_candidate",
]


def _complexity_candidate_context(
    payload: dict[str, object],
    *,
    config: ComplexityAnalysisConfig,
) -> ComplexityCandidateContext:
    anchors = cast("SurfaceAnchorSets", payload["anchors"])
    runtime_anchors, config_anchors, doc_anchors, test_anchors = (
        _complexity_candidate_anchor_slices(
            anchors,
            blocker_anchor_limit=config.blocker_anchor_limit,
        )
    )
    return ComplexityCandidateContext(
        anchors=anchors,
        metrics=cast("SurfaceComplexityMetrics", payload["metrics"]),
        runtime_anchors=runtime_anchors,
        config_anchors=config_anchors,
        doc_anchors=doc_anchors,
        test_anchors=test_anchors,
        blocked_by_current_cycle=bool(payload["blocked_by_current_cycle"]),
        simplification_score=_coerce_float(payload["simplification_score"]),
        classification=str(payload["classification"]),
    )


def _emit_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
) -> None:
    context = _complexity_candidate_context(payload, config=config)
    candidate = _add_complexity_candidate_node(
        snapshot,
        today,
        config,
        node,
        payload,
        context=context,
    )
    _link_complexity_candidate(
        snapshot,
        project,
        candidate,
        node.key,
        context=context,
    )
