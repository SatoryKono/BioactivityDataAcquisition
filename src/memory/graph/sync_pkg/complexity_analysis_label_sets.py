"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import AnalysisLabelSets, NodeKey
from memory.graph.sync_pkg.analysis_source import _analysis_read_source_text
from memory.graph.sync_pkg.curated_script_clusters import (
    _analysis_family_for_source_path,
)
from memory.graph.sync_pkg.graph_contexts import DuplicateFamilyConfig
from memory.graph.sync_pkg.graph_snapshot import GraphNode, GraphSnapshot

__all__ = [
    "_complexity_analysis_label_sets",
    "_complexity_surface_prerequisites",
]


def _complexity_analysis_label_sets() -> AnalysisLabelSets:
    return AnalysisLabelSets(
        ignored_relation_types={
            "DECLARES",
            "OVERRIDES",
            "SAME_SHAPE_AS",
            "CONTAINS",
            "BACKS",
            "HOUSES",
            "CANDIDATE_FOR_REMOVAL",
            "HAS_COMPLEXITY_SIGNAL",
            "CANDIDATE_FOR_SIMPLIFICATION",
            "JUSTIFIED_BY_RUNTIME",
            "BLOCKED_BY_VARIANCE",
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


def _complexity_surface_prerequisites(
    snapshot: GraphSnapshot,
    root: Path,
    node: GraphNode,
    *,
    duplication_config: dict[str, object],
    family_names: set[str],
    family_cache: dict[str, DuplicateFamilyConfig | None],
    text_cache: dict[str, str],
) -> tuple[str, DuplicateFamilyConfig, NodeKey, str] | None:
    analysis_labels = {
        "module_surface",
        "class_surface",
        "function_surface",
        "method_surface",
    }
    if node.key.label not in analysis_labels:
        return None
    source_path = node.properties.get("source_path")
    if not isinstance(source_path, str) or not source_path.endswith(".py"):
        return None
    family = _analysis_family_for_source_path(
        source_path, duplication_config, family_cache
    )
    if family is None or family.name not in family_names:
        return None
    module_key = (
        node.key
        if node.key.label == "module_surface"
        else NodeKey("module_surface", source_path)
    )
    if module_key not in snapshot.nodes:
        return None
    source_text = _analysis_read_source_text(root, source_path, text_cache)
    return source_path, family, module_key, source_text
