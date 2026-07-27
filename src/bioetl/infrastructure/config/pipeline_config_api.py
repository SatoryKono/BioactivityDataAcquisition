"""Canonical function-based pipeline config loading flow."""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.entity_filter_metadata_registry import (
    apply_shared_filter_metadata,
)
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config.pipeline_payload_normalization import (
    PipelineConfigReadPayload,
    normalize_pipeline_payload,
)
from bioetl.infrastructure.config_merge import config_merge
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "PipelineConfigReadPayload",
    "load_pipeline_config",
    "load_pipeline_config_from_root",
    "load_pipeline_config_uncached",
    "map_pipeline_config",
    "normalize_pipeline_config_payload",
    "read_pipeline_config_payload",
    "run_pipeline_config_flow",
    "validate_pipeline_config_payload",
]


def _deep_merge(
    base: JsonDict,
    override: JsonDict,
) -> JsonDict:
    """Deep merge two dictionaries, with override taking precedence."""
    return config_merge(base, override)


def _load_yaml_mapping(path: Path) -> JsonDict | None:
    """Load one YAML mapping via a full-file read.

    Prefer ``read_bytes`` + ``safe_load`` over a streaming file handle. On
    cloud-synced Windows worktrees a mid-stream ``yaml.safe_load(open(...))``
    can stall long enough to trip pytest-timeout while architecture suites
    re-read the same base/entity configs repeatedly.
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    data = yaml.safe_load(raw) or {}
    if not isinstance(data, dict):
        return None
    return data


@lru_cache(maxsize=16)
def _load_base_config_cached(base_path_key: str) -> JsonDict:
    """Cache shared base pipeline defaults (same file for every entity)."""
    payload = _load_yaml_mapping(Path(base_path_key))
    if payload is None:
        return {}
    base_config = dict(payload)
    base_config.pop("schema_version", None)
    return base_config


def _load_base_config(config_path: Path) -> JsonDict:
    """Load pipeline base configuration from the consolidated base path."""
    candidate_paths = (
        config_path.parent.parent.parent / "base" / "pipeline.yaml",
        config_path.parent.parent / "base" / "pipeline.yaml",
    )

    for base_path in candidate_paths:
        if not base_path.is_file():
            continue
        try:
            resolved_key = str(base_path.resolve())
        except OSError:
            resolved_key = str(base_path)
        return _load_base_config_cached(resolved_key)

    return {}


def _assert_legacy_pipeline_config_surface_absent(configs_root: Path) -> None:
    """Fail closed if the retired configs/pipelines tree reappears."""
    legacy_dir = configs_root / "pipelines"
    if legacy_dir.exists():
        raise ValueError(
            "Legacy pipeline config directory must remain absent: "
            f"{legacy_dir}. Use configs/base/pipeline.yaml and "
            "configs/entities/{provider}/{entity}.yaml only."
        )


def _load_unified_entity_raw(path: Path, *, configs_root: Path) -> JsonDict:
    """Load unified entity YAML file, returning empty dict when absent."""
    raw = _load_yaml_mapping(path)
    if raw is None:
        return {}
    return apply_shared_filter_metadata(
        configs_root=configs_root,
        config_path=path,
        payload=raw,
    )


def _get_unified_section(
    unified_raw: JsonDict,
    section: str,
) -> JsonDict | None:
    """Get a dict section from unified entity config if present."""
    value = unified_raw.get(section)
    return value if isinstance(value, dict) else None


def read_pipeline_config_payload(
    pipeline_name: str,
    *,
    configs_root: Path | None = None,
) -> PipelineConfigReadPayload:
    """Read pipeline config from unified entity YAML and merge base defaults."""
    if "_" not in pipeline_name:
        raise ValueError(
            f"Pipeline name must be in '<provider>_<entity>' format: {pipeline_name}"
        )

    provider, entity = pipeline_name.split("_", 1)
    resolved_configs_root = resolve_configs_root(configs_root)
    _assert_legacy_pipeline_config_surface_absent(resolved_configs_root)
    config_path = resolved_configs_root / "entities" / provider / f"{entity}.yaml"

    unified_raw = _load_unified_entity_raw(
        config_path,
        configs_root=resolved_configs_root,
    )
    unified_pipeline = _get_unified_section(unified_raw, "pipeline")
    unified_schema = _get_unified_section(unified_raw, "schema")
    unified_contracts = _get_unified_section(unified_raw, "contracts")
    unified_hash_policy = _get_unified_section(unified_raw, "hash_policy")

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
        unified_contracts=unified_contracts,
        unified_hash_policy=unified_hash_policy,
    )


def normalize_pipeline_config_payload(
    payload: PipelineConfigReadPayload,
    *,
    filter_loader: FilterConfigLoader,
) -> JsonDict:
    """Normalize pipeline payload into validated-config input shape."""
    return normalize_pipeline_payload(
        payload,
        filter_loader=filter_loader,
    )


def validate_pipeline_config_payload(config: JsonDict) -> PipelineYamlConfig:
    """Validate normalized pipeline payload with the canonical schema."""
    validated_config: PipelineYamlConfig = PipelineYamlConfig.model_validate(config)
    return validated_config


def map_pipeline_config(validated_config: PipelineYamlConfig) -> PipelineYamlConfig:
    """Map validated payload to the loader return type."""
    return validated_config


def run_pipeline_config_flow(
    pipeline_name: str,
    *,
    filter_loader: FilterConfigLoader | None,
    configs_root: Path | None = None,
    normalize_payload_fn: Callable[..., JsonDict],
    validate_payload_fn: Callable[[JsonDict], PipelineYamlConfig],
    map_config_fn: Callable[[PipelineYamlConfig], PipelineYamlConfig],
) -> PipelineYamlConfig:
    """Run the canonical staged pipeline-config flow with injectable seams."""
    resolved_configs_root = resolve_configs_root(configs_root)
    effective_filter_loader = filter_loader or FilterConfigLoader(resolved_configs_root)
    raw_payload = read_pipeline_config_payload(
        pipeline_name,
        configs_root=resolved_configs_root,
    )
    normalized_payload = normalize_payload_fn(
        raw_payload,
        filter_loader=effective_filter_loader,
    )
    validated_payload = validate_payload_fn(normalized_payload)
    return map_config_fn(validated_payload)


def _configs_root_cache_key(configs_root: Path | None = None) -> str:
    """Build a stable cache key for configuration root resolution."""
    return str(resolve_configs_root(configs_root))


@lru_cache(maxsize=256)
def _load_pipeline_config_cached(
    pipeline_name: str,
    _configs_root_key: str,
) -> PipelineYamlConfig:
    """Load pipeline configuration with cwd-aware caching.

    Architecture and CI config gates load most entity pipelines in one session;
    keep the cache large enough to avoid re-parsing shared base/filter YAML on
    cloud-synced Windows worktrees under suite pressure.
    """
    return load_pipeline_config_uncached(
        pipeline_name,
        configs_root=Path(_configs_root_key),
    )


def load_pipeline_config(pipeline_name: str) -> PipelineYamlConfig:
    """Load pipeline configuration using the canonical cached function flow."""
    return _load_pipeline_config_cached(pipeline_name, _configs_root_cache_key())


def load_pipeline_config_from_root(
    pipeline_name: str,
    *,
    configs_root: Path,
) -> PipelineYamlConfig:
    """Load pipeline configuration against one explicit config root."""
    return _load_pipeline_config_cached(
        pipeline_name,
        _configs_root_cache_key(configs_root),
    )


def _clear_pipeline_config_caches() -> None:
    """Drop both pipeline and shared base-config caches."""
    _load_pipeline_config_cached.cache_clear()
    _load_base_config_cached.cache_clear()


load_pipeline_config.cache_clear = _clear_pipeline_config_caches  # type: ignore[attr-defined]
load_pipeline_config.cache_info = _load_pipeline_config_cached.cache_info  # type: ignore[attr-defined]
load_pipeline_config.__wrapped__ = _load_pipeline_config_cached  # type: ignore[attr-defined]


def load_pipeline_config_uncached(
    pipeline_name: str,
    *,
    filter_loader: FilterConfigLoader | None = None,
    configs_root: Path | None = None,
) -> PipelineYamlConfig:
    """Load pipeline configuration using the explicit uncached pipeline path."""
    return run_pipeline_config_flow(
        pipeline_name,
        filter_loader=filter_loader,
        configs_root=configs_root,
        normalize_payload_fn=normalize_pipeline_config_payload,
        validate_payload_fn=validate_pipeline_config_payload,
        map_config_fn=map_pipeline_config,
    )
