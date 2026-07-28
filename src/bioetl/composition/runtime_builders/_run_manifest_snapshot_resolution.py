"""Text and mapping resolution helpers for manifest snapshot builders."""

from __future__ import annotations

from collections.abc import Mapping

__all__ = [
    "as_runtime_config_mapping",
    "coerce_optional_text",
    "resolve_mapping_text",
    "resolve_name_component",
    "resolve_replay_parentage_mapping_value",
]

def as_runtime_config_mapping(runtime_config: object) -> Mapping[str, object]:
    """Return a mapping view for runtime config-like objects."""
    if isinstance(runtime_config, Mapping):
        return runtime_config
    return {}

def resolve_mapping_text(mapping: object, key: str) -> str | None:
    """Read one optional text value from a mapping-like object."""
    if not isinstance(mapping, Mapping):
        return None
    return coerce_optional_text(mapping.get(key))

def resolve_replay_parentage_mapping_value(
    runtime_config: Mapping[str, object],
    *keys: str,
) -> str | None:
    """Resolve replay parentage from direct and nested runtime config mappings."""
    candidate_mappings: tuple[object, ...] = (
        runtime_config,
        runtime_config.get("control_plane"),
        runtime_config.get("pipeline"),
        as_runtime_config_mapping(runtime_config.get("pipeline")).get("control_plane"),
    )
    for key in keys:
        for mapping in candidate_mappings:
            resolved = resolve_mapping_text(mapping, key)
            if resolved is not None:
                return resolved
    return None

def resolve_name_component(value: object, *, fallback: str) -> str:
    """Return a normalized provider/entity component or the fallback."""
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    return fallback

def coerce_optional_text(value: object) -> str | None:
    """Normalize one optional runtime/YAML value into stripped text."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None
