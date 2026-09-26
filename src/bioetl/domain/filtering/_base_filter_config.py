"""Shared filter configuration logic for Silver and Gold layers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.types import JsonDict

from ._filter_decision import FilterDecision
from ._filter_evaluator import (
    evaluate_column_filters,
    evaluate_exclude_if_present,
    evaluate_list_contains_filters,
    evaluate_list_length_filters,
    evaluate_range_filters,
    evaluate_required_fields,
)
from ._filter_primitives import (
    check_column_filters,
    check_exclude_if_present,
    check_list_contains_filters,
    check_list_length_filters,
    check_range_filters,
    check_required_fields,
)

__all__ = ["BaseFilterConfig", "FilterDecision"]


def _iter_filter_decisions(
    config: BaseFilterConfig,
    record: JsonDict,
) -> tuple[FilterDecision, ...]:
    """Evaluate configured filters in order and collect their decisions."""
    return (
        evaluate_required_fields(config.required_fields, record),
        evaluate_exclude_if_present(config.exclude_if_present, record),
        evaluate_column_filters(config.column_filters, record),
        evaluate_range_filters(config.range_filters, record),
        evaluate_list_length_filters(config.list_length_filters, record),
        evaluate_list_contains_filters(config.list_contains_filters, record),
    )


@dataclass(frozen=True, slots=True)
class BaseFilterConfig:
    """Base immutable filter configuration used by Silver and Gold layers."""

    column_filters: tuple[GoldColumnFilter, ...] = ()
    range_filters: tuple[GoldRangeFilter, ...] = ()
    list_length_filters: tuple[GoldListLengthFilter, ...] = ()
    list_contains_filters: tuple[GoldListContainsFilter, ...] = ()
    required_fields: tuple[str, ...] = ()
    exclude_if_present: tuple[str, ...] = ()

    @classmethod
    def from_base(cls, other: BaseFilterConfig) -> Self:
        """Create same-type filter config from another base config."""
        return cls(
            column_filters=other.column_filters,
            range_filters=other.range_filters,
            list_length_filters=other.list_length_filters,
            list_contains_filters=other.list_contains_filters,
            required_fields=other.required_fields,
            exclude_if_present=other.exclude_if_present,
        )

    def should_include(self, record: JsonDict) -> bool:
        """Check all filtering rules against a record."""
        decision = self.evaluate(record)
        include: bool = decision.include
        return include

    def evaluate(self, record: JsonDict) -> FilterDecision:
        """Evaluate all filter rules and return the first blocking decision."""
        for decision in _iter_filter_decisions(self, record):
            if not decision.include:
                return decision

        return FilterDecision.allowed()

    def _check_required_fields(self, record: JsonDict) -> bool:
        """Check that all required fields are present and non-empty."""
        is_valid: bool = check_required_fields(self.required_fields, record)
        return is_valid

    def _check_exclude_if_present(self, record: JsonDict) -> bool:
        """Check that exclusion fields are absent or empty."""
        is_valid: bool = check_exclude_if_present(self.exclude_if_present, record)
        return is_valid

    def _check_column_filters(self, record: JsonDict) -> bool:
        """Check that column values match the configured filters."""
        is_valid: bool = check_column_filters(self.column_filters, record)
        return is_valid

    def _check_range_filters(self, record: JsonDict) -> bool:
        """Check that values fall within the configured ranges."""
        is_valid: bool = check_range_filters(self.range_filters, record)
        return is_valid

    def _check_list_length_filters(self, record: JsonDict) -> bool:
        """Check list lengths in columns against configured bounds."""
        is_valid: bool = check_list_length_filters(self.list_length_filters, record)
        return is_valid

    def _check_list_contains_filters(self, record: JsonDict) -> bool:
        """Check list-contains filters against record values."""
        is_valid: bool = check_list_contains_filters(
            self.list_contains_filters,
            record,
        )
        return is_valid

    def is_empty(self) -> bool:
        """Check whether the filter configuration is empty."""
        all_filters = (
            self.column_filters,
            self.range_filters,
            self.list_length_filters,
            self.list_contains_filters,
            self.required_fields,
            self.exclude_if_present,
        )
        return not any(all_filters)
