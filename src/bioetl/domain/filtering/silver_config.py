"""Silver filter configuration."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.filtering._base_filter_config import BaseFilterConfig
from bioetl.domain.types import JsonDict

from ._filter_decision import FilterDecision
from ._filter_evaluator import (
    evaluate_exclude_if_present,
    evaluate_required_fields,
)

__all__ = [
    "SilverFilterConfig",
]


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
