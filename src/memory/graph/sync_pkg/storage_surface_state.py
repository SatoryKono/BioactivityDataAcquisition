"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import (
    _as_mapping,
    _normalized_text_list,
    _optional_text,
)
from memory.graph.sync_pkg._core_models import (
    ControlPlaneArtifactSpec,
    EntityScope,
    JsonValue,
    NodeKey,
    StorageSurfaceSpec,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_storage_layer_config import _storage_ref_identity

__all__ = [
    "_add_control_plane_artifact_surface",
    "_entity_pipeline_scope",
    "_scd_config_columns",
    "_storage_surface_semantic_properties",
    "_storage_surface_state",
]


def _storage_surface_state(
    snapshot: GraphSnapshot,
    spec: StorageSurfaceSpec,
) -> tuple[str, str | None, str | None, list[str], list[str], str, str | None]:
    key = NodeKey("storage_surface", spec.ref)
    existing = snapshot.nodes.get(key)
    inferred_layer, inferred_provider, inferred_entity = _storage_ref_identity(spec.ref)
    provider = spec.scope.provider or inferred_provider
    entity = spec.scope.entity or inferred_entity
    pipeline_name = spec.scope.pipeline_name
    layer = spec.layer or inferred_layer or ""

    existing_roles_raw = (
        existing.properties.get("storage_roles") if existing is not None else None
    )
    existing_roles = _normalized_text_list(existing_roles_raw) or []
    storage_roles = sorted({*existing_roles, spec.storage_kind})

    existing_pipeline_names_raw = (
        existing.properties.get("pipeline_names") if existing is not None else None
    )
    existing_pipeline_names = _normalized_text_list(existing_pipeline_names_raw) or []
    pipeline_names: list[str] = sorted(
        {
            *existing_pipeline_names,
            *([pipeline_name] if pipeline_name is not None else []),
        }
    )

    primary_storage_kind = (
        _optional_text(existing.properties.get("storage_kind"))
        if existing is not None
        else None
    ) or spec.storage_kind
    primary_pipeline_name = (
        _optional_text(existing.properties.get("pipeline_name"))
        if existing is not None
        else None
    ) or pipeline_name
    return (
        layer,
        provider,
        entity,
        storage_roles,
        pipeline_names,
        primary_storage_kind,
        primary_pipeline_name,
    )


def _storage_surface_semantic_properties(
    spec: StorageSurfaceSpec,
) -> dict[str, JsonValue]:
    # Merge curated semantic properties with the normalized top-level storage fields
    # without passing duplicate keyword arguments into add_node().
    semantic_properties = dict(spec.semantic_properties)
    explicit_semantic_fields: dict[str, JsonValue] = {
        "partition_by": spec.partition_by,
        "sort_by": spec.sort_by,
        "on_schema_mismatch": spec.on_schema_mismatch,
        "versioning_mode": spec.versioning_mode,
        "version_column": spec.version_column,
        "current_flag_column": spec.current_flag_column,
        "valid_from_column": spec.valid_from_column,
        "valid_to_column": spec.valid_to_column,
        "merge_strategy": spec.merge_strategy,
    }
    for field_name, field_value in explicit_semantic_fields.items():
        if field_value is not None:
            semantic_properties[field_name] = field_value
    return semantic_properties


def _add_control_plane_artifact_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    spec: ControlPlaneArtifactSpec,
) -> NodeKey:
    artifact = snapshot.add_node(
        "control_plane_artifact_surface",
        spec.artifact_name,
        summary=spec.summary,
        artifact_family=spec.artifact_family,
        artifact_kind=spec.artifact_kind,
        storage_ref=spec.storage_ref,
        artifact_format=spec.artifact_format,
        key_template=spec.key_template,
        last_verified=spec.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    snapshot.add_relation(
        project, "HAS_CONTROL_PLANE_ARTIFACT", artifact, provenance="runtime_evidence"
    )
    return artifact


def _entity_pipeline_scope(
    provider_name: str, entity_name: str, pipeline_name: str
) -> EntityScope:
    return EntityScope(
        provider=provider_name, entity=entity_name, pipeline_name=pipeline_name
    )


def _scd_config_columns(layer_config: dict[str, object]) -> dict[str, str | None]:
    scd_config = _as_mapping(layer_config.get("scd_config"))
    return {
        "version_column": _optional_text(scd_config.get("version_col")),
        "current_flag_column": _optional_text(scd_config.get("current_flag_col")),
        "valid_from_column": _optional_text(scd_config.get("valid_from_col")),
        "valid_to_column": _optional_text(scd_config.get("valid_to_col")),
    }
