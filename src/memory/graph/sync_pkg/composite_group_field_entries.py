"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalized_text_list, _optional_text
from memory.graph.sync_pkg._core_models import EntityScope, NodeKey, StorageSurfaceSpec
from memory.graph.sync_pkg.composite_seed_storage_ref import (
    _composite_seed_storage_ref,
    _link_composite_seed_surface,
)
from memory.graph.sync_pkg.graph_contexts import CompositePipelineContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_field_validation_item import _add_storage_surface

__all__ = [
    "_add_composite_seed_surface",
    "_composite_group_field_entries",
]


def _composite_group_field_entries(item: object) -> list[tuple[str, str]]:
    if not isinstance(item, dict):
        return []
    group_name = _optional_text(item.get("name"))
    if group_name is None:
        return []
    return [
        (group_name, field_name)
        for field_name in (_normalized_text_list(item.get("fields")) or [])
    ]


def _add_composite_seed_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    composite_payload: dict[str, object],
    has_dependency_pipelines: bool,
) -> list[str]:
    seed_storage_ref = _composite_seed_storage_ref(composite_payload)
    if seed_storage_ref is None:
        return []
    seed_surface = NodeKey("storage_surface", seed_storage_ref)
    if has_dependency_pipelines or seed_surface not in snapshot.nodes:
        seed_surface = _add_storage_surface(
            snapshot,
            project,
            StorageSurfaceSpec(
                ref=seed_storage_ref,
                summary=f"Seed storage surface for composite pipeline `{context.composite_name}`.",
                layer="silver",
                today=context.today,
                storage_kind="composite_seed_input",
                scope=EntityScope(pipeline_name=context.composite_name),
            ),
        )
    _link_composite_seed_surface(snapshot, context, seed_surface)
    return [seed_storage_ref]
