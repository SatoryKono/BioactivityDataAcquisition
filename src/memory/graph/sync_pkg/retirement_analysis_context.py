"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from memory.graph.sync_pkg._core_models import (
    AnalysisLabelSets,
    NodeKey,
    RetirementAnalysisConfig,
)
from memory.graph.sync_pkg.analysis_source import _build_surface_relation_indexes
from memory.graph.sync_pkg.git_history import _git_last_commit_age_days_bulk
from memory.graph.sync_pkg.graph_contexts import (
    DuplicateFamilyConfig,
    RetirementAnalysisContext,
    SurfaceRelationIndexes,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.retirement_analysis_label_sets import (
    _evaluate_retirement_surface,
    _retirement_analysis_label_sets,
)

__all__ = [
    "_prime_retirement_age_cache",
    "_retirement_analysis_context",
    "_retirement_candidate_payload",
]


def _retirement_analysis_context(
    snapshot: GraphSnapshot,
    config: RetirementAnalysisConfig,
    today: str,
) -> RetirementAnalysisContext:
    return RetirementAnalysisContext(
        label_sets=_retirement_analysis_label_sets(),
        indexes=_build_surface_relation_indexes(snapshot),
        today_date=date.fromisoformat(today),
        family_names=set(config.family_names),
    )


def _prime_retirement_age_cache(
    root: Path,
    today_date: date,
    age_cache: dict[str, int | None],
    candidate_nodes: list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]],
) -> None:
    _git_last_commit_age_days_bulk(
        root,
        [source_path for _, source_path, _, _ in candidate_nodes],
        today_date,
        age_cache,
    )


def _retirement_candidate_payload(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    source_path: str,
    module_key: NodeKey,
    *,
    indexes: SurfaceRelationIndexes,
    label_sets: AnalysisLabelSets,
    text_cache: dict[str, str],
    age_cache: dict[str, int | None],
    family_name: str,
    config: RetirementAnalysisConfig,
) -> dict[str, object] | None:
    return _evaluate_retirement_surface(
        snapshot,
        root,
        node,
        source_path,
        module_key,
        indexes=indexes,
        label_sets=label_sets,
        text_cache=text_cache,
        age_cache=age_cache,
        family_name=family_name,
        config=config,
    )
