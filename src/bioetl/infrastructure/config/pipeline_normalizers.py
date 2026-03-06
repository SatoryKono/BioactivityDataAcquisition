"""Pipeline-configuration normalization utilities.

Encapsulates schema-reference migration concerns so pipeline loaders can keep
read -> normalize -> validate -> map orchestration explicit.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict


def _load_column_groups_config(
    config_path: Path, column_groups_file: str
) -> list[JsonDict] | None:  # Any: YAML config has heterogeneous values
    """Load column group configuration from column_groups_file.

    Returns:
        List of column group dicts if found, None if file is missing or has no valid groups.
    """
    column_groups_path = config_path.parent / column_groups_file
    if not column_groups_path.exists():
        return None

    with open(column_groups_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        groups = data.get("column_groups")
        if isinstance(groups, list):
            return groups

    return None


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

    with open(schema_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

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


def _validate_schema_config(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    schema_file: str,
) -> None:
    """Validate schema configuration has required minimum structure."""
    groups = data_schema.get("column_groups") or []
    if not isinstance(groups, list) or not groups:
        raise ValueError(
            f"schema_file '{schema_file}' must define non-empty column_groups"
        )

    group_names = {g.get("name") for g in groups if isinstance(g, dict)}
    has_system = "system" in group_names
    has_business = "business" in group_names or any(
        isinstance(name, str) and name != "system" and not name.startswith("dq")
        for name in group_names
    )
    if not (has_system and has_business):
        raise ValueError(
            f"schema_file '{schema_file}' must contain system and business groups"
        )

    for layer in ("silver", "gold"):
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


def apply_pipeline_schema_normalization(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    *,
    entity_config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
    unified_schema: JsonDict | None = None,  # Any: YAML values are heterogeneous
) -> None:
    """Normalize schema references across new and legacy pipeline formats."""
    if "column_groups" in entity_config:
        return

    if unified_schema:
        _validate_schema_config(unified_schema, "entities/*/*:schema")
        _merge_data_schema_into_config(config, unified_schema)
        return

    deprecated_data_schema_file = config.get("data_schema_file")
    if (
        isinstance(deprecated_data_schema_file, str)
        and deprecated_data_schema_file.strip()
    ):
        data_schema = _load_data_schema_config(config_path, deprecated_data_schema_file)
        if data_schema:
            _validate_schema_config(data_schema, deprecated_data_schema_file)
            _merge_data_schema_into_config(config, data_schema)
            return

    schema_file = config.get("schema_file")
    if isinstance(schema_file, str) and schema_file.strip():
        data_schema = _load_data_schema_config(config_path, schema_file)
        if data_schema:
            _validate_schema_config(data_schema, schema_file)
            _merge_data_schema_into_config(config, data_schema)
            return

    column_groups_file = config.get("column_groups_file")
    if isinstance(column_groups_file, str) and column_groups_file.strip():
        column_groups = _load_column_groups_config(config_path, column_groups_file)
        if column_groups is not None:
            config["column_groups"] = column_groups


__all__ = ["apply_pipeline_schema_normalization"]
