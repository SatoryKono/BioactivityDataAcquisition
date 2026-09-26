"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import ComplexityAnalysisConfig
from memory.graph.sync_pkg.complexity_marker_buckets import (
    _classify_complexity_candidate,
)
from memory.graph.sync_pkg.graph_contexts import (
    SurfaceAnchorSets,
    SurfaceComplexityMetrics,
)

__all__ = [
    "_complexity_candidate_classification",
    "_complexity_surface_payload",
    "_should_emit_complexity_candidate",
]


def _should_emit_complexity_candidate(
    config: ComplexityAnalysisConfig,
    *,
    complexity_score: float,
    removable_score: float,
) -> bool:
    return (
        complexity_score >= config.complexity_score_threshold
        or removable_score >= config.removable_score_threshold
    )


def _complexity_candidate_classification(
    config: ComplexityAnalysisConfig,
    *,
    removable_score: float,
    anchor_counts: dict[str, int],
    blocked_by_current_cycle: bool,
) -> tuple[str, str]:
    return _classify_complexity_candidate(
        config,
        removable_score=removable_score,
        runtime_count=anchor_counts["runtime_count"],
        config_count=anchor_counts["config_count"],
        doc_count=anchor_counts["doc_count"],
        blocked_by_current_cycle=blocked_by_current_cycle,
    )


def _complexity_surface_payload(
    *,
    source_path: str,
    family_name: str,
    anchors: SurfaceAnchorSets,
    metrics: SurfaceComplexityMetrics,
    indirection_markers: tuple[str, ...],
    stateful_markers: tuple[str, ...],
    deprecation_markers: tuple[str, ...],
    blocked_by_current_cycle: bool,
    classification: str,
    complexity_score: float,
    simplification_score: float,
    removable_score: float,
    removal_confidence: str,
) -> dict[str, object]:
    return {
        "source_path": source_path,
        "family_name": family_name,
        "anchors": anchors,
        "metrics": metrics,
        "indirection_markers": indirection_markers,
        "stateful_markers": stateful_markers,
        "deprecation_markers": deprecation_markers,
        "blocked_by_current_cycle": blocked_by_current_cycle,
        "classification": classification,
        "complexity_score": complexity_score,
        "simplification_score": simplification_score,
        "removable_score": removable_score,
        "removal_confidence": removal_confidence,
    }
