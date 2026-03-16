"""Configuration loading utilities.

Handles loading and merging of YAML configuration files
with convention-based path resolution (ADR-029) and unified
entity config support (ADR-039).
"""

from __future__ import annotations

__all__ = ["load_pipeline_config", "load_source_config"]

from functools import lru_cache
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    PipelineConfigReadPayload,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    _apply_file_reference_defaults as _apply_file_reference_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    _apply_layer_defaults as _apply_layer_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    apply_convention_defaults as _apply_convention_defaults_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    load_source_section as _load_source_section_impl,
)
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    normalize_pipeline_payload as _normalize_pipeline_payload_impl,
)
from bioetl.infrastructure.config.source_config_loader import (
    load_source_config as _load_source_config,
)
from bioetl.infrastructure.config_loader_filtering import (
    FILTER_SECTIONS,
    apply_hierarchical_filter_config,
)
from bioetl.infrastructure.config_merge import config_merge
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


def _apply_convention_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Compatibility wrapper delegating convention defaults to config module."""
    return _apply_convention_defaults_impl(config)


def _apply_file_reference_defaults(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
) -> None:
    """Compatibility wrapper for file-reference defaults."""
    _apply_file_reference_defaults_impl(config, provider, entity_type)


def _apply_layer_defaults(
    layer: JsonDict,  # Any: YAML config has heterogeneous values
    provider: str,
    entity_type: str,
    layer_name: str,
    sort_policy: list[str],
) -> None:
    """Compatibility wrapper for layer defaults."""
    _apply_layer_defaults_impl(
        layer,
        provider,
        entity_type,
        layer_name,
        sort_policy,
    )


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
    """Compatibility wrapper delegating source merging to config module."""
    _load_source_section_impl(config, config_path)


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
    filter_loader: FilterConfigLoader,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Compatibility wrapper delegating payload normalization to config module."""
    return _normalize_pipeline_payload_impl(
        payload,
        filter_loader=filter_loader,
    )


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


def _configs_root_cache_key() -> str:
    """Build a stable cache key for configuration root resolution.

    The loader depends on the current working directory because it resolves
    relative paths under ``configs/``. Including this key prevents stale cache
    reuse across working-directory changes in tests and tooling.
    """
    return str(Path("configs").resolve())


@lru_cache(maxsize=10)
def _load_pipeline_config_cached(
    pipeline_name: str,
    _configs_root_key: str,
) -> PipelineYamlConfig:
    """Load pipeline configuration using read -> normalize -> validate -> map.

    Returns:
        PipelineYamlConfig instance for the given pipeline name.
    """
    return load_pipeline_config_uncached(pipeline_name)


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration using read -> normalize -> validate -> map.

    The call is cached by ``pipeline_name`` and the resolved configs-root context
    to avoid leaking results between different working directories.
    """
    return _load_pipeline_config_cached(pipeline_name, _configs_root_cache_key())


# Preserve legacy cache management API used by tests and callers.
load_pipeline_config.cache_clear = _load_pipeline_config_cached.cache_clear
load_pipeline_config.cache_info = _load_pipeline_config_cached.cache_info
load_pipeline_config.__wrapped__ = _load_pipeline_config_cached


def load_pipeline_config_uncached(
    pipeline_name: str,
    *,
    filter_loader: FilterConfigLoader | None = None,
) -> PipelineYamlConfig:
    """Load pipeline configuration using the explicit uncached pipeline path.

    Returns:
        PipelineYamlConfig instance for the given pipeline name.
    """
    effective_filter_loader = filter_loader or FilterConfigLoader(Path("configs"))
    raw_payload = read_pipeline_config_payload(pipeline_name)
    normalized_payload = normalize_pipeline_config_payload(
        raw_payload,
        filter_loader=effective_filter_loader,
    )
    validated_payload = validate_pipeline_config_payload(normalized_payload)
    return map_pipeline_config(validated_payload)
