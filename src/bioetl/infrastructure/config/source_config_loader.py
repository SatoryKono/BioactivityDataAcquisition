"""Source config loading pipeline.

This module keeps source loading flow explicit and narrow:
read -> normalize -> validate -> map.
Compatibility migration details are delegated to source normalizers.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def read_source_config_payload(
    provider: str,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Read provider YAML and map to source-loader input payload.

    Returns:
        Dictionary of raw source configuration payload from the provider YAML.
    """
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
        payload: JsonDict = {  # Any: dynamic payload or structural mixin boundary
            "source": source_section
        }  # Any: heterogeneous YAML values
        for key in ("entities", "entity_notes"):
            value = unified_raw.get(key)
            if value is not None:
                payload[key] = value
        return payload

    # Accept legacy-flat provider payload for compatibility with test fixtures.
    return unified_raw


def normalize_source_config_payload(
    payload: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Normalize source payload (legacy/new) to canonical schema.

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
    return SourceYamlConfig.model_validate(payload)


def map_source_config(validated_config: SourceYamlConfig) -> SourceYamlConfig:
    """Map validated source config to loader return type.

    Returns:
        SourceYamlConfig instance (identity mapping for type clarity).
    """
    return validated_config


def load_source_config_uncached(provider: str) -> SourceYamlConfig:
    """Load source configuration using read -> normalize -> validate -> map.

    Returns:
        SourceYamlConfig instance with fully resolved provider configuration.
    """
    raw_payload = read_source_config_payload(provider)
    normalized_payload = normalize_source_config_payload(raw_payload)
    validated_payload = validate_source_config_payload(normalized_payload)
    return map_source_config(validated_payload)


__all__ = [
    "load_source_config_uncached",
    "map_source_config",
    "normalize_source_config_payload",
    "read_source_config_payload",
    "validate_source_config_payload",
]
