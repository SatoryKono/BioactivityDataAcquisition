"""Normalization helpers for DQ config file-shape compatibility."""

from __future__ import annotations

import copy

from bioetl.domain.types import JsonDict


def normalize_to_file_format(
    merged: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> JsonDict:  # Any: YAML DQ config has heterogeneous values
    """Normalize merged DQ config into ``DQConfigFile``-compatible shape."""
    result = copy.deepcopy(merged)
    _normalize_thresholds(result)

    _promote_list_key(
        result,
        legacy_key="field_validations",
        target_key="entity_field_validations",
    )
    _promote_list_key(
        result,
        legacy_key="cross_field_validations",
        target_key="entity_cross_field_validations",
    )
    _promote_list_key(
        result,
        legacy_key="conditional_validations",
        target_key="entity_conditional_validations",
    )
    _promote_list_key(
        result,
        legacy_key="key_nullability_rules",
        target_key="key_nullability",
    )
    return result


def _normalize_thresholds(
    result: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> None:
    """Move flat threshold keys into nested ``thresholds`` object."""
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


def _promote_list_key(
    result: JsonDict,  # Any: YAML DQ config has heterogeneous values
    *,
    legacy_key: str,
    target_key: str,
) -> None:
    """Move list under ``legacy_key`` to ``target_key`` preserving existing entries."""
    if legacy_key not in result:
        return

    result.setdefault(target_key, [])
    target_values = result[target_key]
    legacy_values = result.pop(legacy_key)
    if isinstance(target_values, list) and isinstance(legacy_values, list):
        target_values.extend(legacy_values)
