"""Silver-filter compatibility facade for infrastructure config callers."""

from __future__ import annotations

from bioetl.domain.filtering.silver_config import (
    FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS,
    SILVER_STRUCTURAL_FILTER_KEYS,
    build_silver_filter_config_for_compatibility,
    build_structural_silver_filter_config,
    forbidden_semantic_silver_filter_keys,
    validate_no_semantic_silver_filter_payload,
    validate_structural_silver_filter_payload,
)
from bioetl.domain.filtering.silver_filter_identity import (
    DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE,
    HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE,
    SilverFilterCompatibilityMode,
    build_silver_filter_compatibility_snapshot,
    normalize_silver_filter_compatibility_mode,
    resolve_silver_filter_compatibility_mode,
)

__all__ = [
    "DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE",
    "FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS",
    "HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE",
    "SILVER_STRUCTURAL_FILTER_KEYS",
    "SilverFilterCompatibilityMode",
    "build_silver_filter_compatibility_snapshot",
    "build_silver_filter_config_for_compatibility",
    "build_structural_silver_filter_config",
    "forbidden_semantic_silver_filter_keys",
    "normalize_silver_filter_compatibility_mode",
    "resolve_silver_filter_compatibility_mode",
    "validate_no_semantic_silver_filter_payload",
    "validate_structural_silver_filter_payload",
]
