"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_pipeline_dependency_keys import (
    _build_normalization_pipeline_evidence,
    _composite_pipeline_dependency_keys,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.iter_normalization_evidence_updates import (
    _iter_normalization_evidence_updates,
)
from memory.graph.sync_pkg.normalization_evidence_update_payload import (
    _link_normalization_registry_module,
)

__all__ = [
    "_add_pipeline_normalization_evidence",
    "_link_composite_pipeline_dependencies",
]


def _link_composite_pipeline_dependencies(
    snapshot: GraphSnapshot,
    pipeline: NodeKey,
    composite_payload: object,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    for dependency_key in _composite_pipeline_dependency_keys(
        composite_payload, pipeline_nodes
    ):
        snapshot.add_relation(
            pipeline,
            "DEPENDS_ON",
            dependency_key,
            provenance="impact_pipelines",
        )


def _add_pipeline_normalization_evidence(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
) -> None:
    evidence_by_pipeline = _build_normalization_pipeline_evidence()
    for (
        pipeline_name,
        entity_key,
        update_payload,
    ) in _iter_normalization_evidence_updates(
        pipeline_nodes,
        evidence_by_pipeline,
    ):
        pipeline = snapshot.add_node(
            "pipeline_surface", pipeline_name, **update_payload
        )
        if entity_key in snapshot.nodes:
            snapshot.add_node("entity_config", pipeline_name, **update_payload)
        _link_normalization_registry_module(
            snapshot,
            pipeline,
            entity_key=entity_key,
            module_path=update_payload["normalization_profile_module_path"],
        )
