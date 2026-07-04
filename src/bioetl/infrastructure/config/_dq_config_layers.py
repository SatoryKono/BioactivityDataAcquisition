"""Internal helpers for hierarchical DQ config loading."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from bioetl.domain.types import JsonDict

LoadYamlFn = Callable[[Path], JsonDict]

_PROVIDER_FALLBACK_KEYS = (
    "thresholds",
    "provider_field_validations",
)
_ENTITY_FALLBACK_KEYS = (
    "thresholds",
    "entity_field_validations",
    "entity_cross_field_validations",
    "entity_conditional_validations",
    "key_nullability",
)


def load_defaults_layer(base_root: Path, load_yaml: LoadYamlFn) -> JsonDict:
    """Load DQ defaults from ``configs/base/quality.yaml`` if present.

    Args:
        base_root: Path to the ``configs/base/`` directory.
        load_yaml: Callable that reads and parses a YAML file to a dict.

    Returns:
        Dictionary with global DQ defaults, or empty dict if file does not exist.
    """
    defaults_path = base_root / "quality.yaml"
    if defaults_path.exists():
        return load_yaml(defaults_path)
    return {}


def load_provider_layer(
    configs_root: Path, provider: str, load_yaml: LoadYamlFn
) -> JsonDict:
    """Load provider DQ layer from ``configs/providers/{provider}.yaml``.

    Args:
        configs_root: Root configs directory containing the ``providers/`` subdirectory.
        provider: Provider name (e.g., ``"chembl"``).
        load_yaml: Callable that reads and parses a YAML file to a dict.

    Returns:
        Dictionary with provider-level DQ config, or empty dict if file absent.
    """
    provider_path = configs_root / "providers" / f"{provider}.yaml"
    return _load_unified_quality_layer(
        layer_path=provider_path,
        fallback_keys=_PROVIDER_FALLBACK_KEYS,
        load_yaml=load_yaml,
    )


def load_entity_layer(
    configs_root: Path,
    provider: str,
    entity: str,
    load_yaml: LoadYamlFn,
) -> JsonDict:
    """Load entity DQ layer from ``configs/entities/{provider}/{entity}.yaml``.

    Args:
        configs_root: Root configs directory containing the ``entities/`` subdirectory.
        provider: Provider name (e.g., ``"chembl"``).
        entity: Entity type name (e.g., ``"activity"``).
        load_yaml: Callable that reads and parses a YAML file to a dict.

    Returns:
        Dictionary with entity-level DQ config, or empty dict if file absent.
    """
    entity_path = configs_root / "entities" / provider / f"{entity}.yaml"
    return _load_unified_quality_layer(
        layer_path=entity_path,
        fallback_keys=_ENTITY_FALLBACK_KEYS,
        load_yaml=load_yaml,
    )


def _load_unified_quality_layer(
    *,
    layer_path: Path,
    fallback_keys: tuple[str, ...],
    load_yaml: LoadYamlFn,
) -> JsonDict:
    """Load ``quality`` section or fallback to flat DQ keys for compatibility.

    Args:
        layer_path: Absolute path to the unified YAML config file.
        fallback_keys: Tuple of top-level key names to accept as a flat
            DQ config when no ``quality:`` section is present.
        load_yaml: Callable that reads and parses a YAML file to a dict.

    Returns:
        Dictionary with the quality config section, flat DQ config, or empty dict
        if the file does not exist or contains no recognizable DQ keys.
    """
    if not layer_path.exists():
        return {}

    raw = load_yaml(layer_path)
    quality_section = raw.get("quality")
    if isinstance(quality_section, dict):
        return quality_section

    if any(key in raw for key in fallback_keys):
        return raw
    return {}
