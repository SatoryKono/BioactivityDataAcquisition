"""Shared governance prefixes for Stream B config-surface burn-down."""

from __future__ import annotations

INTENTIONAL_PREFIXES: tuple[str, ...] = (
    "hash_policy",
    "hash_policy.",
    "filters.extraction_params.",
    "filters.gold_filters.columns.",
    "filters.gold_filters.list_contains.",
    "filters.gold_filters.list_lengths.",
    "filters.gold_filters.ranges.",
    "filters.silver_filters.columns.",
    "filters.silver_filters.ranges.",
    "pipeline.page_size_override",
    "pipeline.field_policy.therapeutic_flag",
    "pipeline.source.",
    "quality.thresholds",
    "composite.",
)


def is_sanctioned_partial_key(key: str) -> bool:
    """Return True when a partial matrix key is documented intentional drift."""
    return any(
        key == prefix or key.startswith(f"{prefix}.") or key.startswith(prefix)
        for prefix in INTENTIONAL_PREFIXES
    )
