"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _as_mapping
from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.composite_dependency_storage_ref import (
    _add_composite_dependency_surface,
    _composite_dependency_storage_ref,
    _link_composite_dependency_surface,
)
from memory.graph.sync_pkg.graph_contexts import CompositePipelineContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot

__all__ = [
    "_add_composite_dependency_surfaces",
    "_composite_seed_storage_ref",
    "_link_composite_seed_surface",
]


def _composite_seed_storage_ref(composite_payload: dict[str, object]) -> str | None:
    seed_payload = _as_mapping(composite_payload.get("seed"))
    seed_table = seed_payload.get("silver_table")
    if not isinstance(seed_table, str) or not seed_table.strip():
        return None
    return seed_table.strip()


def _link_composite_seed_surface(
    snapshot: GraphSnapshot,
    context: CompositePipelineContext,
    seed_surface: NodeKey,
) -> None:
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key,
            "DEPENDS_ON",
            seed_surface,
            provenance="storage_surfaces",
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            seed_surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )


def _add_composite_dependency_surfaces(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    dependencies: object,
) -> list[str]:
    source_storage_refs: list[str] = []
    if not isinstance(dependencies, list):
        return source_storage_refs
    for dependency in dependencies:
        storage_ref = _composite_dependency_storage_ref(dependency)
        if storage_ref is None:
            continue
        source_storage_refs.append(storage_ref)
        dependency_surface = _add_composite_dependency_surface(
            snapshot, project, context, storage_ref
        )
        _link_composite_dependency_surface(
            snapshot, context, dependency_surface, dependency
        )
    return source_storage_refs
