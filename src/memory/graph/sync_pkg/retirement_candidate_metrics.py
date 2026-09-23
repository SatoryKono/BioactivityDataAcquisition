"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from typing import cast

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot

__all__ = [
    "_add_retirement_candidate_node",
    "_annotate_current_cycle_surface",
    "_link_retirement_candidate",
    "_retirement_candidate_confidence",
    "_retirement_candidate_metrics",
]


def _retirement_candidate_metrics(payload: dict[str, object]) -> dict[str, int]:
    return {
        "cycle_score": _coerce_int(payload["cycle_score"]),
        "runtime_count": _coerce_int(payload["runtime_count"]),
        "config_count": _coerce_int(payload["config_count"]),
        "doc_count": _coerce_int(payload["doc_count"]),
        "test_count": _coerce_int(payload["test_count"]),
        "deletion_score": _coerce_int(payload["deletion_score"]),
    }


def _retirement_candidate_confidence(
    *,
    deletion_score: int,
    dead_score_threshold: int,
) -> str:
    return "high" if deletion_score >= dead_score_threshold + 2 else "medium"


def _link_retirement_candidate(
    snapshot: GraphSnapshot,
    project: NodeKey,
    candidate: NodeKey,
    target: NodeKey,
) -> None:
    snapshot.add_relation(
        project, "CONTAINS", candidate, provenance="retirement_analysis"
    )
    snapshot.add_relation(
        candidate, "CANDIDATE_FOR_REMOVAL", target, provenance="retirement_analysis"
    )


def _annotate_current_cycle_surface(
    snapshot: GraphSnapshot,
    node: GraphNode,
    *,
    cycle_score: int,
    recent_age_days: object,
    wip_markers: object,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    test_count: int,
) -> None:
    snapshot.add_node(
        node.key.label,
        node.key.name,
        current_cycle_status="current_cycle",
        current_cycle_score=cycle_score,
        current_cycle_recent_age_days=recent_age_days,
        current_cycle_wip_markers=wip_markers,
        current_cycle_runtime_anchor_count=runtime_count,
        current_cycle_config_anchor_count=config_count,
        current_cycle_doc_anchor_count=doc_count,
        current_cycle_test_anchor_count=test_count,
    )


def _add_retirement_candidate_node(
    snapshot: GraphSnapshot,
    today: str,
    node: GraphNode,
    payload: dict[str, object],
    *,
    confidence: str,
    cycle_score: int,
    deletion_score: int,
    recent_age_days: object,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    test_count: int,
    wip_markers: object,
) -> NodeKey:
    anchors = cast("AnalysisAnchors", payload["anchors"])
    return snapshot.add_node(
        "retirement_candidate",
        f"{node.key.label}:{node.key.name}",
        summary=f"Potential dead/stale code candidate `{node.key.name}` in `{payload['family_name']}`.",
        source_path=str(node.properties.get("source_path")),
        source_kind="retirement_candidate",
        family_name=str(payload["family_name"]),
        target_label=node.key.label,
        target_name=node.key.name,
        deletion_score=deletion_score,
        deletion_confidence=confidence,
        recent_age_days=recent_age_days,
        only_test_referenced=payload["only_test_referenced"],
        deprecation_markers=payload["deprecation_markers"],
        runtime_anchor_count=runtime_count,
        config_anchor_count=config_count,
        doc_anchor_count=doc_count,
        test_anchor_count=test_count,
        runtime_anchors=sorted(anchor.name for anchor in anchors.runtime),
        config_anchors=sorted(anchor.name for anchor in anchors.config),
        doc_anchors=sorted(anchor.name for anchor in anchors.docs),
        test_anchors=sorted(anchor.name for anchor in anchors.tests),
        blocked_by_current_cycle=cycle_score >= 3,
        blocked_by_current_cycle_target_name=node.key.name
        if cycle_score >= 3
        else None,
        blocked_by_current_cycle_score=cycle_score if cycle_score >= 3 else None,
        blocked_by_current_cycle_wip_markers=wip_markers if cycle_score >= 3 else None,
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence=confidence,
    )
