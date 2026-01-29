"""Configuration loading utilities.

Handles loading and merging of YAML configuration files.

Convention-based path resolution (ADR-029):
    When a pipeline config does not explicitly specify certain paths/references,
    they are auto-computed from provider and entity_type:

    File References:
        - source_file: ../../sources/{provider}.yaml
        - dq_config_file: ../../dq/entities/{provider}/{entity_type}.yaml
        - filter_config_file: ../../filter/entities/{provider}/{entity_type}.yaml

    Sink Paths:
        - sink.bronze.path: data/output/bronze/{provider}/{entity_type}
        - sink.silver.path: data/output/silver/{provider}/{entity_type}
        - sink.gold.path: data/output/gold/{provider}/{entity_type}
        - sink.silver.csv_export.path: {sink.silver.path}
        - sink.gold.csv_export.path: {sink.gold.path}

    Primary Key Propagation:
        - sink.silver.primary_key: {primary_keys}
        - sink.silver.sort_by.columns: {primary_keys}
        - sink.gold.sort_by.columns: {primary_keys}

    This reduces duplication between pipeline configs and filter/dq entity configs.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries, with override taking precedence."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def _load_base_config(config_path: Path) -> dict[str, Any]:
    """Load pipeline base configuration from _base.yaml."""
    base_path = config_path.parent.parent / "_base.yaml"

    if not base_path.exists():
        base_path = config_path.parent / "_base.yaml"

    if base_path.exists():
        with open(base_path, encoding="utf-8") as f:
            base_config = yaml.safe_load(f) or {}
            base_config.pop("schema_version", None)
            return base_config

    return {}


def _apply_file_reference_defaults(
    config: dict[str, Any], provider: str, entity_type: str
) -> None:
    """Apply convention-based defaults for file references.

    Sets source_file, dq_config_file, and filter_config_file if not specified.
    """
    config.setdefault("source_file", f"../../sources/{provider}.yaml")
    config.setdefault(
        "dq_config_file", f"../../dq/entities/{provider}/{entity_type}.yaml"
    )
    config.setdefault(
        "filter_config_file", f"../../filter/entities/{provider}/{entity_type}.yaml"
    )
    config.setdefault(
        "column_groups_file",
        f"../data_schema/{provider}/{entity_type}.yaml",
    )


def _load_column_groups_config(
    config_path: Path, column_groups_file: str
) -> list[dict[str, Any]] | None:
    """Load column group configuration from column_groups_file."""
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
    config_path: Path, data_schema_file: str
) -> dict[str, Any] | None:
    """Load data schema configuration with layer-specific column definitions.

    Supports:
    1. Legacy format: column_groups only
    2. Layer-specific format: silver/gold with filtering

    Args:
        config_path: Path to pipeline config file.
        data_schema_file: Relative path to data schema YAML.

    Returns:
        Dictionary with column_groups, silver, and gold keys, or None if file not found.
    """
    schema_path = config_path.parent / data_schema_file
    if not schema_path.exists():
        return None

    with open(schema_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Build result with backward compatibility
    result: dict[str, Any] = {}

    # Always include column_groups if present (for backward compatibility)
    if "column_groups" in data:
        result["column_groups"] = data["column_groups"]

    # Add layer-specific configs if present
    if "silver" in data:
        result["silver"] = data["silver"]
    if "gold" in data:
        result["gold"] = data["gold"]

    return result if result else None


def _apply_layer_defaults(
    layer: dict[str, Any],
    provider: str,
    entity_type: str,
    layer_name: str,
    primary_keys: list[str],
) -> None:
    """Apply convention-based defaults for a single medallion layer.

    Sets path, sort_by.columns, csv_export.path if not specified.
    For silver layer, also sets primary_key.
    """
    layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")

    if primary_keys:
        # Silver layer gets primary_key propagation
        if layer_name == "silver":
            layer.setdefault("primary_key", list(primary_keys))

        # Both silver and gold get sort_by.columns propagation
        sort_by = layer.setdefault("sort_by", {})
        sort_by.setdefault("columns", list(primary_keys))

    # Auto-set csv_export path to match layer path
    csv_export = layer.setdefault("csv_export", {})
    csv_export.setdefault("path", layer["path"])


def _apply_convention_defaults(config: dict[str, Any]) -> dict[str, Any]:
    """Apply convention-based defaults for paths and references.

    Auto-computes file references and sink paths from provider/entity_type
    when not explicitly specified. This reduces config duplication.

    Args:
        config: Merged configuration dictionary.

    Returns:
        Configuration with convention-based defaults applied.
    """
    provider = config.get("provider")
    entity_type = config.get("entity_type")

    if not provider or not entity_type:
        return config

    primary_keys = config.get("primary_keys", [])

    # Auto-compute file references
    _apply_file_reference_defaults(config, provider, entity_type)

    # Auto-compute sink paths for each medallion layer
    sink = config.setdefault("sink", {})

    for layer_name in ("bronze", "silver", "gold"):
        layer = sink.setdefault(layer_name, {})
        _apply_layer_defaults(layer, provider, entity_type, layer_name, primary_keys)

    return config


@lru_cache(maxsize=10)
def load_source_config(provider: str) -> SourceYamlConfig:
    """Load source configuration from YAML file."""
    config_path = Path(f"configs/sources/{provider}.yaml")

    if not config_path.exists():
        raise ValueError(
            f"Source configuration file not found: {config_path}. "
            f"Create configs/sources/{provider}.yaml with rate_limit and circuit_breaker settings."
        )

    with open(config_path, encoding="utf-8") as f:
        raw_config = yaml.safe_load(f) or {}

    config: SourceYamlConfig = SourceYamlConfig.model_validate(raw_config)
    return config


def _load_filter_config(
    config_path: Path, filter_config_file: str
) -> dict[str, Any] | None:
    """Load filter configuration from filter_config_file.

    Args:
        config_path: Path to the pipeline config file (for relative resolution).
        filter_config_file: Relative path to filter config file.

    Returns:
        Loaded filter config dict or None if file doesn't exist.
    """
    filter_path = config_path.parent / filter_config_file
    if not filter_path.exists():
        return None

    with open(filter_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_filter_config(
    config: dict[str, Any],
    filter_config: dict[str, Any],
    explicit_entity_config: dict[str, Any],
) -> None:
    """Merge filter config (input_filter, gold_filters) into pipeline config.

    Merge priority (highest to lowest):
    1. Explicit entity config (from pipeline YAML file)
    2. Filter config (from filter entity file)
    3. Base defaults (from _base.yaml)

    This allows minimal pipeline configs that inherit from filter configs
    while still allowing explicit overrides when needed.

    Args:
        config: Pipeline config dict (modified in place). Contains merged
            defaults + entity config.
        filter_config: Filter config dict from filter entity file.
        explicit_entity_config: Original entity config dict (before merging
            with defaults). Used to determine what was explicitly set.
    """
    # Merge input_filter
    if "input_filter" in filter_config:
        # Start with filter config as base
        merged_input_filter = filter_config["input_filter"].copy()

        # Only override with explicit pipeline values (not defaults from _base.yaml)
        if "input_filter" in explicit_entity_config:
            merged_input_filter = _deep_merge(
                merged_input_filter, explicit_entity_config["input_filter"]
            )

        config["input_filter"] = merged_input_filter

    # Merge gold_filters
    if "gold_filters" in filter_config:
        # Start with filter config as base
        merged_gold_filters = filter_config["gold_filters"].copy()

        # Only override with explicit pipeline values (not defaults from _base.yaml)
        if "gold_filters" in explicit_entity_config:
            merged_gold_filters = _deep_merge(
                merged_gold_filters, explicit_entity_config["gold_filters"]
            )

        config["gold_filters"] = merged_gold_filters


def _load_and_merge_filter_config(
    config: dict[str, Any], config_path: Path, entity_config: dict[str, Any]
) -> None:
    """Load and merge filter configuration."""
    if filter_config_file := config.get("filter_config_file"):
        filter_config = _load_filter_config(config_path, filter_config_file)
        if filter_config:
            _merge_filter_config(config, filter_config, entity_config)


def _load_and_merge_data_schema(
    config: dict[str, Any], config_path: Path, entity_config: dict[str, Any]
) -> None:
    """Load and merge data schema configuration."""
    if "column_groups" in entity_config:
        return

    # Try new data_schema_file first
    if data_schema_file := config.get("data_schema_file"):
        data_schema = _load_data_schema_config(config_path, data_schema_file)
        if data_schema:
            if "column_groups" in data_schema:
                config["column_groups"] = data_schema["column_groups"]
            if "silver" in data_schema:
                config.setdefault("data_schema", {})["silver"] = data_schema["silver"]
            if "gold" in data_schema:
                config.setdefault("data_schema", {})["gold"] = data_schema["gold"]
            return

    # Fallback to legacy column_groups_file
    if column_groups_file := config.get("column_groups_file"):
        column_groups = _load_column_groups_config(config_path, column_groups_file)
        if column_groups is not None:
            config["column_groups"] = column_groups


def _load_and_merge_source_config(config: dict[str, Any], config_path: Path) -> None:
    """Load and merge source configuration."""
    if source_file := config.get("source_file"):
        source_path = config_path.parent / source_file
        if source_path.exists():
            with open(source_path, encoding="utf-8") as f:
                source_config = yaml.safe_load(f) or {}
            config["source"] = source_config.get("source", source_config)


@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration from YAML file and return typed model.

    The loading process follows this order:
    1. Load base config from _base.yaml
    2. Merge with entity-specific config
    3. Apply convention-based defaults (auto-compute paths/references)
    4. Load and merge filter config from filter_config_file
    5. Load source config from source_file

    Convention-based defaults auto-compute:
    - File references (source_file, dq_config_file, filter_config_file)
    - Sink paths (bronze/silver/gold paths)
    - Primary key propagation to sink.silver.primary_key and sort_by

    Filter config merging:
    - input_filter and gold_filters from filter_config_file are merged
    - Pipeline inline config acts as overrides on top of filter config
    - This allows minimal pipeline configs with full filter inheritance

    Args:
        pipeline_name: Pipeline name (e.g., "chembl_activity").

    Returns:
        Validated PipelineYamlConfig Pydantic model.

    Raises:
        ValueError: If pipeline config file doesn't exist.
    """
    try:
        provider, entity = pipeline_name.split("_", 1)
        config_path = Path(f"configs/pipelines/{provider}/{entity}.yaml")
    except ValueError:
        config_path = Path(f"configs/pipelines/{pipeline_name}.yaml")

    if not config_path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")

    defaults = _load_base_config(config_path)

    with open(config_path, encoding="utf-8") as f:
        entity_config = yaml.safe_load(f) or {}

    config = _deep_merge(defaults, entity_config)

    # Apply convention-based defaults (auto-compute paths/references)
    config = _apply_convention_defaults(config)

    # Load and merge additional configurations
    _load_and_merge_filter_config(config, config_path, entity_config)
    _load_and_merge_data_schema(config, config_path, entity_config)
    _load_and_merge_source_config(config, config_path)

    validated: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated
