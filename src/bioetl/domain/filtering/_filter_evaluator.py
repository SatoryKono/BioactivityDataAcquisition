"""Decision-building helpers for Silver and Gold filter configs."""

from __future__ import annotations

from bioetl.domain.filtering.column_filter import GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.types import JsonDict

from ._filter_decision import FilterDecision
from ._filter_primitives import (
    check_single_column,
    check_single_list_contains,
    check_single_list_length,
    check_single_range,
    get_list_length,
    is_empty_value,
)


def evaluate_required_fields(
    required_fields: tuple[str, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate required-field rules."""
    for field in required_fields:
        actual = record.get(field)
        if is_empty_value(actual):
            return FilterDecision.rejected(
                reason_code="required_field_missing",
                rule_type="required_fields",
                field=field,
                operator="is_not_null",
                expected="non-empty",
                actual=actual,
                message=f"Missing required Silver field: {field}",
            )
    return FilterDecision.allowed()


def evaluate_exclude_if_present(
    exclude_if_present: tuple[str, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate exclusion-by-presence rules."""
    for field in exclude_if_present:
        actual = record.get(field)
        if actual not in (None, ""):
            return FilterDecision.rejected(
                reason_code="exclude_if_present",
                rule_type="exclude_if_present",
                field=field,
                operator="is_null",
                expected="empty",
                actual=actual,
                message=f"Field '{field}' triggered exclusion because it is present",
            )
    return FilterDecision.allowed()


def evaluate_column_filters(
    column_filters: tuple[GoldColumnFilter, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate configured column filters."""
    for column_filter in column_filters:
        if check_single_column(record, column_filter):
            continue
        actual = record.get(column_filter.column)
        expected = (
            sorted(
                column_filter.values,
                key=lambda value: (type(value).__name__, str(value)),
            )
            if column_filter.values is not None
            else None
        )
        return FilterDecision.rejected(
            reason_code="column_filter_mismatch",
            rule_type="column_filters",
            field=column_filter.column,
            operator=column_filter.operator.value,
            expected=expected,
            actual=actual,
            message=(
                f"Field '{column_filter.column}' failed column filter "
                f"{column_filter.operator.value}"
            ),
        )
    return FilterDecision.allowed()


def evaluate_range_filters(
    range_filters: tuple[GoldRangeFilter, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate numeric range filters."""
    for range_filter in range_filters:
        if check_single_range(record, range_filter):
            continue
        actual = record.get(range_filter.column)
        expected: JsonDict = {
            "min_value": range_filter.min_value,
            "max_value": range_filter.max_value,
            "include_min": range_filter.include_min,
            "include_max": range_filter.include_max,
        }
        return FilterDecision.rejected(
            reason_code="range_filter_mismatch",
            rule_type="range_filters",
            field=range_filter.column,
            operator="range",
            expected=expected,
            actual=actual,
            message=f"Field '{range_filter.column}' failed numeric range filter",
        )
    return FilterDecision.allowed()


def evaluate_list_length_filters(
    list_length_filters: tuple[GoldListLengthFilter, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate list-length filters."""
    for list_filter in list_length_filters:
        if check_single_list_length(record, list_filter):
            continue
        actual = get_list_length(record.get(list_filter.column))
        expected: JsonDict = {
            "min_length": list_filter.min_length,
            "max_length": list_filter.max_length,
        }
        return FilterDecision.rejected(
            reason_code="list_length_filter_mismatch",
            rule_type="list_length_filters",
            field=list_filter.column,
            operator="list_length",
            expected=expected,
            actual=actual,
            message=f"Field '{list_filter.column}' failed list-length filter",
        )
    return FilterDecision.allowed()


def evaluate_list_contains_filters(
    list_contains_filters: tuple[GoldListContainsFilter, ...],
    record: JsonDict,
) -> FilterDecision:
    """Evaluate list-contains filters."""
    for contains_filter in list_contains_filters:
        if check_single_list_contains(record, contains_filter):
            continue
        actual = record.get(contains_filter.column)
        expected: JsonDict = {
            "values": sorted(contains_filter.values),
            "mode": contains_filter.mode,
        }
        return FilterDecision.rejected(
            reason_code="list_contains_filter_mismatch",
            rule_type="list_contains_filters",
            field=contains_filter.column,
            operator=f"list_contains:{contains_filter.mode}",
            expected=expected,
            actual=actual,
            message=f"Field '{contains_filter.column}' failed list-contains filter",
        )
    return FilterDecision.allowed()
