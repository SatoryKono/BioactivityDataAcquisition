"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_models import EntityScope, JsonValue, NodeKey
from memory.graph.sync_pkg.add_file_structure_surfaces import (
    _add_entity_layer_field_nodes,
)
from memory.graph.sync_pkg.graph_contexts import (
    EntityLayerFieldContext,
    EntityPipelineContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_storage_layer_config import _merge_storage_layer_config
from memory.graph.sync_pkg.skip_entity_storage_layer import (
    _create_entity_storage_layer_surface,
    _link_entity_storage_layer_backing,
    _skip_entity_storage_layer,
)

__all__ = [
    "_add_entity_storage_layer",
]


def _add_entity_storage_layer(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    quality_index: dict[str, dict[str, JsonValue]],
    *,
    scope: EntityScope,
    layer_name: str,
    layer_nodes: dict[str, NodeKey],
    field_nodes_by_layer: dict[str, dict[str, NodeKey]],
) -> None:
    layer_config = _merge_storage_layer_config(base_sink, pipeline_sink, layer_name)
    if _skip_entity_storage_layer(layer_name, layer_config):
        return
    surface = _create_entity_storage_layer_surface(
        snapshot,
        project,
        context,
        payload,
        scope=scope,
        layer_name=layer_name,
        layer_config=layer_config,
    )
    layer_nodes[layer_name] = surface
    _link_entity_storage_layer_backing(snapshot, context, surface)
    field_nodes_by_layer[layer_name] = _add_entity_layer_field_nodes(
        snapshot,
        project,
        context,
        EntityLayerFieldContext(
            payload=payload,
            surface=surface,
            layer_name=layer_name,
            quality_index=quality_index,
            layer_config=layer_config,
        ),
    )
