"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_iterable, _as_string_list
from memory.graph.sync_pkg._core_models import (
    ComplexityAnalysisConfig,
    ComplexityMetrics,
    ComplexityScoreInputs,
    NodeKey,
    RetirementAnalysisConfig,
    RetirementScoreInputs,
)
from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.score_family import _presence_score, _threshold_score

__all__ = [
    "_classify_complexity_candidate",
    "_complexity_marker_buckets",
    "_complexity_scores",
    "_configured_duplicate_families",
    "_configured_node_keys",
    "_link_existing_targets",
    "_retirement_scores",
]


def _complexity_marker_buckets(
    config: ComplexityAnalysisConfig,
    relative_path: str,
    symbol_name: str,
    source_text: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    normalized = f"{relative_path} {symbol_name}".casefold()
    indirection = sorted(
        {
            marker
            for marker in config.indirection_markers
            if marker in normalized or marker in source_text
        }
    )
    stateful = sorted(
        {
            marker
            for marker in config.stateful_markers
            if marker in normalized or marker in source_text
        }
    )
    deprecation = sorted(
        {
            marker
            for marker in config.deprecation_markers
            if marker in normalized or marker in source_text
        }
    )
    return tuple(indirection), tuple(stateful), tuple(deprecation)


def _retirement_scores(
    config: RetirementAnalysisConfig,
    inputs: RetirementScoreInputs,
) -> tuple[int, int, bool]:
    only_test_referenced = (
        inputs.test_count > 0
        and inputs.runtime_count == 0
        and inputs.config_count == 0
        and inputs.doc_count == 0
    )
    cycle_score = 0
    if (
        inputs.recent_age_days is not None
        and inputs.recent_age_days <= config.current_cycle_age_days
    ):
        cycle_score += 2
    if inputs.wip_markers:
        cycle_score += 3
    if inputs.doc_count > 0 and inputs.runtime_count == 0:
        cycle_score += 1

    deletion_score = 0
    if inputs.runtime_count == 0:
        deletion_score += 3
    if inputs.config_count == 0:
        deletion_score += 2
    if inputs.doc_count == 0:
        deletion_score += 1
    if only_test_referenced:
        deletion_score += 2
    if inputs.deprecation_markers:
        deletion_score += 2
    if (
        inputs.recent_age_days is not None
        and inputs.recent_age_days >= config.stale_age_days
    ):
        deletion_score += 2
    return cycle_score, deletion_score - cycle_score, only_test_referenced


def _complexity_scores(
    metrics: ComplexityMetrics,
    inputs: ComplexityScoreInputs,
) -> tuple[int, int, int]:
    complexity_score = 0
    complexity_score += _threshold_score(metrics.branch_count, medium=3, high=6)
    complexity_score += _threshold_score(metrics.nesting_depth, medium=3, high=4)
    complexity_score += _threshold_score(metrics.helper_call_count, medium=2, high=4)
    complexity_score += _presence_score(len(inputs.indirection_markers))
    complexity_score += _presence_score(len(inputs.stateful_markers))
    complexity_score += _threshold_score(metrics.abstraction_fanout, medium=3, high=6)

    removable_score = complexity_score
    if inputs.runtime_count == 0:
        removable_score += 2
    if inputs.config_count == 0:
        removable_score += 2
    if inputs.doc_count == 0:
        removable_score += 1
    if inputs.test_count == 0:
        removable_score += 1
    if inputs.deprecation_markers:
        removable_score += 2
    if inputs.blocked_by_current_cycle:
        removable_score -= 3
    return complexity_score, complexity_score, removable_score


def _classify_complexity_candidate(
    config: ComplexityAnalysisConfig,
    *,
    removable_score: float,
    runtime_count: int,
    config_count: int,
    doc_count: int,
    blocked_by_current_cycle: bool,
) -> tuple[str, str]:
    if (
        removable_score >= config.removable_score_threshold
        and not blocked_by_current_cycle
    ):
        removal_confidence = (
            "high"
            if removable_score >= config.removable_score_threshold + 2
            else "medium"
        )
        return "removable_complexity", removal_confidence
    if runtime_count == 0 and config_count == 0 and doc_count == 0:
        return "overengineered_stale", "medium"
    return "overengineered_active", "low"


def _configured_node_keys(
    label: str,
    values: object,
    default_names: tuple[str, ...],
) -> list[NodeKey]:
    names = _as_string_list(values) or list(default_names)
    return [NodeKey(label, name) for name in names]


def _link_existing_targets(
    snapshot: GraphSnapshot,
    source: NodeKey,
    relation_type: str,
    targets: list[NodeKey],
    *,
    provenance: str,
) -> None:
    for target in targets:
        if target in snapshot.nodes:
            snapshot.add_relation(source, relation_type, target, provenance=provenance)


def _configured_duplicate_families(
    payload: dict[str, object],
    duplication_config: dict[str, object],
) -> tuple[str, ...]:
    duplication_families = tuple(
        family.name
        for family in _as_iterable(duplication_config.get("families"))
        if isinstance(family, DuplicateFamilyConfig)
    )
    configured_families = tuple(
        family_name
        for family_name in _as_string_list(payload.get("families"))
        if family_name in duplication_families
    )
    return configured_families or duplication_families
