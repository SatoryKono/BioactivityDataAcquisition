"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from memory.graph.sync_pkg._core_convert import (
    _as_iterable,
    _as_mapping,
    _normalized_text_list,
    _optional_text,
)
from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_entity_pipeline_sink_config",
    "_filtered_group_fields",
    "_infer_storage_format",
    "_merge_sink_config",
    "_merge_storage_layer_config",
    "_schema_group_field_map",
    "_storage_ref_from_output_path",
    "_storage_ref_identity",
    "_storage_schema_properties",
]


def _merge_storage_layer_config(
    base_sink: dict[str, object],
    pipeline_sink: dict[str, object],
    layer_name: str,
) -> dict[str, object]:
    merged: dict[str, object] = {}
    base_layer = base_sink.get(layer_name)
    if isinstance(base_layer, dict):
        merged.update(base_layer)
    override_layer = pipeline_sink.get(layer_name)
    if isinstance(override_layer, dict):
        merged.update(override_layer)
    return merged


def _merge_sink_config(
    base_sink: dict[str, object],
    override_sink: dict[str, object],
) -> dict[str, object]:
    merged: dict[str, object] = dict(base_sink)
    for raw_layer_name, override_layer in override_sink.items():
        layer_name = str(raw_layer_name)
        base_layer = merged.get(layer_name)
        if isinstance(base_layer, dict) and isinstance(override_layer, dict):
            layer_config = dict(base_layer)
            layer_config.update(override_layer)
            merged[layer_name] = layer_config
        else:
            merged[layer_name] = override_layer
    return merged


def _entity_pipeline_sink_config(payload: dict[str, object]) -> dict[str, object]:
    direct_sink = _as_mapping(payload.get("sink"))
    pipeline_payload = _as_mapping(payload.get("pipeline"))
    nested_sink = _as_mapping(pipeline_payload.get("sink"))
    return _merge_sink_config(direct_sink, nested_sink)


def _storage_ref_from_output_path(raw_path: str) -> str:
    normalized = raw_path.strip().strip("/")
    if normalized.startswith("data/output/"):
        normalized = normalized.removeprefix("data/output/")
    return normalized


def _storage_ref_identity(ref: str) -> tuple[str | None, str | None, str | None]:
    parts = [part for part in ref.split("/") if part]
    if len(parts) < 3:
        return (parts[0] if parts else None, None, None)
    return parts[0], parts[1], "/".join(parts[2:])


def _infer_storage_format(ref: str) -> str | None:
    suffix = Path(ref).suffix.casefold()
    if suffix == ".json":
        return "json"
    if suffix == ".jsonl":
        return "jsonl"
    if suffix == ".txt":
        return "txt"
    return None


def _storage_schema_properties(
    payload: dict[str, object],
    *,
    layer_name: str,
) -> dict[str, JsonValue]:
    schema_payload = _as_mapping(payload.get("schema"))
    layer_schema = _as_mapping(schema_payload.get(layer_name))
    column_groups = _as_iterable(schema_payload.get("column_groups"))
    schema_column_groups = [
        name
        for item in column_groups
        if isinstance(item, dict)
        for name in [_optional_text(item.get("name"))]
        if name is not None
    ]
    return {
        "schema_present": bool(layer_schema),
        "schema_column_groups": schema_column_groups if schema_column_groups else None,
        "schema_include_groups": _normalized_text_list(
            layer_schema.get("include_groups")
        ),
        "schema_exclude_fields": _normalized_text_list(
            layer_schema.get("exclude_fields")
        ),
        "schema_alias_policy": _optional_text(layer_schema.get("alias_policy")),
    }


def _schema_group_field_map(payload: dict[str, object]) -> dict[str, list[str]]:
    schema_payload = _as_mapping(payload.get("schema"))
    column_groups = schema_payload.get("column_groups")
    group_map: dict[str, list[str]] = {}
    if not isinstance(column_groups, list):
        return group_map
    for item in column_groups:
        if not isinstance(item, dict):
            continue
        group_name = _optional_text(item.get("name"))
        if group_name is None:
            continue
        fields = _normalized_text_list(item.get("fields")) or []
        if fields:
            group_map[group_name] = fields
    return group_map


def _filtered_group_fields(
    payload: dict[str, object],
    *,
    layer_name: str,
) -> list[tuple[str, str]]:
    schema_payload = _as_mapping(payload.get("schema"))
    layer_schema = _as_mapping(schema_payload.get(layer_name))
    include_groups = _normalized_text_list(layer_schema.get("include_groups")) or []
    exclude_patterns = _normalized_text_list(layer_schema.get("exclude_fields")) or []
    group_map = _schema_group_field_map(payload)
    results: list[tuple[str, str]] = []
    for group_name in include_groups:
        for field_name in group_map.get(group_name, []):
            if any(
                fnmatch.fnmatch(field_name, pattern) for pattern in exclude_patterns
            ):
                continue
            results.append((group_name, field_name))
    return results
