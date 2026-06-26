"""Silver-filter structural boundary helpers owned by infrastructure."""

from __future__ import annotations

from typing import Literal, cast

from bioetl.domain.config.runtime import (
    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
    LEGACY_SILVER_FILTER_COMPATIBILITY_MODE,
    SILVER_FILTER_COMPATIBILITY_MODES,
)
from bioetl.domain.filtering.silver_config import (
    FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS,
    SILVER_STRUCTURAL_FILTER_KEYS,
    build_silver_filter_config_for_compatibility,
    build_structural_silver_filter_config,
    forbidden_semantic_silver_filter_keys,
    validate_no_semantic_silver_filter_payload,
    validate_structural_silver_filter_payload,
)
from bioetl.domain.types import JsonDict

SilverFilterCompatibilityMode = Literal[
    "structural_only_compat",
    "structural_only_auto_promote",
]

DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
)
HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    LEGACY_SILVER_FILTER_COMPATIBILITY_MODE
)


def resolve_silver_filter_compatibility_mode() -> SilverFilterCompatibilityMode:
    """Return the canonical Silver filter mode captured in runtime identity."""
    return DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE


def normalize_silver_filter_compatibility_mode(
    mode: str | None,
) -> SilverFilterCompatibilityMode:
    """Normalize persisted Silver filter mode values without rewriting history."""
    if mode is None:
        return DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE
    normalized = mode.strip()
    if normalized in SILVER_FILTER_COMPATIBILITY_MODES:
        return cast(SilverFilterCompatibilityMode, normalized)
    raise ValueError(
        "Unsupported silver_filter_compatibility_mode "
        f"{mode!r}; expected one of {sorted(SILVER_FILTER_COMPATIBILITY_MODES)!r}"
    )


def build_silver_filter_compatibility_snapshot() -> JsonDict:
    """Build the manifest/effective-config identity payload for Silver filtering."""
    return {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": resolve_silver_filter_compatibility_mode(),
        "source": "default",
    }


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
