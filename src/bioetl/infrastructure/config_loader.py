"""Configuration loading utilities.

Handles loading and merging of YAML configuration files
with convention-based path resolution (ADR-029) and unified
entity config support (ADR-039).
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.config_merge import config_merge
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig
from bioetl.infrastructure.source_normalizers.source import (
    normalize_source_config,
)


def _deep_merge(
    base: dict[str, Any],  # Any: YAML config has heterogeneous values
    override: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Deep merge two dictionaries, with override taking precedence."""
    return config_merge(base, override)


def _load_base_config(
    config_path: Path,
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Load pipeline base configuration from consolidated base path.

    Resolution order:
    1. configs/base/pipeline.yaml (new consolidated base path)
    """
    candidate_paths = (
        config_path.parent.parent.parent / "base" / "pipeline.yaml",
        config_path.parent.parent / "base" / "pipeline.yaml",
    )

    for base_path in candidate_paths:
        if not base_path.exists():
            continue
        with open(base_path, encoding="utf-8") as f:
            base_config = yaml.safe_load(f) or {}
            base_config.pop("schema_version", None)
            return base_config

    return {}


def _apply_file_reference_defaults(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
) -> None:
    """Apply convention-based defaults for file references.

    Sets source_file, dq_config_file, and filter_config_file if not specified.
    """
    config.setdefault("source_file", f"../../providers/{provider}.yaml")
    config.setdefault("dq_config_file", f"../../entities/{provider}/{entity_type}.yaml")
    config.setdefault(
        "filter_config_file",
        f"../../entities/{provider}/{entity_type}.yaml",
    )
    config.setdefault(
        "schema_file",
        f"../../schemas/{provider}/{entity_type}.yaml",
    )
    config.setdefault(
        "column_groups_file",
        f"../data_schema/{provider}/{entity_type}.yaml",
    )


def _load_column_groups_config(
    config_path: Path, column_groups_file: str
) -> list[dict[str, Any]] | None:  # Any: YAML config has heterogeneous values
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
    config_path: Path, schema_file: str
) -> dict[str, Any] | None:  # Any: YAML config has heterogeneous values
    """Load data schema configuration with layer-specific column definitions.

    Supports:
    1. Legacy format: column_groups only
    2. Layer-specific format: silver/gold with filtering

    Args:
        config_path: Path to pipeline config file.
        schema_file: Relative path to data schema YAML.

    Returns:
        Dictionary with column_groups, content_hash, silver, and gold keys, or None if empty.

    Raises:
        FileNotFoundError: If the resolved schema path does not exist.
    """
    schema_path = (config_path.parent / schema_file).resolve()
    if not schema_path.exists():
        raise FileNotFoundError(
            f"Data schema file not found: {schema_path} "
            f"(resolved from '{schema_file}' relative to {config_path.parent})"
        )

    with open(schema_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    # Build result with backward compatibility
    result: dict[str, Any] = {}  # Any: YAML config has heterogeneous values

    # Always include column_groups if present (for backward compatibility)
    if "column_groups" in data:
        result["column_groups"] = data["column_groups"]

    if "content_hash" in data:
        result["content_hash"] = data["content_hash"]

    # Add layer-specific configs if present
    if "silver" in data:
        result["silver"] = data["silver"]
    if "gold" in data:
        result["gold"] = data["gold"]

    return result if result else None


def _apply_layer_defaults(
    layer: dict[str, Any],  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
    layer_name: str,
    primary_keys: list[str],
) -> None:
    """Apply convention-based defaults for a single medallion layer.

    Sets path and csv_export.path if not specified.
    """
    layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")

    # Auto-set csv_export path to match layer path
    csv_export = layer.setdefault("csv_export", {})
    csv_export.setdefault("path", layer["path"])


def _apply_convention_defaults(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Apply convention-based defaults for paths, references, and table names.

    Auto-computes from provider/entity_type when not explicitly specified.
    """
    provider = config.get("provider")
    entity_type = config.get("entity_type")

    if not provider or not entity_type:
        return config

    primary_keys = config.get("primary_keys", [])
    _apply_file_reference_defaults(config, provider, entity_type)

    # Auto-compute table names from provider + entity_type
    table_name = f"{provider}_{entity_type}"
    config.setdefault("silver_table", table_name)
    config.setdefault("gold_table", table_name)

    sink = config.setdefault("sink", {})
    for layer_name in ("bronze", "silver", "gold"):
        layer = sink.setdefault(layer_name, {})
        _apply_layer_defaults(layer, provider, entity_type, layer_name, primary_keys)

    return config


def _read_source_config_payload(
    provider: str,
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Read provider YAML and map to source-loader input payload."""
    unified_path = Path(f"configs/providers/{provider}.yaml")
    if not unified_path.exists():
        raise ValueError(
            f"Source configuration file not found: {unified_path}. "
            "Create provider config with source/rate_limit/circuit_breaker settings."
        )

    with open(unified_path, encoding="utf-8") as f:
        unified_raw = yaml.safe_load(f) or {}

    source_section = unified_raw.get("source")
    if isinstance(source_section, dict):
        payload: dict[str, Any] = {  # Any: YAML config has heterogeneous values
            "source": source_section
        }  # Any: YAML config has heterogeneous values
        for key in ("entities", "entity_notes"):
            value = unified_raw.get(key)
            if value is not None:
                payload[key] = value
        return payload

    # Accept legacy-flat provider payload for compatibility with test fixtures.
    return unified_raw


def _validate_source_config_payload(
    payload: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> SourceYamlConfig:
    """Validate canonical source payload with pydantic schema."""
    return SourceYamlConfig.model_validate(payload)


def _map_source_config(validated_config: SourceYamlConfig) -> SourceYamlConfig:
    """Map validated source config to loader return type."""
    return validated_config


@lru_cache(maxsize=10)
def load_source_config(provider: str) -> SourceYamlConfig:
    """Load source configuration using read -> normalize -> validate -> map."""
    raw_payload = _read_source_config_payload(provider)
    normalized_payload = normalize_source_config(raw_payload)
    validated_payload = _validate_source_config_payload(normalized_payload)
    return _map_source_config(validated_payload)


_FILTER_SECTIONS: tuple[str, ...] = (
    "input_filter",
    "silver_filters",
    "gold_filters",
    "extraction_params",
)


def _apply_hierarchical_filter_config(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
    entity_config: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> None:
    """Apply filter config from the hierarchical filter system (ADR-028).

    Uses FilterConfigLoader to merge the 4-level hierarchy:
    1. defaults layer from configs/base/pipeline.yaml.filter_defaults
    2. providers/{provider}.yaml — provider-specific
    3. entities/{provider}/{entity}.yaml — entity-specific
    4. Inline overrides from pipeline config — highest priority

    Replaces the legacy _load_filter_config + _merge_filter_config functions
    that only loaded the entity file without the full hierarchy.

    Args:
        config: Pipeline config dict (modified in place).
        entity_config: Original entity config dict (before base merge).
            Used to extract inline filter overrides.
    """
    from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader

    provider = config.get("provider", "")
    entity_type = config.get("entity_type", "")

    if not provider or not entity_type:
        return

    # Collect inline filter overrides from pipeline YAML
    inline_overrides: dict[str, Any] = {}  # Any: YAML config has heterogeneous values
    for section in _FILTER_SECTIONS:
        if section in entity_config:
            inline_overrides[section] = entity_config[section]

    # Also handle filter_rules key (ADR-028 inline override field)
    filter_rules = entity_config.get("filter_rules")
    if isinstance(filter_rules, dict):
        inline_overrides = _deep_merge(inline_overrides, filter_rules)

    # Use FilterConfigLoader for hierarchical merge
    loader = FilterConfigLoader(Path("configs"))
    merged_filters = loader.load_as_dict(
        provider, entity_type, inline_overrides or None
    )

    # Apply merged filter sections to pipeline config
    for section in _FILTER_SECTIONS:
        if section in merged_filters:
            config[section] = merged_filters[section]


def _merge_data_schema_into_config(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
    data_schema: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> None:
    """Merge loaded data schema (column_groups, silver, gold) into pipeline config."""
    if "column_groups" in data_schema:
        config["column_groups"] = data_schema["column_groups"]
    if "content_hash" in data_schema:
        config["content_hash"] = data_schema["content_hash"]
    if "silver" in data_schema:
        config.setdefault("data_schema", {})["silver"] = data_schema["silver"]
    if "gold" in data_schema:
        config.setdefault("data_schema", {})["gold"] = data_schema["gold"]


def _validate_schema_config(
    data_schema: dict[str, Any],  # Any: YAML config has heterogeneous values
    schema_file: str,
) -> None:
    """Validate schema configuration has required minimum structure.

    Required:
      - non-empty column_groups
      - system/identifiers/business groups
      - layer filters for silver and gold (non-empty include_groups)
    """
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


def _load_unified_entity_raw(
    path: Path,
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Load unified entity YAML file, returning empty dict when absent."""
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw if isinstance(raw, dict) else {}


def _get_unified_section(
    unified_raw: dict[str, Any],  # Any: YAML config has heterogeneous values
    section: str,
) -> dict[str, Any] | None:  # Any: YAML config has heterogeneous values
    """Get a dict section from unified entity config if present."""
    value = unified_raw.get(section)
    return value if isinstance(value, dict) else None


def _load_column_groups_section(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
    entity_config: dict[str, Any],  # Any: YAML config has heterogeneous values
    config_path: Path,
    unified_schema: dict[str, Any]  # Any: YAML config has heterogeneous values
    | None = None,  # Any: YAML config has heterogeneous values
) -> None:
    """Load column groups from external file unless explicitly set inline.

    Priority: explicit inline > unified schema section > schema_file >
    data_schema_file > column_groups_file (legacy).
    """
    if "column_groups" in entity_config:
        return

    if unified_schema:
        _validate_schema_config(unified_schema, "entities/*/*:schema")
        _merge_data_schema_into_config(config, unified_schema)
        return

    schema_file = config.get("schema_file")
    if isinstance(schema_file, str) and schema_file.strip():
        data_schema = _load_data_schema_config(config_path, schema_file)
        if data_schema:
            _validate_schema_config(data_schema, schema_file)
            _merge_data_schema_into_config(config, data_schema)
            return

    # Backward compatibility for deprecated data_schema_file field
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

    if column_groups_file := config.get("column_groups_file"):
        column_groups = _load_column_groups_config(config_path, column_groups_file)
        if column_groups is not None:
            config["column_groups"] = column_groups


def _load_source_section(
    config: dict[str, Any],  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Load source config from external file and merge with entity overrides.

    The source file (configs/providers/{provider}.yaml) provides base settings.
    Entity-specific source settings from the pipeline YAML override them.
    """
    source_file = config.get("source_file")
    if not source_file:
        return
    source_path = config_path.parent / source_file
    if source_path.exists():
        with open(source_path, encoding="utf-8") as f:
            source_config = yaml.safe_load(f) or {}
        base_source = source_config.get("source", source_config)
        entity_source = config.get("source", {})
        config["source"] = _deep_merge(base_source, entity_source)


@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration from YAML file and return typed model.

    Loading order: base → unified entity (ADR-039) →
    convention defaults (ADR-029) → hierarchical filters (ADR-028) →
    column groups → source section.

    Args:
        pipeline_name: Pipeline name (e.g., "chembl_activity").

    Raises:
        ValueError: If pipeline config file doesn't exist.

    Returns:
        Loaded PipelineYamlConfig.
    """
    unified_raw: dict[str, Any] = {}  # Any: YAML config has heterogeneous values
    unified_schema: (
        dict[
            str, Any  # Any: YAML config has heterogeneous values
        ]
        | None
    ) = None

    if "_" not in pipeline_name:
        raise ValueError(
            f"Pipeline name must be in '<provider>_<entity>' format: {pipeline_name}"
        )

    provider, entity = pipeline_name.split("_", 1)
    config_path = Path(f"configs/entities/{provider}/{entity}.yaml")
    unified_raw = _load_unified_entity_raw(config_path)
    unified_pipeline = _get_unified_section(unified_raw, "pipeline")
    unified_schema = _get_unified_section(unified_raw, "schema")

    if not unified_pipeline:
        raise ValueError(
            f"Configuration file not found: {config_path} "
            "(or missing 'pipeline' section)"
        )

    entity_config = unified_pipeline

    defaults = _load_base_config(config_path)

    config = _deep_merge(defaults, entity_config)
    config = _apply_convention_defaults(config)

    # Apply hierarchical filter config (ADR-028)
    _apply_hierarchical_filter_config(config, entity_config)

    _load_column_groups_section(config, entity_config, config_path, unified_schema)
    _load_source_section(config, config_path)

    # Strip intermediate keys consumed above but absent from PipelineYamlConfig.
    for _key in ("source_file", "data_schema", "filter_defaults", "contract_defaults"):
        config.pop(_key, None)

    validated: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated
