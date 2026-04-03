"""Canonical function-based DQ config resolution flow."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.config import DQConfig
from bioetl.domain.types import JsonDict
from bioetl.infrastructure.schemas.dq_config import DQConfigFile

__all__ = [
    "build_dq_cache_key",
    "map_dq_config",
    "merge_dq_config_hierarchy",
    "run_dq_config_flow",
    "validate_dq_config_payload",
]


def build_dq_cache_key(
    provider: str,
    entity: str,
    *,
    relaxed_dq: bool,
) -> str:
    """Build a stable cache key for DQ config resolution."""
    return f"{provider}:{entity}:relaxed={relaxed_dq}"


def merge_dq_config_hierarchy(
    provider: str,
    entity: str,
    *,
    inline_overrides: JsonDict | None,
    load_defaults_layer: Callable[[], JsonDict],
    load_provider_layer: Callable[[str], JsonDict],
    load_entity_layer: Callable[[str, str], JsonDict],
    deep_merge: Callable[[JsonDict, JsonDict], JsonDict],
    relaxed_dq: bool,
) -> JsonDict:
    """Build merged DQ config from defaults -> provider -> entity -> inline."""
    merged = load_defaults_layer()
    if not merged:
        raise FileNotFoundError(
            "Required DQ defaults file not found in configs/base/quality.yaml. "
            "Create defaults in this location."
        )

    for layer in (
        load_provider_layer(provider),
        load_entity_layer(provider, entity),
        inline_overrides or {},
    ):
        if layer:
            merged = deep_merge(merged, layer)

    if relaxed_dq:
        merged = deep_merge(
            merged,
            {"thresholds": {"soft_fail": 0.99, "hard_fail": 1.0}},
        )
    return merged


def validate_dq_config_payload(config: JsonDict) -> DQConfigFile:
    """Validate normalized DQ payload with the canonical schema."""
    validated_config: DQConfigFile = DQConfigFile.model_validate(config)
    return validated_config


def map_dq_config(validated_config: DQConfigFile) -> DQConfig:
    """Map validated DQ payload to the domain config."""
    return validated_config.to_domain()


def run_dq_config_flow(
    provider: str,
    entity: str,
    *,
    inline_overrides: JsonDict | None,
    load_defaults_layer: Callable[[], JsonDict],
    load_provider_layer: Callable[[str], JsonDict],
    load_entity_layer: Callable[[str, str], JsonDict],
    deep_merge: Callable[[JsonDict, JsonDict], JsonDict],
    normalize_payload: Callable[[JsonDict], JsonDict],
    validate_payload: Callable[[JsonDict], DQConfigFile],
    map_config: Callable[[DQConfigFile], DQConfig],
    relaxed_dq: bool,
) -> DQConfig:
    """Run the canonical staged DQ config resolution flow."""
    merged = merge_dq_config_hierarchy(
        provider,
        entity,
        inline_overrides=inline_overrides,
        load_defaults_layer=load_defaults_layer,
        load_provider_layer=load_provider_layer,
        load_entity_layer=load_entity_layer,
        deep_merge=deep_merge,
        relaxed_dq=relaxed_dq,
    )
    normalized = normalize_payload(merged)
    validated = validate_payload(normalized)
    return map_config(validated)
