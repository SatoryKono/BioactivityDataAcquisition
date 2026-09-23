"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import (
    AnalysisLabelSets,
    NodeKey,
    RetirementAnalysisConfig,
)
from memory.graph.sync_pkg.analysis_source import _analysis_read_source_text
from memory.graph.sync_pkg.complexity_marker_buckets import _retirement_scores
from memory.graph.sync_pkg.curated_quality_gates import _collect_analysis_anchor_nodes
from memory.graph.sync_pkg.curated_script_clusters import (
    _analysis_family_for_source_path,
)
from memory.graph.sync_pkg.graph_contexts import (
    DuplicateFamilyConfig,
    SurfaceRelationIndexes,
)
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot
from memory.graph.sync_pkg.retirement_marker_sets import (
    _analysis_anchor_counts,
    _retirement_marker_sets,
    _retirement_score_inputs,
    _retirement_surface_payload,
)

__all__ = [
    "_evaluate_retirement_surface",
    "_retirement_analysis_label_sets",
    "_retirement_candidate_nodes",
]


def _retirement_analysis_label_sets() -> AnalysisLabelSets:
    return AnalysisLabelSets(
        ignored_relation_types={
            "DECLARES",
            "OVERRIDES",
            "SAME_SHAPE_AS",
            "CONTAINS",
            "BACKS",
            "HOUSES",
            "CANDIDATE_FOR_REMOVAL",
        },
        runtime_labels={
            "pipeline_surface",
            "execution_path",
            "alert_surface",
            "adapter_surface",
            "adapter_impl_surface",
        },
        config_labels={
            "entity_config",
            "composite_config",
            "provider_surface",
            "contract_surface",
            "port_surface",
        },
        doc_labels={
            "policy_surface",
            "doc_source_surface",
            "doc_artifact",
            "dashboard_surface",
            "quality_gate",
        },
        test_labels={"test_surface", "test_artifact"},
    )


def _retirement_candidate_nodes(
    snapshot: GraphSnapshot,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
) -> list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]]:
    analysis_labels = {
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
    }
    candidate_nodes: list[tuple[GraphNode, str, DuplicateFamilyConfig, NodeKey]] = []
    for node in sorted(
        snapshot.nodes.values(), key=lambda item: (item.key.label, item.key.name)
    ):
        if node.key.label not in analysis_labels:
            continue
        source_path = node.properties.get("source_path")
        if not isinstance(source_path, str) or not source_path.endswith(".py"):
            continue
        family = _analysis_family_for_source_path(
            source_path, duplication_config, family_cache
        )
        if family is None or family.name not in family_names:
            continue
        module_key = (
            node.key
            if node.key.label == "module_surface"
            else NodeKey("module_surface", source_path)
        )
        if module_key not in snapshot.nodes:
            continue
        candidate_nodes.append((node, source_path, family, module_key))
    return candidate_nodes


def _evaluate_retirement_surface(
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
    anchors = _collect_analysis_anchor_nodes(
        snapshot,
        indexes,
        node.key,
        module_key,
        label_sets,
    )
    anchor_counts = _analysis_anchor_counts(anchors)
    source_text = _analysis_read_source_text(root, source_path, text_cache)
    wip_markers, deprecation_markers = _retirement_marker_sets(config, source_text)
    recent_age_days = age_cache.get(source_path)
    cycle_score, deletion_score, only_test_referenced = _retirement_scores(
        config,
        _retirement_score_inputs(
            anchor_counts,
            recent_age_days=recent_age_days,
            wip_markers=wip_markers,
            deprecation_markers=deprecation_markers,
        ),
    )
    return _retirement_surface_payload(
        family_name=family_name,
        anchors=anchors,
        anchor_counts=anchor_counts,
        wip_markers=wip_markers,
        deprecation_markers=deprecation_markers,
        recent_age_days=recent_age_days,
        cycle_score=cycle_score,
        deletion_score=deletion_score,
        only_test_referenced=only_test_referenced,
    )
