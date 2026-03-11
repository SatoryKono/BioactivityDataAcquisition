"""Configuration loading utilities.

Handles loading and merging of YAML configuration files
with convention-based path resolution (ADR-029) and unified
entity config support (ADR-039).
"""

from __future__ import annotations

__all__ = ["load_pipeline_config", "load_source_config"]

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config_loader_filtering import (
    FILTER_SECTIONS,
    apply_hierarchical_filter_config,
)
from bioetl.infrastructure.config_merge import config_merge
from bioetl.infrastructure.config.source_config_loader import (
    load_source_config as _load_source_config,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def _deep_merge(
    base: JsonDict,  # Any: YAML config has heterogeneous values
    override: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Deep merge two dictionaries, with override taking precedence.

    Returns:
        Deep-merged dictionary with override values taking precedence.
    """
    return config_merge(base, override)


def _load_base_config(
    config_path: Path,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Load pipeline base configuration from consolidated base path.

    Resolution order:
    1. configs/base/pipeline.yaml (new consolidated base path)

    Returns:
        Dictionary with base pipeline configuration, or empty dict if no base file found.
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
    config: JsonDict,  # Any: YAML config has heterogeneous values
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


def _apply_layer_defaults(
    layer: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
    layer_name: str,
    sort_policy: list[str],
) -> None:
    """Apply convention-based defaults for a single medallion layer.

    Sets path and csv_export.path if not specified.
    """
    layer.setdefault("path", f"data/output/{layer_name}/{provider}/{entity_type}")
    if layer_name in {"silver", "gold"}:
        layer.setdefault("sort_by", list(sort_policy))

    # Auto-set csv_export path to match layer path
    csv_export = layer.setdefault("csv_export", {})
    csv_export.setdefault("path", layer["path"])


def _apply_convention_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Apply convention-based defaults for paths, references, and table names.

    Auto-computes from provider/entity_type when not explicitly specified.

    Returns:
        The config dictionary with convention-based defaults applied in place.
    """
    provider = config.get("provider")
    entity_type = config.get("entity_type")

    if not provider or not entity_type:
        return config

    raw_primary_keys = config.get("business_primary_keys") or config.get(
        "primary_keys", []
    )
    primary_keys = [str(key) for key in raw_primary_keys if str(key).strip()]
    technical_primary_key = str(config.get("technical_primary_key", "entity_id"))
    sort_policy = [technical_primary_key] + [
        key for key in primary_keys if key != technical_primary_key
    ]
    _apply_file_reference_defaults(config, provider, entity_type)

    # Auto-compute table names from provider + entity_type
    table_name = f"{provider}_{entity_type}"
    config.setdefault("silver_table", table_name)
    config.setdefault("gold_table", table_name)

    sink = config.setdefault("sink", {})
    for layer_name in ("bronze", "silver", "gold"):
        layer = sink.setdefault(layer_name, {})
        _apply_layer_defaults(layer, provider, entity_type, layer_name, sort_policy)

    return config


def _load_data_schema_config(
    config_path: Path, schema_file: str
) -> JsonDict | None:  # Any: YAML config has heterogeneous values
    """Compatibility wrapper for schema loader tests/importers.

    Returns:
        Dictionary with schema configuration data, or None if not found.
    """
    from bioetl.infrastructure.config import pipeline_normalizers

    return pipeline_normalizers._load_data_schema_config(
        config_path=config_path,
        schema_file=schema_file,
    )


def _validate_schema_config(
    data_schema: JsonDict,  # Any: YAML config has heterogeneous values
    schema_file: str,
) -> None:
    """Compatibility wrapper for schema validation tests/importers."""
    from bioetl.infrastructure.config import pipeline_normalizers

    pipeline_normalizers._validate_schema_config(
        data_schema=data_schema,
        schema_file=schema_file,
    )


load_source_config = _load_source_config


_FILTER_SECTIONS = FILTER_SECTIONS
_apply_hierarchical_filter_config = apply_hierarchical_filter_config


def _load_unified_entity_raw(
    path: Path,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Load unified entity YAML file, returning empty dict when absent.

    Returns:
        Dictionary with the parsed YAML content, or empty dict if file absent or not a mapping.
    """
    if not path.exists():
        return {}

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw if isinstance(raw, dict) else {}


def _get_unified_section(
    unified_raw: JsonDict,  # Any: YAML config has heterogeneous values
    section: str,
) -> JsonDict | None:  # Any: YAML config has heterogeneous values
    """Get a dict section from unified entity config if present.

    Returns:
        Dictionary section value if present and is a dict, None otherwise.
    """
    value = unified_raw.get(section)
    return value if isinstance(value, dict) else None


def _load_source_section(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Load source config from external file and merge with entity overrides.

    The source file (configs/providers/{provider}.yaml) provides base settings.
    Entity-specific source settings from the pipeline YAML override them.
    """
    source_file = config.get("source_file")
    if not source_file:
        return
    provider = config.get("provider")
    if not isinstance(provider, str) or not provider:
        return

    from bioetl.infrastructure.config.source_config_loader import load_source_config

    try:
        source_config = load_source_config(provider)
    except ValueError:
        return

    base_source = source_config.model_dump().get("source", {})
    entity_source = config.get("source", {})
    config["source"] = _deep_merge(base_source, entity_source)


@dataclass(frozen=True)
class PipelineConfigReadPayload:
    """Raw payload + context produced by pipeline-config read stage."""

    config: JsonDict  # Any: YAML config has heterogeneous values
    entity_config: JsonDict  # Any: YAML config has heterogeneous values
    config_path: Path
    unified_schema: JsonDict | None = None  # Any: YAML values are heterogeneous


def read_pipeline_config_payload(
    pipeline_name: str,
) -> PipelineConfigReadPayload:
    """Read pipeline config from unified entity YAML and merge base defaults.

    Returns:
        PipelineConfigReadPayload with merged config, entity config, path, and optional schema.
    """
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

    defaults = _load_base_config(config_path)
    merged = _deep_merge(defaults, unified_pipeline)

    return PipelineConfigReadPayload(
        config=merged,
        entity_config=unified_pipeline,
        config_path=config_path,
        unified_schema=unified_schema,
    )


def normalize_pipeline_config_payload(
    payload: PipelineConfigReadPayload,
    *,
    filter_loader: FilterConfigLoader | None = None,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Normalize pipeline payload (new + legacy shapes) before validation.

    Returns:
        Normalized pipeline config dictionary ready for Pydantic validation.
    """
    from bioetl.infrastructure.config.pipeline_normalizers import (
        apply_pipeline_schema_normalization,
    )

    config = _apply_convention_defaults(payload.config.copy())
    _apply_hierarchical_filter_config(
        config,
        payload.entity_config,
        filter_loader=filter_loader,
    )
    apply_pipeline_schema_normalization(
        config,
        entity_config=payload.entity_config,
        config_path=payload.config_path,
        unified_schema=payload.unified_schema,
    )
    _load_source_section(config, payload.config_path)

    for key in ("source_file", "data_schema", "filter_defaults", "contract_defaults"):
        config.pop(key, None)
    return config


def validate_pipeline_config_payload(
    config: JsonDict,  # Any: YAML config has heterogeneous values
) -> PipelineYamlConfig:
    """Validate normalized pipeline payload with pydantic schema.

    Returns:
        PipelineYamlConfig instance validated from the config dictionary.
    """
    return PipelineYamlConfig.model_validate(config)


def map_pipeline_config(validated_config: PipelineYamlConfig) -> PipelineYamlConfig:
    """Map validated payload to loader return type.

    Returns:
        The validated PipelineYamlConfig instance unchanged.
    """
    return validated_config


@lru_cache(maxsize=10)
def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration using read -> normalize -> validate -> map.

    Returns:
        PipelineYamlConfig instance for the given pipeline name.
    """
    return load_pipeline_config_uncached(pipeline_name)


def load_pipeline_config_uncached(
    pipeline_name: str,
    *,
    filter_loader: FilterConfigLoader | None = None,
) -> PipelineYamlConfig:
    """Load pipeline configuration using the explicit uncached pipeline path.

    Returns:
        PipelineYamlConfig instance for the given pipeline name.
    """
    raw_payload = read_pipeline_config_payload(pipeline_name)
    normalized_payload = normalize_pipeline_config_payload(
        raw_payload,
        filter_loader=filter_loader,
    )
    validated_payload = validate_pipeline_config_payload(normalized_payload)
    return map_pipeline_config(validated_payload)
