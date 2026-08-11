# pyright: reportFunctionMemberAccess=false
# basedpyright residual burn-down (shrink-only product surface).
"""Source config loading pipeline.

This module keeps source loading flow explicit and narrow:
read -> normalize -> validate -> map.
Compatibility migration details are delegated to source normalizers and governed
by configs/quality/config_compatibility_registry.yaml.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.base_config_loader import _load_yaml_file
from bioetl.infrastructure.config.config_root import resolve_configs_root
from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def read_source_config_payload(
    provider: str,
    *,
    configs_root: Path | None = None,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Read provider YAML and map to source-loader input payload.

    Returns:
        Dictionary of raw source configuration payload from the provider YAML.
    """
    resolved_configs_root = resolve_configs_root(configs_root)
    unified_path = resolved_configs_root / "providers" / f"{provider}.yaml"
    if not unified_path.exists():
        raise ValueError(
            f"Source configuration file not found: {unified_path}. "
            "Create provider config with source/rate_limit/circuit_breaker settings."
        )

    unified_raw = _load_yaml_file(unified_path)

    source_section = unified_raw.get("source")
    if isinstance(source_section, dict):
        return {"source": source_section}

    raise ValueError(
        f"Provider configuration requires a top-level 'source' section: {unified_path}"
    )


def normalize_source_config_payload(
    payload: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Normalize registered source compatibility shapes to canonical schema.

    Returns:
        Normalized source configuration dictionary in canonical format.
    """
    return normalize_source_config(payload)


def validate_source_config_payload(
    payload: JsonDict,  # Any: YAML config has heterogeneous values
) -> SourceYamlConfig:
    """Validate canonical source payload with pydantic schema.

    Returns:
        SourceYamlConfig instance validated from the canonical payload.
    """
    validated_config: SourceYamlConfig = SourceYamlConfig.model_validate(payload)
    return validated_config


def map_source_config(validated_config: SourceYamlConfig) -> SourceYamlConfig:
    """Map validated source config to loader return type.

    Returns:
        SourceYamlConfig instance (identity mapping for type clarity).
    """
    return validated_config


def load_source_config_uncached(
    provider: str,
    *,
    configs_root: Path | None = None,
) -> SourceYamlConfig:
    """Load source configuration using read -> normalize -> validate -> map.

    Returns:
        SourceYamlConfig instance with fully resolved provider configuration.
    """
    raw_payload = read_source_config_payload(provider, configs_root=configs_root)
    normalized_payload = normalize_source_config_payload(raw_payload)
    validated_payload = validate_source_config_payload(normalized_payload)
    return map_source_config(validated_payload)


@lru_cache(maxsize=32)
def _load_source_config_cached(
    provider: str, configs_root_key: str
) -> SourceYamlConfig:
    return load_source_config_uncached(provider, configs_root=Path(configs_root_key))


def load_source_config(provider: str) -> SourceYamlConfig:
    """Load source configuration using the canonical cached entrypoint.

    Returns:
        Cached SourceYamlConfig instance for the given provider.
    """
    return _load_source_config_cached(provider, str(resolve_configs_root()))


def load_source_config_from_root(
    provider: str,
    *,
    configs_root: Path,
) -> SourceYamlConfig:
    """Load source configuration against one explicit config root."""
    return _load_source_config_cached(provider, str(resolve_configs_root(configs_root)))


load_source_config.cache_clear = _load_source_config_cached.cache_clear  # type: ignore[attr-defined]
load_source_config.cache_info = _load_source_config_cached.cache_info  # type: ignore[attr-defined]
load_source_config.__wrapped__ = _load_source_config_cached  # type: ignore[attr-defined]


__all__ = [
    "load_source_config",
    "load_source_config_from_root",
    "load_source_config_uncached",
    "map_source_config",
    "normalize_source_config_payload",
    "read_source_config_payload",
    "validate_source_config_payload",
]
