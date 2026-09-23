"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _normalized_text_list, _optional_text
from memory.graph.sync_pkg._core_models import (
    JsonValue,
    NodeKey,
    SchemaFieldSpec,
    StorageSurfaceSpec,
)
from memory.graph.sync_pkg.graph_snapshot import GraphSnapshot
from memory.graph.sync_pkg.merge_storage_layer_config import _infer_storage_format
from memory.graph.sync_pkg.storage_surface_state import (
    _storage_surface_semantic_properties,
    _storage_surface_state,
)

__all__ = [
    "_add_schema_field_surface",
    "_add_storage_surface",
    "_merge_field_validation_item",
    "_merge_key_nullability_item",
    "_merged_maintenance_config",
]


def _merge_field_validation_item(
    index: dict[str, dict[str, JsonValue]],
    item: object,
) -> None:
    if not isinstance(item, dict):
        return
    field_name = _optional_text(item.get("field"))
    if field_name is None:
        return
    entry = index.setdefault(field_name, {})
    validation_types = set(_normalized_text_list(entry.get("validation_types")) or [])
    validation_type = _optional_text(item.get("type"))
    if validation_type is not None:
        validation_types.add(validation_type)
    entry["validation_types"] = sorted(validation_types) if validation_types else None
    if validation_type == "required" and item.get("nullable") is False:
        entry["required_in_quality"] = True


def _merge_key_nullability_item(
    index: dict[str, dict[str, JsonValue]],
    item: object,
) -> None:
    if not isinstance(item, dict):
        return
    field_name = _optional_text(item.get("field"))
    if field_name is None:
        return
    if item.get("nullable") is False:
        entry = index.setdefault(field_name, {})
        entry["required_in_quality"] = True


def _add_schema_field_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    storage_key: NodeKey,
    *,
    field_name: str,
    field_group: str,
    today: str,
    spec: SchemaFieldSpec = SchemaFieldSpec(),
) -> NodeKey:
    storage_node = snapshot.nodes.get(storage_key)
    storage_ref = storage_key.name
    key = NodeKey("schema_field_surface", f"{storage_ref}::{field_name}")
    surface = snapshot.add_node(
        "schema_field_surface",
        key.name,
        summary=f"Schema field `{field_name}` for storage surface `{storage_ref}`.",
        field_name=field_name,
        field_group=field_group,
        storage_ref=storage_ref,
        storage_layer=(
            storage_node.properties.get("layer") if storage_node is not None else None
        ),
        provider=spec.scope.provider
        or (
            storage_node.properties.get("provider")
            if storage_node is not None
            else None
        ),
        entity=spec.scope.entity
        or (
            storage_node.properties.get("entity") if storage_node is not None else None
        ),
        pipeline_name=spec.scope.pipeline_name
        or (
            storage_node.properties.get("pipeline_name")
            if storage_node is not None
            else None
        ),
        contract_ref=spec.contract_ref,
        required_in_quality=spec.required_in_quality,
        validation_types=spec.validation_types,
        drift_classification=spec.drift_classification,
        source_storage_refs=spec.source_storage_refs,
        source_kind="schema_field_surface",
        last_verified=today,
        ingest_wave="repo_sync_v1",
        confidence="high",
    )
    if spec.drift_classification is None:
        snapshot.nodes[key].properties.setdefault("drift_classification", None)
    snapshot.add_relation(
        project, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
    )
    snapshot.add_relation(
        storage_key, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
    )
    if spec.contract_ref is not None:
        contract_key = NodeKey("contract_surface", spec.contract_ref)
        if contract_key in snapshot.nodes:
            snapshot.add_relation(
                contract_key, "HAS_SCHEMA_FIELD", surface, provenance="schema_fields"
            )
    return surface


def _merged_maintenance_config(
    base_payload: dict[str, object],
    payload: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = {}
    base_maintenance = base_payload.get("maintenance")
    if isinstance(base_maintenance, dict):
        merged.update(base_maintenance)
    payload_maintenance = payload.get("maintenance")
    if isinstance(payload_maintenance, dict):
        merged.update(payload_maintenance)
    return merged


def _add_storage_surface(
    snapshot: GraphSnapshot,
    project: NodeKey,
    spec: StorageSurfaceSpec,
) -> NodeKey:
    (
        layer,
        provider,
        entity,
        storage_roles,
        pipeline_names,
        primary_storage_kind,
        primary_pipeline_name,
    ) = _storage_surface_state(snapshot, spec)
    semantic_properties = _storage_surface_semantic_properties(spec)
    format_name = spec.format_name or _infer_storage_format(spec.ref)
    surface = snapshot.add_node(
        "storage_surface",
        spec.ref,
        summary=spec.summary,
        layer=layer,
        storage_kind=primary_storage_kind,
        storage_roles=storage_roles,
        provider=provider,
        entity=entity,
        pipeline_name=primary_pipeline_name,
        pipeline_names=pipeline_names if pipeline_names else None,
        format=format_name,
        mode=spec.mode,
        enabled=spec.enabled,
        retention_days=spec.retention_days,
        config_version=spec.config_version,
        quality_version=spec.quality_version,
        last_verified=spec.today,
        ingest_wave="repo_sync_v1",
        confidence="high",
        **semantic_properties,
    )
    snapshot.add_relation(
        project, "HAS_STORAGE_SURFACE", surface, provenance="storage_surfaces"
    )
    return surface
