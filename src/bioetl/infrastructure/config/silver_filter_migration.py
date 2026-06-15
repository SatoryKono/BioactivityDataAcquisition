"""Silver-filter structural boundary helpers owned by infrastructure."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from bioetl.domain.filtering import BaseFilterConfig, SilverFilterConfig
from bioetl.domain.types import JsonDict

SilverFilterCompatibilityMode = Literal["structural_only_auto_promote",]

DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE: SilverFilterCompatibilityMode = (
    "structural_only_auto_promote"
)
SILVER_STRUCTURAL_FILTER_KEYS = frozenset({"required_fields", "exclude_if_present"})
FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS = frozenset(
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
    """Return the canonical structural-only Silver config.

    The import path is retained for existing runtime identity helpers; it no
    longer performs or implies semantic Silver-to-Gold promotion.
    """
    return build_structural_silver_filter_config(source)


def resolve_silver_filter_compatibility_mode() -> SilverFilterCompatibilityMode:
    """Return the canonical Silver filter mode captured in runtime identity."""
    return DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE


def build_silver_filter_compatibility_snapshot() -> JsonDict:
    """Build the manifest/effective-config identity payload for Silver filtering."""
    return {
        "schema_version": "silver-filter-compatibility-v1",
        "mode": resolve_silver_filter_compatibility_mode(),
        "source": "default",
    }


def forbidden_semantic_silver_filter_keys(
    silver_filters: Mapping[str, Any],
) -> tuple[str, ...]:
    """Return semantic Silver keys present in a Silver filter payload."""
    return tuple(
        sorted(
            key
            for key in FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS
            if key in silver_filters
        )
    )


def validate_structural_silver_filter_payload(
    silver_filters: Mapping[str, Any],
    *,
    path: str = "silver_filters",
) -> None:
    """Reject semantic keys in a Silver filter payload."""
    forbidden = forbidden_semantic_silver_filter_keys(silver_filters)
    if not forbidden:
        return

    qualified = ", ".join(f"{path}.{key}" for key in forbidden)
    raise ValueError(
        "Semantic filter keys are not allowed under silver_filters after "
        f"ADR-050 cleanup: {qualified}. Move semantic/business filters to "
        "gold_filters or source_profile."
    )


def validate_no_semantic_silver_filter_payload(
    payload: Mapping[str, Any],  # Any: Filter payloads have heterogeneous value types
) -> JsonDict:
    """Validate a full filter payload and return a shallow dict copy."""
    result = dict(payload)
    silver_filters = result.get("silver_filters")
    if isinstance(silver_filters, Mapping):
        validate_structural_silver_filter_payload(silver_filters)
    return result


__all__ = [
    "DEFAULT_SILVER_FILTER_COMPATIBILITY_MODE",
    "FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS",
    "SILVER_STRUCTURAL_FILTER_KEYS",
    "SilverFilterCompatibilityMode",
    "build_silver_filter_compatibility_snapshot",
    "build_silver_filter_config_for_compatibility",
    "build_structural_silver_filter_config",
    "forbidden_semantic_silver_filter_keys",
    "resolve_silver_filter_compatibility_mode",
    "validate_no_semantic_silver_filter_payload",
    "validate_structural_silver_filter_payload",
]
