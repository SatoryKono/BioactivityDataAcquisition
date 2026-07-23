"""Load/access helpers for architecture metric exemptions registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    build_module_path_key,
)
from bioetl.infrastructure.quality.exemptions_registry_paths import (
    resolve_registry_path as _resolve_registry_path,
)


def load_exemptions_registry(
    path: Path | str | None = None,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Load YAML exemptions registry as dictionary."""
    registry_path = _resolve_registry_path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Exemptions registry not found: {registry_path}")

    from scripts.engineering.common.repo_paths import resolve_output_path

    registry_path = resolve_output_path(registry_path)
    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Exemptions registry must be a mapping: {registry_path}")
    return raw


def get_registry_values(
    registry_name: str,
    path: Path | str | None = None,
) -> JsonDict:  # Any: DQ check values vary by check type
    """Return value-only mapping for a concrete registry section."""
    raw = load_exemptions_registry(path)
    registries = raw.get("registries", {})
    if not isinstance(registries, dict):
        raise ValueError("Invalid exemptions registry: 'registries' must be a mapping")

    entries = registries.get(registry_name, {})
    if not isinstance(entries, dict):
        raise ValueError(f"Invalid registry '{registry_name}': expected mapping")

    values: JsonDict = {}
    for name, entry in entries.items():
        if not isinstance(entry, dict) or "value" not in entry:
            raise ValueError(
                f"Invalid entry for registry '{registry_name}' key '{name}': missing 'value'"
            )
        values[name] = entry["value"]
    return values


def resolve_registry_value(
    values: JsonDict,  # Any: check-specific thresholds vary by registry
    *,
    module_path: Path | str,
    symbol_name: str | None = None,
    legacy_name: str | None = None,
) -> Any | None:  # Any: dynamic payload or structural mixin boundary
    """Resolve exemption value using canonical path key with dual-read fallback."""
    module_key = build_module_path_key(module_path)
    candidates: list[str] = []
    if symbol_name:
        candidates.append(f"{module_key}::{symbol_name}")
    candidates.append(module_key)
    if symbol_name:
        candidates.append(symbol_name)
    if legacy_name:
        candidates.append(legacy_name)
    candidates.append(Path(module_key).name)

    for candidate in candidates:
        if candidate in values:
            return values[candidate]
    return None


__all__ = [
    "build_module_path_key",
    "get_registry_values",
    "load_exemptions_registry",
    "resolve_registry_value",
]
