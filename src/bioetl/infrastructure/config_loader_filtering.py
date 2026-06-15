"""Filter hierarchy helpers for pipeline config loader."""

from __future__ import annotations

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config.filter_config_loader import FilterConfigLoader
from bioetl.infrastructure.config_merge import config_merge

FILTER_SECTIONS: tuple[str, ...] = (
    "input_filter",
    "silver_filters",
    "gold_filters",
    "extraction_params",
    "source_profile",
)


def apply_hierarchical_filter_config(
    config: JsonDict,  # Any: YAML config has heterogeneous values
    entity_config: JsonDict,  # Any: YAML config has heterogeneous values
    *,
    filter_loader: FilterConfigLoader,
) -> None:
    """Apply filter config from the hierarchical filter system (ADR-028)."""
    provider = config.get("provider", "")
    entity_type = config.get("entity_type", "")

    if not provider or not entity_type:
        return

    inline_overrides: JsonDict = {}  # Any: YAML config has heterogeneous values
    for section in FILTER_SECTIONS:
        if section in entity_config:
            inline_overrides[section] = entity_config[section]

    filter_rules = entity_config.get("filter_rules")
    if isinstance(filter_rules, dict):
        inline_overrides = config_merge(inline_overrides, filter_rules)

    merged_filters = filter_loader.load_as_dict(
        provider,
        entity_type,
        inline_overrides or None,
    )

    for section in FILTER_SECTIONS:
        if section in merged_filters:
            config[section] = merged_filters[section]
