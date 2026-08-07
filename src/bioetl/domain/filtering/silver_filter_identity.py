"""Silver-filter runtime identity helpers.

These helpers are pure domain policy: they describe the canonical Silver filter
compatibility identity captured in run manifests and effective-config artifacts.
"""

from __future__ import annotations

from bioetl.domain.config.runtime import (
    CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE,
    LEGACY_SILVER_FILTER_COMPATIBILITY_MODE,
    SILVER_FILTER_COMPATIBILITY_MODES,
    SilverFilterCompatibilityMode,
)
from bioetl.domain.types import JsonDict

__all__ = [
    "DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE",
    "HISTORICAL_SILVER_FILTER_COMPATIBILITY_MODE",
    "SilverFilterCompatibilityMode",
    "build_silver_filter_compatibility_snapshot",
    "normalize_silver_filter_compatibility_mode",
    "resolve_silver_filter_compatibility_mode",
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
    if normalized == CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE:
        return CANONICAL_SILVER_FILTER_COMPATIBILITY_MODE
    if normalized == LEGACY_SILVER_FILTER_COMPATIBILITY_MODE:
        return LEGACY_SILVER_FILTER_COMPATIBILITY_MODE
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
