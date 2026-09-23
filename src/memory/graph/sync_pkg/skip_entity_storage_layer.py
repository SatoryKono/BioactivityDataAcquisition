"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalized_text_list, _optional_text
from memory.graph.sync_pkg._core_models import EntityScope, NodeKey, StorageSurfaceSpec
from memory.graph.sync_pkg.graph_contexts import EntityPipelineContext
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_field_validation_item import _add_storage_surface
from memory.graph.sync_pkg.merge_storage_layer_config import _storage_schema_properties
from memory.graph.sync_pkg.storage_surface_state import _scd_config_columns

__all__ = [
    "_create_entity_storage_layer_surface",
    "_link_entity_storage_layer_backing",
    "_skip_entity_storage_layer",
]


def _skip_entity_storage_layer(
    layer_name: str, layer_config: dict[str, object]
) -> bool:
    return layer_name == "gold" and not bool(layer_config.get("enabled", True))


def _create_entity_storage_layer_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: EntityPipelineContext,
    payload: dict[str, object],
    *,
    scope: EntityScope,
    layer_name: str,
    layer_config: dict[str, object],
) -> NodeKey:
    storage_ref = f"{layer_name}/{context.provider_name}/{context.entity_name}"
    return _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"{layer_name.title()} storage surface for `{context.pipeline_name}`.",
            layer=layer_name,
            today=context.today,
            storage_kind="entity_layer_output",
            scope=scope,
            format_name=str(layer_config.get("format"))
            if layer_config.get("format") is not None
            else None,
            mode=str(layer_config.get("mode"))
            if layer_config.get("mode") is not None
            else None,
            enabled=bool(layer_config.get("enabled", True)),
            retention_days=context.retention_days,
            config_version=context.config_version,
            quality_version=context.quality_version,
            partition_by=_normalized_text_list(layer_config.get("partition_by")),
            sort_by=_normalized_text_list(layer_config.get("sort_by")),
            on_schema_mismatch=_optional_text(layer_config.get("on_schema_mismatch")),
            versioning_mode=_optional_text(layer_config.get("mode")),
            semantic_properties={
                **_scd_config_columns(layer_config),
                **_storage_schema_properties(payload, layer_name=layer_name),
            },
        ),
    )


def _link_entity_storage_layer_backing(
    snapshot: GraphSnapshot,
    context: EntityPipelineContext,
    surface: NodeKey,
) -> None:
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.entity_key in snapshot.nodes:
        snapshot.add_relation(
            context.entity_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )
