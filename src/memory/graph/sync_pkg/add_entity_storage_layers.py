"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import JsonValue, NodeKey
from memory.graph.sync_pkg.add_entity_storage_layer import _add_entity_storage_layer
from memory.graph.sync_pkg.graph_contexts import EntityPipelineContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.storage_surface_state import _entity_pipeline_scope

__all__ = [
    "_add_entity_storage_layers",
]


def _add_entity_storage_layers(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
) -> tuple[dict[str, NodeKey], dict[str, dict[str, NodeKey]]]:
    layer_nodes: dict[str, NodeKey] = {}
    field_nodes_by_layer: dict[str, dict[str, NodeKey]] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    for layer_name in ("bronze", "silver", "gold"):
        _add_entity_storage_layer(
            snapshot,
            project,
            context,
            payload,
            base_sink,
            pipeline_sink,
            quality_index,
            scope=scope,
            layer_name=layer_name,
            layer_nodes=layer_nodes,
            field_nodes_by_layer=field_nodes_by_layer,
        )
    return layer_nodes, field_nodes_by_layer
