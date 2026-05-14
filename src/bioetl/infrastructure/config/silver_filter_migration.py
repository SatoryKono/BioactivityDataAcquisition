"""Silver-filter normalization helpers owned by the infrastructure boundary."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any, Literal

from bioetl.domain.filtering import BaseFilterConfig, SilverFilterConfig
from bioetl.domain.types import JsonDict

SilverFilterCompatibilityMode = Literal[
    "structural_only_auto_promote",
]

DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "structural_only_auto_promote"
)
SILVER_STRUCTURAL_FILTER_KEYS = frozenset({"required_fields", "exclude_if_present"})
SILVER_SEMANTIC_FILTER_KEYS = frozenset(
    {"columns", "ranges", "list_lengths", "list_contains"}
)


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
) -> SilverFilterConfig:
    """Return the canonical structural-only Silver config."""
    return build_structural_silver_filter_config(source)


def resolve_silver_filter_compatibility_mode(
) -> SilverFilterCompatibilityMode:
    """Return the canonical Silver filter mode captured in runtime identity."""
    return DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE


def build_silver_filter_compatibility_snapshot(
) -> JsonDict:
    """Build the manifest/effective-config identity payload for Silver filtering."""
    return {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": resolve_silver_filter_compatibility_mode(),
        "source": "default",
    }


def normalize_silver_gold_filter_payload(
    payload: Mapping[str, Any],
) -> JsonDict:
    """Promote semantic Silver rules into Gold and leave Silver structural-only."""
    result = deepcopy(dict(payload))

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
    "SILVER_SEMANTIC_FILTER_KEYS",
    "SILVER_STRUCTURAL_FILTER_KEYS",
    "SilverFilterCompatibilityMode",
    "build_silver_filter_compatibility_snapshot",
    "build_silver_filter_config_for_compatibility",
    "build_structural_silver_filter_config",
    "normalize_silver_gold_filter_payload",
    "resolve_silver_filter_compatibility_mode",
]
