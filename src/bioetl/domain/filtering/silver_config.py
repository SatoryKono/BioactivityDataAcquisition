"""Silver filter configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import cast

from bioetl.domain.filtering._base_filter_config import BaseFilterConfig
from bioetl.domain.types import JsonDict

from ._filter_decision import FilterDecision
from ._filter_evaluator import (
    evaluate_exclude_if_present,
    evaluate_required_fields,
)

__all__ = [
    "FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS",
    "SILVER_STRUCTURAL_FILTER_KEYS",
    "SilverFilterConfig",
    "build_silver_filter_config_for_compatibility",
    "build_structural_silver_filter_config",
    "forbidden_semantic_silver_filter_keys",
    "validate_no_semantic_silver_filter_payload",
    "validate_structural_silver_filter_payload",
]

SILVER_STRUCTURAL_FILTER_KEYS = frozenset({"required_fields", "exclude_if_present"})
FORBIDDEN_SILVER_SEMANTIC_FILTER_KEYS = frozenset(
    {"columns", "ranges", "list_lengths", "list_contains"}
)


@dataclass(frozen=True, slots=True)
class SilverFilterConfig(BaseFilterConfig):
    """Structural-only filter configuration for the Silver layer.

    Silver may still hydrate legacy semantic buckets for compatibility, but
    runtime evaluation is intentionally limited to structural presence rules.
    Business/profile eligibility belongs to Gold.
    """

    def should_include(self, record: JsonDict) -> bool:
        """Return whether record passes structural Silver rules."""
        return self.evaluate(record).include

    def evaluate(self, record: JsonDict) -> FilterDecision:
        """Evaluate only structural Silver filter rules."""
        for decision in (
            evaluate_required_fields(self.required_fields, record),
            evaluate_exclude_if_present(self.exclude_if_present, record),
        ):
            if not decision.include:
                return decision
        return FilterDecision.allowed()

    def is_empty(self) -> bool:
        """Return whether structural Silver filtering has no active rules."""
        return not (self.required_fields or self.exclude_if_present)


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


def forbidden_semantic_silver_filter_keys(
    silver_filters: Mapping[str, object],
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
    silver_filters: Mapping[str, object],
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
    payload: Mapping[str, object],
) -> JsonDict:
    """Validate a full filter payload and return a shallow dict copy."""
    result = dict(payload)
    silver_filters = result.get("silver_filters")
    if isinstance(silver_filters, Mapping):
        validate_structural_silver_filter_payload(
            cast("Mapping[str, object]", silver_filters)
        )
    return cast("JsonDict", result)
