"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_models import NodeKey
from memory.graph.sync_pkg.add_entity_regular_field_node import (
    _add_entity_metadata_field_node,
    _add_entity_regular_field_node,
)
from memory.graph.sync_pkg.file_structure import _file_structure_config
from memory.graph.sync_pkg.file_structure_zone_roots import _file_structure_zone_roots
from memory.graph.sync_pkg.graph_contexts import (
    EntityLayerFieldContext,
    EntityPipelineContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _load_memory_mapping
from memory.graph.sync_pkg.materialize_file_structure import _materialize_file_structure
from memory.graph.sync_pkg.merge_storage_layer_config import _filtered_group_fields
from memory.graph.sync_pkg.storage_surface_state import (
    _entity_pipeline_scope,
    _scd_config_columns,
)

__all__ = [
    "_add_entity_layer_field_nodes",
    "_add_file_structure_surfaces",
]


def _add_file_structure_surfaces(
    snapshot: GraphSnapshot, root: Path, project: NodeKey, today: str
) -> None:
    memory_mapping = _load_memory_mapping(root)
    config = _file_structure_config(memory_mapping)
    zone_roots = _file_structure_zone_roots(config)
    _materialize_file_structure(snapshot, root, project, today, zone_roots, config)


def _add_entity_layer_field_nodes(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
) -> dict[str, NodeKey]:
    layer_field_nodes: dict[str, NodeKey] = {}
    scope = _entity_pipeline_scope(
        context.provider_name, context.entity_name, context.pipeline_name
    )
    drift_classification = (
        "staging_projection" if layer_context.layer_name == "bronze" else None
    )
    for field_group, field_name in _filtered_group_fields(
        layer_context.payload, layer_name=layer_context.layer_name
    ):
        _add_entity_regular_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            field_group=field_group,
            field_name=field_name,
            drift_classification=drift_classification,
            layer_field_nodes=layer_field_nodes,
        )
    for metadata_field in _scd_config_columns(layer_context.layer_config).values():
        _add_entity_metadata_field_node(
            snapshot,
            project,
            context,
            layer_context,
            scope=scope,
            metadata_field=metadata_field,
            layer_field_nodes=layer_field_nodes,
        )
    return layer_field_nodes
