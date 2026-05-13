"""Silver-filter migration helpers owned by the infrastructure boundary."""

from __future__ import annotations

import os
from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from bioetl.domain.filtering import BaseFilterConfig, SilverFilterConfig
from bioetl.domain.types import JsonDict

SilverFilterCompatibilityMode = Literal[
    "structural_only_auto_promote",
    "legacy_semantic_silver",
]

DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "structural_only_auto_promote"
)
LEGACY_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "legacy_semantic_silver"
)
LEGACY_SILVER_FILTER_ENV = "BIOETL_LEGACY_SILVER_SEMANTIC"
SILVER_STRUCTURAL_FILTER_KEYS = frozenset({"required_fields", "exclude_if_present"})
SILVER_SEMANTIC_FILTER_KEYS = frozenset(
    {"columns", "ranges", "list_lengths", "list_contains"}
)

_TRUTHY_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


def build_structural_silver_filter_config(
    source: BaseFilterConfig,
) -> SilverFilterConfig:
    """Return a Silver config containing only structural filter rules."""
    return SilverFilterConfig(
        required_fields=source.required_fields,
        exclude_if_present=source.exclude_if_present,
    )


def build_silver_filter_config_for_compatibility(
    source: BaseFilterConfig,
    *,
    compatibility_mode: SilverFilterCompatibilityMode | None = None,
) -> SilverFilterConfig:
    """Return a Silver config that honors the active migration compatibility mode."""
    resolved_mode = compatibility_mode or resolve_silver_filter_compatibility_mode()
    if resolved_mode == LEGACY_SILVER_FILTER_COMPATIBILITY_MODE:
        return SilverFilterConfig.from_base(source)
    return build_structural_silver_filter_config(source)


def resolve_silver_filter_compatibility_mode(
    env: Mapping[str, str] | None = None,
) -> SilverFilterCompatibilityMode:
    """Resolve the explicit Silver filter compatibility mode."""
    environ = os.environ if env is None else env
    raw_legacy_flag = environ.get(LEGACY_SILVER_FILTER_ENV, "")
    if raw_legacy_flag.strip().lower() in _TRUTHY_ENV_VALUES:
        return LEGACY_SILVER_FILTER_COMPATIBILITY_MODE
    return DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE


def build_silver_filter_compatibility_snapshot(
    env: Mapping[str, str] | None = None,
) -> JsonDict:
    """Build the manifest/effective-config identity payload for Silver filtering."""
    mode = resolve_silver_filter_compatibility_mode(env)
    source = (
        f"environment:{LEGACY_SILVER_FILTER_ENV}"
        if mode == LEGACY_SILVER_FILTER_COMPATIBILITY_MODE
        else "default"
    )
    return {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": mode,
        "source": source,
    }


def normalize_silver_gold_filter_payload(
    payload: Mapping[str, Any],
    *,
    compatibility_mode: SilverFilterCompatibilityMode | None = None,
) -> JsonDict:
    """Promote semantic Silver rules into Gold and leave Silver structural-only."""
    result = deepcopy(dict(payload))
    resolved_mode = compatibility_mode or resolve_silver_filter_compatibility_mode()
    if resolved_mode == LEGACY_SILVER_FILTER_COMPATIBILITY_MODE:
        return result

    silver_filters = result.get("silver_filters")
    if not isinstance(silver_filters, dict):
        return result

    gold_filters = result.get("gold_filters")
    if not isinstance(gold_filters, dict):
        gold_filters = {}

    structural_silver = {
        key: deepcopy(value)
        for key, value in silver_filters.items()
        if key in SILVER_STRUCTURAL_FILTER_KEYS
    }
    promoted_gold = deepcopy(gold_filters)
    for key in SILVER_SEMANTIC_FILTER_KEYS:
        silver_section = silver_filters.get(key)
        if not isinstance(silver_section, dict) or not silver_section:
            continue
        gold_section = promoted_gold.get(key)
        if not isinstance(gold_section, dict):
            gold_section = {}
        for field_name, silver_value in silver_section.items():
            gold_section.setdefault(field_name, deepcopy(silver_value))
        promoted_gold[key] = gold_section

    result["silver_filters"] = structural_silver
    result["gold_filters"] = promoted_gold
    return result


__all__ = [
    "DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE",
    "LEGACY_SILVER_FILTER_COMPATIBILITY_MODE",
    "LEGACY_SILVER_FILTER_ENV",
    "SILVER_SEMANTIC_FILTER_KEYS",
    "SILVER_STRUCTURAL_FILTER_KEYS",
    "SilverFilterCompatibilityMode",
    "build_silver_filter_compatibility_snapshot",
    "build_silver_filter_config_for_compatibility",
    "build_structural_silver_filter_config",
    "normalize_silver_gold_filter_payload",
    "resolve_silver_filter_compatibility_mode",
]
