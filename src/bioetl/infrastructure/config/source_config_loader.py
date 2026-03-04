"""Source config loading pipeline.

This module keeps source loading flow explicit and narrow:
read -> normalize -> validate -> map.
Legacy migration details are delegated to ``legacy_normalizers``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioetl.infrastructure.legacy_normalizers.source import normalize_source_config
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig


def read_source_config_payload(
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
        payload: dict[str, Any] = {
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
    payload: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> dict[str, Any]:  # Any: YAML config has heterogeneous values
    """Normalize source payload (legacy/new) to canonical schema."""
    return normalize_source_config(payload)


def validate_source_config_payload(
    payload: dict[str, Any],  # Any: YAML config has heterogeneous values
) -> SourceYamlConfig:
    """Validate canonical source payload with pydantic schema."""
    return SourceYamlConfig.model_validate(payload)


def map_source_config(validated_config: SourceYamlConfig) -> SourceYamlConfig:
    """Map validated source config to loader return type."""
    return validated_config


def load_source_config_uncached(provider: str) -> SourceYamlConfig:
    """Load source configuration using read -> normalize -> validate -> map."""
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
