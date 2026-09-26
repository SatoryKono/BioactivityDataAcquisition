"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ComplexityAnalysisConfig, NodeKey
from memory.graph.sync_pkg.alerttargetselection import ComplexityCandidateContext
from memory.graph.sync_pkg.complexity_blocker_context import _complexity_blocker_context
from memory.graph.sync_pkg.graph_contexts import SurfaceAnchorSets
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot

__all__ = [
    "_add_complexity_candidate_node",
    "_complexity_candidate_anchor_slices",
    "_link_complexity_candidate",
]


def _complexity_candidate_anchor_slices(
    anchors: SurfaceAnchorSets,
    *,
    blocker_anchor_limit: int,
) -> tuple[
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
    tuple[NodeKey, ...],
]:
    return (
        anchors.runtime[:blocker_anchor_limit],
        anchors.config[:blocker_anchor_limit],
        anchors.docs[:blocker_anchor_limit],
        anchors.tests[:blocker_anchor_limit],
    )


def _link_complexity_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    candidate: NodeKey,
    target: NodeKey,
    *,
    context: ComplexityCandidateContext,
) -> None:
    snapshot.add_relation(
        project, "CONTAINS", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        target, "HAS_COMPLEXITY_SIGNAL", candidate, provenance="complexity_analysis"
    )
    snapshot.add_relation(
        candidate,
        "CANDIDATE_FOR_SIMPLIFICATION",
        target,
        provenance="complexity_analysis",
    )
    if context.classification == "removable_complexity":
        snapshot.add_relation(
            candidate, "CANDIDATE_FOR_REMOVAL", target, provenance="complexity_analysis"
        )
    for anchor in context.runtime_anchors:
        snapshot.add_relation(
            candidate, "JUSTIFIED_BY_RUNTIME", anchor, provenance="complexity_analysis"
        )
    for anchor in [*context.config_anchors, *context.doc_anchors]:
        snapshot.add_relation(
            candidate, "BLOCKED_BY_VARIANCE", anchor, provenance="complexity_analysis"
        )


def _add_complexity_candidate_node(
    snapshot: GraphSnapshot,
    today: str,
    config: ComplexityAnalysisConfig,
    node: GraphNode,
    payload: dict[str, object],
    *,
    context: ComplexityCandidateContext,
) -> NodeKey:
    blocker_context = _complexity_blocker_context(
        node,
        blocked_by_current_cycle=context.blocked_by_current_cycle,
    )
    return snapshot.add_node(
        "complexity_candidate",
        f"{node.key.label}:{node.key.name}",
        summary=f"Complexity analysis candidate for `{node.key.name}` in `{payload['family_name']}`.",
        source_path=str(payload["source_path"]),
        source_kind="complexity_candidate",
        family_name=str(payload["family_name"]),
        target_label=node.key.label,
        target_name=node.key.name,
        classification=context.classification,
        complexity_score=payload["complexity_score"],
        simplification_score=payload["simplification_score"],
        removable_score=payload["removable_score"],
        simplification_confidence="high"
        if context.simplification_score >= config.complexity_score_threshold + 2
        else "medium",
        removal_confidence=payload["removal_confidence"],
        branch_count=context.metrics.branch_count,
        nesting_depth=context.metrics.nesting_depth,
        call_count=context.metrics.call_count,
        helper_call_count=context.metrics.helper_call_count,
        abstraction_fanout=context.metrics.abstraction_fanout,
        api_surface_to_logic_ratio=context.metrics.api_surface_to_logic_ratio,
        runtime_anchor_count=len(context.anchors.runtime),
        config_anchor_count=len(context.anchors.config),
        doc_anchor_count=len(context.anchors.docs),
        test_anchor_count=len(context.anchors.tests),
        indirection_markers=payload["indirection_markers"],
        stateful_markers=payload["stateful_markers"],
        deprecation_markers=payload["deprecation_markers"],
        blocked_by_current_cycle=context.blocked_by_current_cycle,
        blocked_by_current_cycle_target_name=blocker_context["target_name"],
        blocked_by_current_cycle_score=blocker_context["score"],
        blocked_by_current_cycle_wip_markers=blocker_context["wip_markers"],
        runtime_anchors=[anchor.name for anchor in context.runtime_anchors],
        config_anchors=[anchor.name for anchor in context.config_anchors],
        doc_anchors=[anchor.name for anchor in context.doc_anchors],
        test_anchors=[anchor.name for anchor in context.test_anchors],
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="medium",
    )
