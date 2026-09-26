"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import (
    NodeKey,
    RetirementAnalysisConfig,
    RetirementScoreInputs,
)
from memory.graph.sync_pkg.graph_contexts import SurfaceAnchorSets
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.retirement_candidate_metrics import (
    _add_retirement_candidate_node,
    _annotate_current_cycle_surface,
    _link_retirement_candidate,
    _retirement_candidate_confidence,
    _retirement_candidate_metrics,
)

__all__ = [
    "_analysis_anchor_counts",
    "_emit_retirement_candidate",
    "_retirement_marker_sets",
    "_retirement_score_inputs",
    "_retirement_surface_payload",
]


def _retirement_marker_sets(
    config: RetirementAnalysisConfig,
    source_text: str,
) -> tuple[list[str], list[str]]:
    return (
        sorted({marker for marker in config.wip_markers if marker in source_text}),
        sorted(
            {marker for marker in config.deprecation_markers if marker in source_text}
        ),
    )


def _retirement_score_inputs(
    anchor_counts: dict[str, int],
    *,
    recent_age_days: int | None,
    wip_markers: list[str],
    deprecation_markers: list[str],
) -> RetirementScoreInputs:
    return RetirementScoreInputs(
        runtime_count=anchor_counts["runtime_count"],
        config_count=anchor_counts["config_count"],
        doc_count=anchor_counts["doc_count"],
        test_count=anchor_counts["test_count"],
        recent_age_days=recent_age_days,
        wip_markers=wip_markers,
        deprecation_markers=deprecation_markers,
    )


def _analysis_anchor_counts(anchors: SurfaceAnchorSets) -> dict[str, int]:
    return {
        "runtime_count": len(anchors.runtime),
        "config_count": len(anchors.config),
        "doc_count": len(anchors.docs),
        "test_count": len(anchors.tests),
    }


def _retirement_surface_payload(
    *,
    family_name: str,
    anchors: SurfaceAnchorSets,
    anchor_counts: dict[str, int],
    wip_markers: list[str],
    deprecation_markers: list[str],
    recent_age_days: int | None,
    cycle_score: int,
    deletion_score: int,
    only_test_referenced: bool,
) -> dict[str, object]:
    return {
        "family_name": family_name,
        "anchors": anchors,
        **anchor_counts,
        "wip_markers": wip_markers,
        "deprecation_markers": deprecation_markers,
        "recent_age_days": recent_age_days,
        "cycle_score": cycle_score,
        "deletion_score": deletion_score,
        "only_test_referenced": only_test_referenced,
    }


def _emit_retirement_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    today: str,
    config: RetirementAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
) -> None:
    metrics = _retirement_candidate_metrics(payload)
    cycle_score = metrics["cycle_score"]
    recent_age_days = payload["recent_age_days"]
    wip_markers = payload["wip_markers"]
    deletion_score = metrics["deletion_score"]
    if cycle_score >= 3:
        _annotate_current_cycle_surface(
            snapshot,
            node,
            cycle_score=cycle_score,
            recent_age_days=recent_age_days,
            wip_markers=wip_markers,
            runtime_count=metrics["runtime_count"],
            config_count=metrics["config_count"],
            doc_count=metrics["doc_count"],
            test_count=metrics["test_count"],
        )
    if deletion_score < config.dead_score_threshold:
        return
    confidence = _retirement_candidate_confidence(
        deletion_score=deletion_score,
        dead_score_threshold=config.dead_score_threshold,
    )
    candidate = _add_retirement_candidate_node(
        snapshot,
        today,
        node,
        payload,
        confidence=confidence,
        cycle_score=cycle_score,
        deletion_score=deletion_score,
        recent_age_days=recent_age_days,
        runtime_count=metrics["runtime_count"],
        config_count=metrics["config_count"],
        doc_count=metrics["doc_count"],
        test_count=metrics["test_count"],
        wip_markers=wip_markers,
    )
    _link_retirement_candidate(snapshot, project, candidate, node.key)
