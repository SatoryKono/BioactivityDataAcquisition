"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _as_mapping,
    _normalized_text_list,
    _optional_text,
)
from memory.graph.sync_pkg._core_models import (
    EntityScope,
    NodeKey,
    SchemaFieldSpec,
    StorageSurfaceSpec,
)
from memory.graph.sync_pkg.graph_contexts import (
    CompositeOutputConfig,
    CompositePipelineContext,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.mapping_io import _read_yaml
from memory.graph.sync_pkg.merge_field_validation_item import (
    _add_schema_field_surface,
    _add_storage_surface,
)
from memory.graph.sync_pkg.merge_storage_layer_config import (
    _storage_ref_from_output_path,
)

__all__ = [
    "_add_composite_output_field_nodes",
    "_add_composite_output_surface",
    "_base_pipeline_storage_config",
    "_composite_output_storage_ref",
]


def _composite_output_storage_ref(
    output_payload: dict[str, object], layer_name: str
) -> str | None:
    output_path = output_payload.get(layer_name)
    if not isinstance(output_path, str) or not output_path.strip():
        return None
    return _storage_ref_from_output_path(output_path)


def _add_composite_output_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
    *,
    layer_name: str,
) -> NodeKey | None:
    storage_ref = _composite_output_storage_ref(
        output_config.output_payload, layer_name
    )
    if storage_ref is None:
        return None
    surface = _add_storage_surface(
        snapshot,
        project,
        StorageSurfaceSpec(
            ref=storage_ref,
            summary=f"{layer_name.title()} output surface for composite pipeline `{context.composite_name}`.",
            layer=layer_name,
            today=context.today,
            storage_kind="composite_layer_output",
            scope=EntityScope(pipeline_name=context.composite_name),
            config_version=context.composite_version,
            semantic_properties={
                "merge_strategy": _optional_text(
                    output_config.merge_payload.get("strategy")
                ),
                "sort_by": _normalized_text_list(
                    _as_mapping(output_config.merge_payload.get("sort_by")).get(
                        layer_name
                    )
                ),
            },
        ),
    )
    if context.pipeline_key in snapshot.nodes:
        snapshot.add_relation(
            context.pipeline_key, "WRITES_TO", surface, provenance="storage_surfaces"
        )
    if context.config_artifact in snapshot.nodes:
        snapshot.add_relation(
            surface,
            "DEFINED_BY",
            context.config_artifact,
            provenance="storage_surfaces",
        )
    return surface


def _add_composite_output_field_nodes(
    snapshot: GraphSnapshot,
    project: NodeKey,
    context: CompositePipelineContext,
    output_config: CompositeOutputConfig,
    *,
    composite_scope: EntityScope,
    surface: NodeKey,
) -> dict[str, NodeKey]:
    layer_field_nodes: dict[str, NodeKey] = {}
    for field_group, field_name in output_config.group_fields:
        candidate_sources = [
            ref
            for ref in output_config.source_storage_refs
            if field_name in output_config.schema_fields_by_storage.get(ref, {})
        ]
        field_node = _add_schema_field_surface(
            snapshot,
            project,
            surface,
            field_name=field_name,
            field_group=field_group,
            today=context.today,
            spec=SchemaFieldSpec(
                scope=composite_scope,
                drift_classification="inherited_field"
                if candidate_sources
                else "composite_only",
                source_storage_refs=candidate_sources if candidate_sources else None,
            ),
        )
        layer_field_nodes[field_name] = field_node
        if context.config_artifact in snapshot.nodes:
            snapshot.add_relation(
                field_node,
                "DEFINED_BY",
                context.config_artifact,
                provenance="schema_fields",
            )
        for source_ref in candidate_sources:
            source_field = output_config.schema_fields_by_storage.get(
                source_ref, {}
            ).get(field_name)
            if source_field is not None:
                snapshot.add_relation(
                    field_node,
                    "DERIVES_FIELD_FROM",
                    source_field,
                    provenance="schema_fields",
                )
    return layer_field_nodes


def _base_pipeline_storage_config(
    root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    base_pipeline_path = root / "configs" / "base" / "pipeline.yaml"
    base_payload = (
        _read_yaml(base_pipeline_path) if base_pipeline_path.is_file() else {}
    )
    base_sink = _as_mapping(base_payload.get("sink"))
    return base_payload, base_sink
