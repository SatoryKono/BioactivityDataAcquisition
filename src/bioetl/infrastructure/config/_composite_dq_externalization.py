"""Internal helpers for externalized composite DQ config merging."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict

__all__ = ["merge_external_dq_overrides"]


def _deep_merge_dicts(
    base: JsonDict,  # Any: YAML config has heterogeneous values
    override: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Recursively merge two dictionaries with override precedence."""
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
            continue
        merged[key] = deepcopy(value)
    return merged


def _load_external_dq_payload(
    dq_config_file: str,
    config_path: Path,
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Load and validate external DQ config, returning the dq_overrides payload."""
    dq_path = config_path.parent / dq_config_file
    if not dq_path.exists():
        raise FileNotFoundError(
            f"Composite DQ config not found: {dq_path} (referenced from {config_path})"
        )

    with dq_path.open(encoding="utf-8") as handle:
        external_raw = yaml.safe_load(handle) or {}

    if not isinstance(external_raw, dict):
        raise ValueError(f"Composite DQ config must be a mapping: {dq_path}")

    external_dq = external_raw.get("dq_overrides", external_raw)
    if not isinstance(external_dq, dict):
        raise ValueError(
            f"Composite DQ payload must be a mapping under 'dq_overrides': {dq_path}"
        )
    return external_dq


def merge_external_dq_overrides(
    raw: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Merge external composite DQ config into inline dq_overrides."""
    composite = raw.get("composite")
    if not isinstance(composite, dict):
        return

    dq_overrides = composite.get("dq_overrides")
    if not isinstance(dq_overrides, dict):
        return

    dq_config_file = dq_overrides.get("dq_config_file")
    if not isinstance(dq_config_file, str) or not dq_config_file.strip():
        return

    external_dq = _load_external_dq_payload(dq_config_file, config_path)
    inline_dq = {
        key: value for key, value in dq_overrides.items() if key != "dq_config_file"
    }
    composite["dq_overrides"] = _deep_merge_dicts(external_dq, inline_dq)
