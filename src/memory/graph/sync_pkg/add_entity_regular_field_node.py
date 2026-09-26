"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalized_text_list
from memory.graph.sync_pkg._core_models import EntityScope, NodeKey, SchemaFieldSpec
from memory.graph.sync_pkg.graph_contexts import (
    EntityLayerFieldContext,
    EntityPipelineContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.link_schema_field_definition import (
    _link_schema_field_definition,
)
from memory.graph.sync_pkg.merge_field_validation_item import _add_schema_field_surface

__all__ = [
    "_add_entity_metadata_field_node",
    "_add_entity_regular_field_node",
]


def _add_entity_regular_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    field_group: str,
    field_name: str,
    drift_classification: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    field_quality = layer_context.quality_index.get(field_name, {})
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=field_name,
        field_group=field_group,
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            required_in_quality=(
                bool(field_quality.get("required_in_quality"))
                if field_quality.get("required_in_quality") is not None
                else None
            ),
            validation_types=_normalized_text_list(
                field_quality.get("validation_types")
            ),
            drift_classification=drift_classification,
        ),
    )
    layer_field_nodes[field_name] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)


def _add_entity_metadata_field_node(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    layer_context: EntityLayerFieldContext,
    *,
    scope: EntityScope,
    metadata_field: str | None,
    layer_field_nodes: dict[str, NodeKey],
) -> None:
    if metadata_field is None or metadata_field in layer_field_nodes:
        return
    field_node = _add_schema_field_surface(
        snapshot,
        project,
        layer_context.surface,
        field_name=metadata_field,
        field_group="system",
        today=context.today,
        spec=SchemaFieldSpec(
            contract_ref=context.contract_ref,
            scope=scope,
            drift_classification="runtime_metadata",
        ),
    )
    layer_field_nodes[metadata_field] = field_node
    _link_schema_field_definition(snapshot, field_node, context.config_artifact)
