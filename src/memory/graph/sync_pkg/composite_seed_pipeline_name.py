"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.pipeline_normalization_targets import (
    _link_pipeline_normalization_modules,
    _normalization_edge_config,
    _pipeline_normalization_modules,
    _pipeline_normalization_targets,
)

__all__ = [
    "_add_pipeline_normalization_edges",
    "_composite_dependency_pipeline_keys",
    "_composite_seed_pipeline_name",
]


def _composite_seed_pipeline_name(seed: object) -> str | None:
    if not isinstance(seed, dict):
        return None
    seed_pipeline = seed.get("pipeline")
    return seed_pipeline if isinstance(seed_pipeline, str) else None


def _composite_dependency_pipeline_keys(
    dependencies: object,
    pipeline_nodes: dict[str, NodeKey],
) -> tuple[NodeKey, ...]:
    if not isinstance(dependencies, list):
        return ()
    keys: list[NodeKey] = []
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            continue
        dependency_pipeline = dependency.get("pipeline")
        if (
            isinstance(dependency_pipeline, str)
            and dependency_pipeline in pipeline_nodes
        ):
            keys.append(pipeline_nodes[dependency_pipeline])
    return tuple(keys)


def _add_pipeline_normalization_edges(
    snapshot: GraphSnapshot,
    pipeline_nodes: dict[str, NodeKey],
    memory_mapping: dict[str, object],
) -> None:
    normalization_mapping = memory_mapping.get("normalization")
    if not isinstance(normalization_mapping, dict):
        return

    (
        relation_type,
        entity_relation_type,
        default_entity_modules,
        default_composite_modules,
        pipeline_overrides,
    ) = _normalization_edge_config(normalization_mapping)

    for (
        pipeline_name,
        pipeline_key,
        pipeline_kind,
        entity_key,
    ) in _pipeline_normalization_targets(
        snapshot,
        pipeline_nodes,
    ):
        modules = _pipeline_normalization_modules(
            pipeline_name,
            pipeline_kind,
            pipeline_overrides,
            default_entity_modules,
            default_composite_modules,
        )
        _link_pipeline_normalization_modules(
            snapshot,
            pipeline_key,
            entity_key=entity_key,
            pipeline_kind=pipeline_kind,
            modules=modules,
            relation_type=relation_type,
            entity_relation_type=entity_relation_type,
        )
