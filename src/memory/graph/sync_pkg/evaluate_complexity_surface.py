"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import (
    AnalysisLabelSets,
    ComplexityAnalysisConfig,
)
from memory.graph.sync_pkg.complexity_analysis_context import (
    _complexity_surface_measurements,
)
from memory.graph.sync_pkg.complexity_analysis_label_sets import (
    _complexity_surface_prerequisites,
)
from memory.graph.sync_pkg.graph_contexts import (
    DuplicateFamilyConfig,
    SurfaceRelationIndexes,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.retirement_marker_sets import _analysis_anchor_counts
from memory.graph.sync_pkg.should_emit_complexity_candidate import (
    _complexity_candidate_classification,
    _complexity_surface_payload,
    _should_emit_complexity_candidate,
)

__all__ = [
    "_evaluate_complexity_surface",
]


def _evaluate_complexity_surface(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
    label_sets: AnalysisLabelSets,
    indexes: SurfaceRelationIndexes,
    text_cache: dict[str, str],
    config: ComplexityAnalysisConfig,
) -> dict[str, object] | None:
    prerequisites = _complexity_surface_prerequisites(
        snapshot,
        root,
        node,
        duplication_config=duplication_config,
        family_names=family_names,
        family_cache=family_cache,
        text_cache=text_cache,
    )
    if prerequisites is None:
        return None
    source_path, family, module_key, source_text = prerequisites
    (
        anchors,
        indirection_markers,
        stateful_markers,
        deprecation_markers,
        metrics,
        blocked_by_current_cycle,
        complexity_score,
        simplification_score,
        removable_score,
    ) = _complexity_surface_measurements(
        snapshot,
        node,
        source_path=source_path,
        module_key=module_key,
        source_text=source_text,
        label_sets=label_sets,
        indexes=indexes,
        config=config,
    )
    anchor_counts = _analysis_anchor_counts(anchors)
    if not _should_emit_complexity_candidate(
        config,
        complexity_score=complexity_score,
        removable_score=removable_score,
    ):
        return None
    classification, removal_confidence = _complexity_candidate_classification(
        config,
        removable_score=removable_score,
        anchor_counts=anchor_counts,
        blocked_by_current_cycle=blocked_by_current_cycle,
    )
    return _complexity_surface_payload(
        source_path=source_path,
        family_name=family.name,
        anchors=anchors,
        metrics=metrics,
        indirection_markers=indirection_markers,
        stateful_markers=stateful_markers,
        deprecation_markers=deprecation_markers,
        blocked_by_current_cycle=blocked_by_current_cycle,
        classification=classification,
        complexity_score=complexity_score,
        simplification_score=simplification_score,
        removable_score=removable_score,
        removal_confidence=removal_confidence,
    )
