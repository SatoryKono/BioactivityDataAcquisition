"""Configuration loading utilities.

Handles loading and merging of YAML configuration files.

Convention-based path resolution (ADR-029):
    When a pipeline config does not explicitly specify certain paths/references,
    they are auto-computed from provider and entity_type:

    File References:
        - source_file: ../../sources/{provider}.yaml
        - dq_config_file: ../../quality/entities/{provider}/{entity_type}.yaml
        - filter_config_file: ../../filters/entities/{provider}/{entity_type}.yaml

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

_PATH_ALIAS_GROUPS: tuple[tuple[str, str], ...] = (
    ("filters", "filter"),
    ("quality", "dq"),
    ("schemas", "data_schema"),
)


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
        "dq_config_file", f"../../quality/entities/{provider}/{entity_type}.yaml"
    )
    config.setdefault(
        "filter_config_file",
        f"../../filters/entities/{provider}/{entity_type}.yaml",
    )
    config.setdefault(
        "data_schema_file",
        f"../schemas/{provider}/{entity_type}.yaml",
    )
    config.setdefault(
        "column_groups_file",
        f"../data_schema/{provider}/{entity_type}.yaml",
    )


def _resolve_with_path_aliases(base_dir: Path, relative_path: str) -> Path | None:
    """Resolve file path using new-first aliases with legacy fallback."""
    direct_path = base_dir / relative_path
    if direct_path.exists():
        return direct_path

    parts = Path(relative_path).parts
    for new_dir, legacy_dir in _PATH_ALIAS_GROUPS:
        for source, target in ((new_dir, legacy_dir), (legacy_dir, new_dir)):
            if source not in parts:
                continue
            rewritten = Path(*[target if part == source else part for part in parts])
            candidate = base_dir / rewritten
            if candidate.exists():
                return candidate

    return None


def _normalize_timeout_keys(config: dict[str, Any]) -> dict[str, Any]:
    """Normalize timeout and timeout_sec aliases bidirectionally."""
    result = config.copy()
    if "timeout" in result and "timeout_sec" not in result:
        result["timeout_sec"] = result["timeout"]
    if "timeout_sec" in result and "timeout" not in result:
        result["timeout"] = result["timeout_sec"]
    return result


def _normalize_rate_limit_aliases(source_norm: dict[str, Any]) -> None:
    """Normalize rate_limit.with_api_key ↔ rate_limit.authenticated aliases."""
    rate_limit = source_norm.get("rate_limit")
    if not isinstance(rate_limit, dict):
        return

    rate_limit_norm = rate_limit.copy()
    with_api_key = rate_limit_norm.get("with_api_key")
    authenticated = rate_limit_norm.get("authenticated")

    if isinstance(with_api_key, dict) and "authenticated" not in rate_limit_norm:
        rate_limit_norm["authenticated"] = with_api_key
    if isinstance(authenticated, dict) and "with_api_key" not in rate_limit_norm:
        rate_limit_norm["with_api_key"] = authenticated

    source_norm["rate_limit"] = rate_limit_norm


def _normalize_health_check_aliases(source_norm: dict[str, Any]) -> None:
    """Normalize health_check timeout aliases."""
    health_check = source_norm.get("health_check")
    if isinstance(health_check, dict):
        source_norm["health_check"] = _normalize_timeout_keys(health_check)


def _project_provider_config_to_new_shape(
    source_norm: dict[str, Any],
) -> dict[str, Any]:
    """Project legacy provider_config fields to canonical new-style sections."""
    provider_config = source_norm.get("provider_config")
    if not isinstance(provider_config, dict):
        return {}

    _project_api_from_provider_config(source_norm, provider_config)
    _project_client_from_provider_config(source_norm, provider_config)
    _project_batch_from_provider_config(source_norm, provider_config)

    return provider_config


def _project_api_from_provider_config(
    source_norm: dict[str, Any],
    provider_config: dict[str, Any],
) -> None:
    """Project provider_config API fields into source.api."""

    api_norm = source_norm.get("api")
    if not isinstance(api_norm, dict):
        api_norm = {}
    for key in ("base_url", "auth_type", "api_key", "api_version"):
        if key in provider_config:
            api_norm.setdefault(key, provider_config[key])
    if api_norm:
        source_norm["api"] = api_norm


def _project_client_from_provider_config(
    source_norm: dict[str, Any],
    provider_config: dict[str, Any],
) -> None:
    """Project provider_config client fields into source.client."""
    client = provider_config.get("client")
    if not isinstance(client, dict):
        return

    client_norm = source_norm.get("client")
    if not isinstance(client_norm, dict):
        client_norm = {}

    source_norm["client"] = _deep_merge(_normalize_timeout_keys(client), client_norm)


def _project_batch_from_provider_config(
    source_norm: dict[str, Any],
    provider_config: dict[str, Any],
) -> None:
    """Project provider_config batch fields into source.batch."""
    batch_norm = source_norm.get("batch")
    if not isinstance(batch_norm, dict):
        batch_norm = {}

    _set_default_if_present(batch_norm, "batch_size", provider_config)
    if "batch_size" in provider_config:
        batch_norm.setdefault("size", provider_config["batch_size"])
    _set_default_if_present(batch_norm, "page_size", provider_config)
    _set_default_if_present(batch_norm, "max_url_length", provider_config)

    if batch_norm:
        source_norm["batch"] = batch_norm


def _set_default_if_present(
    target: dict[str, Any],
    key: str,
    source: dict[str, Any],
) -> None:
    """Set target[key] from source when key exists and target lacks it."""
    if key in source:
        target.setdefault(key, source[key])


def _apply_api_to_provider_config(
    provider_config: dict[str, Any],
    api: dict[str, Any],
) -> None:
    """Map API section into provider_config."""
    for key in ("base_url", "auth_type", "api_key", "api_version"):
        if key in api:
            provider_config.setdefault(key, api[key])


def _apply_client_to_provider_config(
    provider_config: dict[str, Any],
    client: dict[str, Any],
) -> None:
    """Map client section into provider_config with timeout normalization."""
    existing_client = provider_config.get("client")
    if not isinstance(existing_client, dict):
        existing_client = {}

    provider_config["client"] = _deep_merge(
        _normalize_timeout_keys(existing_client),
        _normalize_timeout_keys(client),
    )


def _apply_batch_to_provider_config(
    provider_config: dict[str, Any],
    batch: dict[str, Any] | int,
) -> None:
    """Map batch section into provider_config."""
    if isinstance(batch, int):
        provider_config.setdefault("batch_size", batch)
        return

    if not isinstance(batch, dict):
        return

    if "batch_size" in batch:
        provider_config.setdefault("batch_size", batch["batch_size"])
    elif "size" in batch:
        provider_config.setdefault("batch_size", batch["size"])

    if "page_size" in batch:
        provider_config.setdefault("page_size", batch["page_size"])
    if "max_url_length" in batch:
        provider_config.setdefault("max_url_length", batch["max_url_length"])


def _load_column_groups_config(
    config_path: Path, column_groups_file: str
) -> list[dict[str, Any]] | None:
    """Load column group configuration from column_groups_file."""
    column_groups_path = _resolve_with_path_aliases(
        config_path.parent, column_groups_file
    )
    if column_groups_path is None:
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
    schema_path = _resolve_with_path_aliases(config_path.parent, data_schema_file)
    if schema_path is None:
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


def _normalize_source_config(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize source config across legacy/new schemas before validation.

    Supported input schemas:
    - Legacy: ``source.provider_config.*`` and ``rate_limit.with_api_key``
    - New: ``source.api`` + ``source.client`` + ``source.batch``
      and ``rate_limit.authenticated``

    The current ``SourceYamlConfig`` validates provider-config shape, so this
    function performs dual-format reconciliation and emits provider-config
    compatible output while preserving backward compatibility.
    """
    config = raw.copy()

    # Support flat root-level source format:
    # api/client/batch and related source-section keys can live at root.
    if "source" not in config and any(
        key in config for key in ("api", "client", "batch")
    ):
        source_section_keys = {
            "type",
            "load_strategy",
            "batch_size",
            "provider_config",
            "api",
            "client",
            "batch",
            "rate_limit",
            "circuit_breaker",
            "health_check",
            "retry",
            "entities",
        }
        config["source"] = {
            key: value for key, value in config.items() if key in source_section_keys
        }

    source = config.get("source")
    if not isinstance(source, dict):
        return config

    source_norm = source.copy()

    _normalize_rate_limit_aliases(source_norm)
    _normalize_health_check_aliases(source_norm)

    provider_config = _project_provider_config_to_new_shape(source_norm)

    # Consume new-style keys into legacy provider_config for current validation schema.
    api = source_norm.pop("api", None)
    if isinstance(api, dict):
        _apply_api_to_provider_config(provider_config, api)

    client = source_norm.pop("client", None)
    if isinstance(client, dict):
        _apply_client_to_provider_config(provider_config, client)

    batch = source_norm.pop("batch", None)
    if batch is not None:
        _apply_batch_to_provider_config(provider_config, batch)

    if provider_config:
        source_norm["provider_config"] = provider_config

    config["source"] = source_norm
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

    normalized_config = _normalize_source_config(raw_config)

    config: SourceYamlConfig = SourceYamlConfig.model_validate(normalized_config)
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
    filter_path = _resolve_with_path_aliases(config_path.parent, filter_config_file)
    if filter_path is None:
        return None

    with open(filter_path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _merge_filter_config(
    config: dict[str, Any],
    filter_config: dict[str, Any],
    explicit_entity_config: dict[str, Any],
) -> None:
    """Merge filter config (input_filter, gold_filters, extraction_params) into pipeline config.

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

    # Merge extraction_params (ADR-028 §3)
    if "extraction_params" in filter_config:
        merged_extraction_params = dict(filter_config["extraction_params"])

        # Pipeline-level overrides take precedence
        if "extraction_params" in explicit_entity_config:
            merged_extraction_params.update(explicit_entity_config["extraction_params"])

        config["extraction_params"] = merged_extraction_params


def _load_column_groups_section(
    config: dict[str, Any],
    entity_config: dict[str, Any],
    config_path: Path,
) -> None:
    """Load column groups from external file unless explicitly set inline.

    Priority: explicit inline > data_schema_file > column_groups_file (legacy).
    """
    if "column_groups" in entity_config:
        return

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

    if column_groups_file := config.get("column_groups_file"):
        column_groups = _load_column_groups_config(config_path, column_groups_file)
        if column_groups is not None:
            config["column_groups"] = column_groups


def _load_source_section(config: dict[str, Any], config_path: Path) -> None:
    """Load source config from external file if specified."""
    source_file = config.get("source_file")
    if not source_file:
        return
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
    config = _apply_convention_defaults(config)

    # Load and merge filter config from filter_config_file
    if filter_config_file := config.get("filter_config_file"):
        filter_config = _load_filter_config(config_path, filter_config_file)
        if filter_config:
            _merge_filter_config(config, filter_config, entity_config)

    _load_column_groups_section(config, entity_config, config_path)
    _load_source_section(config, config_path)

    validated: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated
