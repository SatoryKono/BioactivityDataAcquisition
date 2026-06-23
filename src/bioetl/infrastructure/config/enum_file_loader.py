"""Infrastructure-level enum file loading with direct I/O operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

__all__ = ["load_chembl_enums_from_file", "load_provider_enums_from_file"]


def _normalize_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if not normalized:
        raise ValueError("provider cannot be blank")
    if "/" in normalized or "\\" in normalized:
        raise ValueError("provider cannot contain path separators")
    return normalized


def _default_enum_path(provider: str, base_path: Path | None = None) -> Path:
    root = Path() if base_path is None else base_path
    return root / "configs" / "enums" / f"{provider}.yaml"


def _freeze_sequences(
    value: Any,  # Any: recursive function handles arbitrary YAML structures
) -> Any:  # Any: recursive function handles arbitrary YAML structures
    if isinstance(value, dict):
        return {str(key): _freeze_sequences(item) for key, item in value.items()}
    if isinstance(value, list):
        return tuple(_freeze_sequences(item) for item in value)
    return value


def load_provider_enums_from_file(
    provider: str,
    yaml_path: Path | None = None,
) -> dict[str, Any]:  # Any: Dynamic YAML content structure
    """Load provider enum configurations from a YAML file.

    This is an infrastructure-level function that performs direct file I/O.

    Args:
        provider: Provider name used to resolve the default enum file.
        yaml_path: Path to YAML file. If None, uses default path.

    Returns:
        Dictionary containing all enum configurations
    """
    normalized_provider = _normalize_provider(provider)
    if yaml_path is None:
        yaml_path = _default_enum_path(normalized_provider)

    with yaml_path.open() as f:
        payload = yaml.safe_load(f)
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"Enum config must be a YAML mapping: {yaml_path}")
    normalized = {str(key): value for key, value in payload.items()}
    if yaml_path == _default_enum_path(normalized_provider):
        return _freeze_sequences(normalized)
    return normalized


def load_chembl_enums_from_file(
    yaml_path: Path | None = None,
) -> dict[str, Any]:  # Any: Dynamic YAML content structure
    """Load ChEMBL enum configurations from YAML file."""
    return load_provider_enums_from_file("chembl", yaml_path)
