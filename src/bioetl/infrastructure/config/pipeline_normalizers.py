"""Pipeline-configuration normalization utilities.

Encapsulates schema-reference migration concerns so pipeline loaders can keep
read -> normalize -> validate -> map orchestration explicit.
"""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file


def _load_data_schema_config(
    config_path: Path, schema_file: str
) -> JsonDict | None:  # Any: YAML config has heterogeneous values
    """Load data schema configuration with layer-specific column definitions.

    Returns:
        Dictionary with column_groups, silver, and gold schema sections if present, None if empty.
    """
    schema_path = (config_path.parent / schema_file).resolve()
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Data schema file not found: {schema_path} "
            f"(resolved from '{schema_file}' relative to {config_path.parent})"
        )

    data = _load_yaml_file(schema_path)

    result: JsonDict = {}  # Any: YAML config has heterogeneous values
    if "column_groups" in data:
        result["column_groups"] = data["column_groups"]
    if "content_hash" in data:
        result["content_hash"] = data["content_hash"]
    if "silver" in data:
        result["silver"] = data["silver"]
    if "gold" in data:
        result["gold"] = data["gold"]

    return result if result else None


def _merge_data_schema_into_config(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
) -> None:
    """Merge loaded data schema (column_groups, silver, gold) into config."""
    if "column_groups" in data_schema:
        config["column_groups"] = data_schema["column_groups"]
    if "content_hash" in data_schema:
        config["content_hash"] = data_schema["content_hash"]
    if "silver" in data_schema:
        config.setdefault("data_schema", {})["silver"] = data_schema["silver"]
    if "gold" in data_schema:
        config.setdefault("data_schema", {})["gold"] = data_schema["gold"]


def _validate_column_groups(
    groups: object,
    schema_file: str,
) -> set[str | None]:
    """Validate column_groups is a non-empty list and return group names.

    Returns:
        Set of group name values extracted from valid column group dicts.
    """
    if not isinstance(groups, list) or not groups:
        raise ValueError(
            f"schema_file '{schema_file}' must define non-empty column_groups"
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
    schema_file: str,
) -> None:
    """Validate a single layer has proper include_groups config."""
    layer_cfg = data_schema.get(layer)
    if not isinstance(layer_cfg, dict):
        raise ValueError(
            f"schema_file '{schema_file}' missing '{layer}' layer filter config"
        )
    include_groups = layer_cfg.get("include_groups")
    if not isinstance(include_groups, list) or not include_groups:
        raise ValueError(
            f"schema_file '{schema_file}' must define non-empty {layer}.include_groups"
        )


def _validate_schema_config(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    schema_file: str,
) -> None:
    """Validate schema configuration has required minimum structure."""
    group_names = _validate_column_groups(
        data_schema.get("column_groups") or [], schema_file
    )

    if not ("system" in group_names and _has_business_group(group_names)):
        raise ValueError(
            f"schema_file '{schema_file}' must contain system and business groups"
        )

    for layer in ("silver", "gold"):
        _validate_layer_include_groups(data_schema, layer, schema_file)


def apply_pipeline_schema_normalization(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    *,
    entity_config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
    unified_schema: JsonDict | None = None,  # Any: YAML values are heterogeneous
) -> None:
    """Normalize pipeline schema from canonical `unified_schema`."""
    _ = entity_config

    if unified_schema:
        _validate_schema_config(unified_schema, "entities/*/*:schema")
        _merge_data_schema_into_config(config, unified_schema)
        return


__all__ = ["apply_pipeline_schema_normalization"]
