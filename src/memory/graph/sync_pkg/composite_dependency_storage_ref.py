"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import EntityScope, NodeKey, StorageSurfaceSpec
from memory.graph.sync_pkg.composite_output_storage_ref import (
    _add_composite_output_field_nodes,
    _add_composite_output_surface,
)
from memory.graph.sync_pkg.graph_contexts import (
    CompositeOutputConfig,
    CompositePipelineContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_field_validation_item import _add_storage_surface

__all__ = [
    "_add_composite_dependency_surface",
    "_add_composite_output_layers",
    "_composite_dependency_storage_ref",
    "_link_composite_dependency_surface",
]


def _composite_dependency_storage_ref(dependency: object) -> str | None:
    if not isinstance(dependency, dict):
        return None
    silver_table = dependency.get("silver_table")
    if not isinstance(silver_table, str) or not silver_table.strip():
        return None
    return silver_table.strip()


def _add_composite_dependency_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    storage_ref: str,
) -> NodeKey:
    return _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"Dependency storage surface for composite pipeline `{context.composite_name}`.",
            layer="silver",
            today=context.today,
            storage_kind="composite_dependency_input",
            scope=EntityScope(pipeline_name=context.composite_name),
        ),
    )


def _link_composite_dependency_surface(
    snapshot: GraphSnapshot,
    context: CompositePipelineContext,
    dependency_surface: NodeKey,
    dependency: object,
) -> None:
    required = (
        bool(dependency.get("required", False))
        if isinstance(dependency, dict)
        else False
    )
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key,
            "DEPENDS_ON",
            dependency_surface,
            provenance="storage_surfaces",
            required=required,
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            dependency_surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )


def _add_composite_output_layers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
) -> tuple[dict[str, NodeKey], dict[str, dict[str, NodeKey]]]:
    layer_nodes: dict[str, NodeKey] = {}
    field_nodes_by_layer: dict[str, dict[str, NodeKey]] = {}
    composite_scope = EntityScope(
        provider="composite",
        entity=context.composite_name.removeprefix("composite_"),
        pipeline_name=context.composite_name,
    )
    for layer_name in ("silver", "gold"):
        surface = _add_composite_output_surface(
            snapshot,
            project,
            context,
            output_config,
            layer_name=layer_name,
        )
        if surface is None:
            continue
        layer_nodes[layer_name] = surface
        field_nodes_by_layer[layer_name] = _add_composite_output_field_nodes(
            snapshot,
            project,
            context,
            output_config,
            composite_scope=composite_scope,
            surface=surface,
        )
    return layer_nodes, field_nodes_by_layer
