"""Composite DQ config externalization helpers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml

from bioetl.domain.types import JsonDict


def _deep_merge_dicts(
    base: JsonDict,  # Any: YAML config has heterogeneous values
    override: JsonDict,  # Any: YAML config has heterogeneous values
) -> JsonDict:  # Any: YAML config has heterogeneous values
    """Recursively merge two dictionaries with override precedence.

    Performs a deep merge: nested dicts are merged recursively while scalar
    values in ``override`` always win over ``base``. The original dicts are
    not mutated — a deep copy is returned.

    Args:
        base: Base dictionary providing default values.
        override: Dictionary whose values take precedence over base.

    Returns:
        New merged dictionary combining base and override values.
    """
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
            continue
        merged[key] = deepcopy(value)
    return merged


def merge_external_dq_overrides(
    raw: JsonDict,  # Any: YAML config has heterogeneous values
    config_path: Path,
) -> None:
    """Merge external composite DQ config file into inline dq_overrides.

    Merge order:
    1. External dq_config_file payload
    2. Inline dq_overrides values (highest precedence)

    Mutates ``raw`` in-place by replacing the ``composite.dq_overrides`` key
    with the merged result. Returns immediately without error if the
    ``composite``, ``dq_overrides``, or ``dq_config_file`` keys are absent.

    Args:
        raw: Mutable YAML payload dict as loaded from the composite config file.
        config_path: Path to the composite YAML config file, used to resolve
            the relative path of the external DQ config file.

    Raises:
        FileNotFoundError: If the referenced dq_config_file does not exist.
        ValueError: If the external DQ config file is not a valid YAML mapping.
    """
    composite = raw.get("composite")
    if not isinstance(composite, dict):
        return

    dq_overrides = composite.get("dq_overrides")
    if not isinstance(dq_overrides, dict):
        return

    dq_config_file = dq_overrides.get("dq_config_file")
    if not isinstance(dq_config_file, str) or not dq_config_file.strip():
        return

    dq_path = config_path.parent / dq_config_file
    if not dq_path.exists():
        raise FileNotFoundError(
            f"Composite DQ config not found: {dq_path} (referenced from {config_path})"
        )

    with dq_path.open(encoding="utf-8") as f:
        external_raw = yaml.safe_load(f) or {}

    if not isinstance(external_raw, dict):
        raise ValueError(f"Composite DQ config must be a mapping: {dq_path}")

    external_dq = external_raw.get("dq_overrides", external_raw)
    if not isinstance(external_dq, dict):
        raise ValueError(
            f"Composite DQ payload must be a mapping under 'dq_overrides': {dq_path}"
        )

    inline_dq = {
        key: value for key, value in dq_overrides.items() if key != "dq_config_file"
    }
    composite["dq_overrides"] = _deep_merge_dicts(external_dq, inline_dq)


__all__ = ["merge_external_dq_overrides"]
