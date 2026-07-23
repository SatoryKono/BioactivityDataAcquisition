"""Primitive checks used by filter evaluators."""

from __future__ import annotations

import json
from collections.abc import Callable

from bioetl.domain.filtering.column_filter import FilterOperator, GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.types import JsonDict

type FilterScalar = str | int | bool


def check_required_fields(required_fields: tuple[str, ...], record: JsonDict) -> bool:
    """Check that all required fields are present and non-empty."""
    return all(not is_empty_value(record.get(field)) for field in required_fields)


def check_exclude_if_present(
    exclude_if_present: tuple[str, ...],
    record: JsonDict,
) -> bool:
    """Check that exclusion fields are absent or empty."""
    return all(is_empty_value(record.get(field)) for field in exclude_if_present)


def check_column_filters(
    column_filters: tuple[GoldColumnFilter, ...],
    record: JsonDict,
) -> bool:
    """Check that column values match the configured filters."""
    return all(
        check_single_column(record, column_filter) for column_filter in column_filters
    )


def check_range_filters(
    range_filters: tuple[GoldRangeFilter, ...],
    record: JsonDict,
) -> bool:
    """Check that values fall within the configured ranges."""
    return all(
        check_single_range(record, range_filter) for range_filter in range_filters
    )


def check_list_length_filters(
    list_length_filters: tuple[GoldListLengthFilter, ...],
    record: JsonDict,
) -> bool:
    """Check list lengths in columns against configured bounds."""
    return all(
        check_single_list_length(record, list_filter)
        for list_filter in list_length_filters
    )


def check_list_contains_filters(
    list_contains_filters: tuple[GoldListContainsFilter, ...],
    record: JsonDict,
) -> bool:
    """Check list-contains filters against record values."""
    return all(
        check_single_list_contains(record, contains_filter)
        for contains_filter in list_contains_filters
    )


def check_single_column(record: JsonDict, column_filter: GoldColumnFilter) -> bool:
    """Check a single column value against its filter operator."""
    value = record.get(column_filter.column)
    checker = _OPERATOR_CHECKERS.get(column_filter.operator)
    if checker is None:
        return False
    return checker(value, column_filter.values)


def check_single_range(record: JsonDict, range_filter: GoldRangeFilter) -> bool:
    """Check a single value against a range filter."""
    value = record.get(range_filter.column)
    if value is None or value == "":
        return False
    try:
        numeric_value = float(value)
    except (ValueError, TypeError):
        return False
    return in_range(numeric_value, range_filter)


def check_single_list_length(
    record: JsonDict,
    list_filter: GoldListLengthFilter,
) -> bool:
    """Check the length of a single list column."""
    return length_in_bounds(
        get_list_length(record.get(list_filter.column)),
        list_filter.min_length,
        list_filter.max_length,
    )


def check_single_list_contains(
    record: JsonDict,
    contains_filter: GoldListContainsFilter,
) -> bool:
    """Check a single list-contains filter against a record value."""
    value = record.get(contains_filter.column)
    if not value:
        return True
    return matches_contains_mode(
        to_string_set(value),
        contains_filter.values,
        contains_filter.mode,
    )


def is_empty_value(val: object) -> bool:
    """Check whether a value is considered 'empty'."""
    if val is None:
        return True
    if isinstance(val, str) and val.strip() == "":
        return True
    return isinstance(val, (list, dict, set)) and len(val) == 0


def _is_json_list_candidate(value: str) -> bool:
    """Return whether a string looks like a serialized JSON list."""
    return value.startswith("[") and value.endswith("]")


def _decode_json_list_like(val: object) -> object:
    """Decode a JSON-encoded list string when filter inputs arrive serialized."""
    if not isinstance(val, str):
        return val
    stripped = val.strip()
    if not _is_json_list_candidate(stripped):
        return val
    try:
        decoded = json.loads(stripped)
    except json.JSONDecodeError:
        return val
    return decoded if isinstance(decoded, list) else val


def get_list_length(val: object) -> int:
    """Compute the length of a value treated as a list."""
    val = _decode_json_list_like(val)
    if val is None:
        return 0
    if isinstance(val, list):
        return len(val)
    return 1


def length_in_bounds(
    length: int,
    min_len: int | None,
    max_len: int | None,
) -> bool:
    """Check whether the length falls within the allowed bounds."""
    if min_len is not None and length < min_len:
        return False
    return not (max_len is not None and length > max_len)


def to_string_set(val: object) -> set[str]:
    """Convert a value to a set of strings."""
    val = _decode_json_list_like(val)
    if not isinstance(val, list):
        val = [val]
    return {str(item) for item in val}


def matches_contains_mode(
    value_set: set[str],
    allowed: frozenset[str],
    mode: str,
) -> bool:
    """Check whether the value set matches the filter mode."""
    if mode == "all":
        return value_set.issubset(allowed)
    return bool(value_set.intersection(allowed))


def in_range(num_val: float, range_filter: GoldRangeFilter) -> bool:
    """Check whether a numeric value falls within a range."""
    return check_min_bound(
        num_val,
        range_filter.min_value,
        range_filter.include_min,
    ) and check_max_bound(
        num_val,
        range_filter.max_value,
        range_filter.include_max,
    )


def check_min_bound(val: float, min_val: float | None, inclusive: bool) -> bool:
    """Check the lower bound of a range."""
    if min_val is None:
        return True
    return val >= min_val if inclusive else val > min_val


def check_max_bound(val: float, max_val: float | None, inclusive: bool) -> bool:
    """Check the upper bound of a range."""
    if max_val is None:
        return True
    return val <= max_val if inclusive else val < max_val


def _matches_filter_literal(
    value: object, values: frozenset[FilterScalar] | None
) -> bool:
    if values is None:
        return False
    if value in values:
        return True
    return str(value) in {str(candidate) for candidate in values}


def _check_op_in(val: object, values: frozenset[FilterScalar] | None) -> bool:
    """Check the IN operator."""
    return _matches_filter_literal(val, values)


def _check_op_not_in(val: object, values: frozenset[FilterScalar] | None) -> bool:
    """Check the NOT_IN operator."""
    return values is not None and not _matches_filter_literal(val, values)


def _check_op_is_null(val: object, _values: frozenset[FilterScalar] | None) -> bool:
    """Check the IS_NULL operator."""
    return val is None or val == ""


def _check_op_is_not_null(
    val: object,
    _values: frozenset[FilterScalar] | None,
) -> bool:
    """Check the IS_NOT_NULL operator."""
    return val is not None and val != ""


def _check_op_is_empty(val: object, _values: frozenset[FilterScalar] | None) -> bool:
    """Check the IS_EMPTY operator."""
    return is_empty_value(val)


def _check_op_is_not_empty(
    val: object,
    _values: frozenset[FilterScalar] | None,
) -> bool:
    """Check the IS_NOT_EMPTY operator."""
    return not is_empty_value(val)


_OPERATOR_CHECKERS: dict[
    FilterOperator, Callable[[object, frozenset[FilterScalar] | None], bool]
] = {
    FilterOperator.IN: _check_op_in,
    FilterOperator.NOT_IN: _check_op_not_in,
    FilterOperator.IS_NULL: _check_op_is_null,
    FilterOperator.IS_NOT_NULL: _check_op_is_not_null,
    FilterOperator.IS_EMPTY: _check_op_is_empty,
    FilterOperator.IS_NOT_EMPTY: _check_op_is_not_empty,
}
