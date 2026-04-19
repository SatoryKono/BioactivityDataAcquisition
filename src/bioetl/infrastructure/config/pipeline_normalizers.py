"""Pipeline-configuration normalization utilities."""

from __future__ import annotations

from bioetl.domain.types import JsonDict


def _project_schema_fields_into_config(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
) -> None:
    """Project runtime-relevant schema fields into pipeline config."""
    if "column_groups" in data_schema:
        config["column_groups"] = data_schema["column_groups"]
    if "content_hash" in data_schema:
        config["content_hash"] = data_schema["content_hash"]


def _validate_column_groups(
    groups: object,
    schema_source: str,
) -> set[str | None]:
    """Validate column_groups is a non-empty list and return group names.

    Returns:
        Set of group name values extracted from valid column group dicts.
    """
    if not isinstance(groups, list) or not groups:
        raise ValueError(
            f"schema '{schema_source}' must define non-empty column_groups"
        )
    return {g.get("name") for g in groups if isinstance(g, dict)}


def _has_business_group(group_names: set[str | None]) -> bool:
    """Check if group names contain a business group.

    Returns:
        True if 'business' is present or any non-system, non-dq group name exists.
    """
    if "business" in group_names:
        return True
    return any(
        isinstance(name, str) and name != "system" and not name.startswith("dq")
        for name in group_names
    )


def _validate_layer_include_groups(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    layer: str,
    schema_source: str,
) -> None:
    """Validate a single layer has proper include_groups config."""
    layer_cfg = data_schema.get(layer)
    if not isinstance(layer_cfg, dict):
        raise ValueError(
            f"schema '{schema_source}' missing '{layer}' layer filter config"
        )
    include_groups = layer_cfg.get("include_groups")
    if not isinstance(include_groups, list) or not include_groups:
        raise ValueError(
            f"schema '{schema_source}' must define non-empty {layer}.include_groups"
        )


def _validate_schema_config(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    schema_source: str,
) -> None:
    """Validate schema configuration has required minimum structure."""
    group_names = _validate_column_groups(
        data_schema.get("column_groups") or [], schema_source
    )

    if not ("system" in group_names and _has_business_group(group_names)):
        raise ValueError(
            f"schema '{schema_source}' must contain system and business groups"
        )

    for layer in ("silver", "gold"):
        _validate_layer_include_groups(data_schema, layer, schema_source)


def apply_pipeline_schema_normalization(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    *,
    entity_config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: object,
    unified_schema: JsonDict | None = None,  # Any: YAML values are heterogeneous
) -> None:
    """Validate and project canonical `unified_schema` into pipeline config."""
    _ = entity_config, config_path

    if unified_schema:
        _validate_schema_config(unified_schema, "entities/*/*:schema")
        _project_schema_fields_into_config(config, unified_schema)


__all__ = ["apply_pipeline_schema_normalization"]
