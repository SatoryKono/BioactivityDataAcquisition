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
