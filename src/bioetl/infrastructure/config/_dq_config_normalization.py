"""Normalization helpers for DQ config file-shape compatibility."""

from __future__ import annotations

import copy

from pydantic import TypeAdapter

from bioetl.domain.types import JsonDict

_THRESHOLD_VALUE = TypeAdapter(float)


def normalize_to_file_format(
    merged: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
    """Normalize merged DQ config into ``DQConfigFile``-compatible shape.

    Args:
        merged: Raw merged DQ config dictionary from the layered loader.

    Returns:
        Normalized copy with flat threshold keys nested and no mutation of input.
    """
    result = normalize_threshold_aliases(merged)
    _normalize_allowed_value_aliases(result)
    return result


def normalize_threshold_aliases(layer: JsonDict) -> JsonDict:
    """Normalize threshold aliases within one layer without mutating it."""
    result = copy.deepcopy(layer)
    _normalize_thresholds(result)
    return result


def _normalize_thresholds(
    result: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> None:
    """Move flat threshold keys into nested ``thresholds`` object.

    Args:
        result: Mutable DQ config dict; modified in place if flat threshold
            keys ``soft_fail_threshold`` or ``hard_fail_threshold`` are present.
    """
    if "soft_fail_threshold" not in result and "hard_fail_threshold" not in result:
        return

    thresholds = result.get("thresholds", {})
    if not isinstance(thresholds, dict):
        thresholds = {}

    for flat, nested in (
        ("soft_fail_threshold", "soft_fail"),
        ("hard_fail_threshold", "hard_fail"),
    ):
        if flat not in result:
            continue
        value = result.pop(flat)
        if nested in thresholds:
            existing = _THRESHOLD_VALUE.validate_python(thresholds[nested])
            if existing != _THRESHOLD_VALUE.validate_python(value):
                raise ValueError(
                    f"Conflicting DQ threshold aliases: {flat} and thresholds.{nested}"
                )
        thresholds[nested] = value

    result["thresholds"] = thresholds


def _normalize_allowed_value_aliases(value: object) -> None:
    """Rewrite legacy ``allowed_values`` keys to ``allowed`` in-place.

    Standalone DQ config schemas accept ``allowed`` for enum validations, while
    several provider/entity YAML surfaces still use the more explicit
    ``allowed_values`` spelling. Preserve backward compatibility by normalizing
    the legacy key before Pydantic validation.
    """
    if isinstance(value, dict):
        if "allowed_values" in value and "allowed" not in value:
            value["allowed"] = value.pop("allowed_values")
        for nested in value.values():
            _normalize_allowed_value_aliases(nested)
        return

    if isinstance(value, list):
        for item in value:
            _normalize_allowed_value_aliases(item)
