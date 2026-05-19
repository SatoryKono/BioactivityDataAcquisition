"""Normalization helpers for DQ config file-shape compatibility."""

from __future__ import annotations

import copy

from bioetl.domain.types import JsonDict


def normalize_to_file_format(
    merged: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
    """Normalize merged DQ config into ``DQConfigFile``-compatible shape.

    Args:
        merged: Raw merged DQ config dictionary from the layered loader.

    Returns:
        Normalized copy with flat threshold keys nested and no mutation of input.
    """
    result = copy.deepcopy(merged)
    _normalize_thresholds(result)
    _normalize_allowed_value_aliases(result)
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

    if "soft_fail_threshold" in result:
        thresholds["soft_fail"] = result.pop("soft_fail_threshold")
    if "hard_fail_threshold" in result:
        thresholds["hard_fail"] = result.pop("hard_fail_threshold")

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
