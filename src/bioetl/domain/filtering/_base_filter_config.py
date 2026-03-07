"""Shared filter configuration logic for Silver and Gold layers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from bioetl.domain.filtering.column_filter import FilterOperator, GoldColumnFilter
from bioetl.domain.filtering.list_filters import (
    GoldListContainsFilter,
    GoldListLengthFilter,
)
from bioetl.domain.filtering.range_filter import GoldRangeFilter
from bioetl.domain.types import JsonDict

__all__ = ["BaseFilterConfig"]


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
        """Check all filtering rules against a record.

        Returns:
            True if the record passes all configured filter rules, False otherwise.
        """
        checks = [
            self._check_required_fields,
            self._check_exclude_if_present,
            self._check_column_filters,
            self._check_range_filters,
            self._check_list_length_filters,
            self._check_list_contains_filters,
        ]
        return all(check(record) for check in checks)

    def _check_required_fields(
        self,
        record: JsonDict,
    ) -> bool:
        """Check that all required fields are present and non-empty."""
        return all(record.get(fld) not in (None, "") for fld in self.required_fields)

    def _check_exclude_if_present(
        self,
        record: JsonDict,
    ) -> bool:
        """Check that exclusion fields are absent or empty."""
        return all(record.get(fld) in (None, "") for fld in self.exclude_if_present)

    def _check_column_filters(
        self,
        record: JsonDict,
    ) -> bool:
        """Check that column values match the configured filters."""
        return all(self._check_single_column(record, f) for f in self.column_filters)

    def _check_single_column(
        self,
        record: JsonDict,
        f: GoldColumnFilter,
    ) -> bool:
        """Check a single column value against its filter operator."""
        val = record.get(f.column)
        checker = _OPERATOR_CHECKERS.get(f.operator)
        if checker is None:
            return False
        return checker(self, val, f.values)

    def _check_op_in(
        self,
        val: object,
        values: frozenset[str] | None,
    ) -> bool:
        """Check the IN operator."""
        return values is not None and str(val) in values

    def _check_op_not_in(
        self,
        val: object,
        values: frozenset[str] | None,
    ) -> bool:
        """Check the NOT_IN operator."""
        return values is not None and str(val) not in values

    def _check_op_is_null(
        self,
        val: object,
        _values: frozenset[str] | None,
    ) -> bool:
        """Check the IS_NULL operator."""
        return val is None or val == ""

    def _check_op_is_not_null(
        self,
        val: object,
        _values: frozenset[str] | None,
    ) -> bool:
        """Check the IS_NOT_NULL operator."""
        return val is not None and val != ""

    def _check_op_is_empty(
        self,
        val: object,
        _values: frozenset[str] | None,
    ) -> bool:
        """Check the IS_EMPTY operator."""
        return self._is_empty_value(val)

    def _check_op_is_not_empty(
        self,
        val: object,
        _values: frozenset[str] | None,
    ) -> bool:
        """Check the IS_NOT_EMPTY operator."""
        return not self._is_empty_value(val)

    @staticmethod
    def _is_empty_value(val: object) -> bool:
        """Check whether a value is considered 'empty'."""
        if val is None:
            return True
        if isinstance(val, str) and val.strip() == "":
            return True
        return isinstance(val, (list, dict, set)) and len(val) == 0

    def _check_range_filters(
        self,
        record: JsonDict,
    ) -> bool:
        """Check that values fall within the configured ranges."""
        return all(self._check_single_range(record, f) for f in self.range_filters)

    def _check_list_length_filters(
        self,
        record: JsonDict,
    ) -> bool:
        """Check list lengths in columns against configured bounds."""
        return all(
            self._check_single_list_length(record, f) for f in self.list_length_filters
        )

    def _check_single_list_length(
        self,
        record: JsonDict,
        f: GoldListLengthFilter,
    ) -> bool:
        """Check the length of a single list column."""
        length = self._get_list_length(record.get(f.column))
        return self._length_in_bounds(length, f.min_length, f.max_length)

    @staticmethod
    def _get_list_length(val: object) -> int:
        """Compute the length of a value treated as a list."""
        if val is None:
            return 0
        if isinstance(val, list):
            return len(val)
        return 1

    @staticmethod
    def _length_in_bounds(
        length: int, min_len: int | None, max_len: int | None
    ) -> bool:
        """Check whether the length falls within the allowed bounds."""
        if min_len is not None and length < min_len:
            return False
        return not (max_len is not None and length > max_len)

    def _check_list_contains_filters(
        self,
        record: JsonDict,
    ) -> bool:
        """Check list-contains filters against record values."""
        return all(
            self._check_single_list_contains(record, f)
            for f in self.list_contains_filters
        )

    def _check_single_list_contains(
        self,
        record: JsonDict,
        f: GoldListContainsFilter,
    ) -> bool:
        """Check a single list-contains filter against a record value."""
        val = record.get(f.column)
        if not val:
            return True

        val_set = self._to_string_set(val)
        return self._matches_contains_mode(val_set, f.values, f.mode)

    @staticmethod
    def _to_string_set(val: object) -> set[str]:
        """Convert a value to a set of strings."""
        if not isinstance(val, list):
            val = [val]
        return {str(v) for v in val}

    @staticmethod
    def _matches_contains_mode(
        val_set: set[str], allowed: frozenset[str], mode: str
    ) -> bool:
        """Check whether the value set matches the filter mode."""
        if mode == "all":
            return val_set.issubset(allowed)
        return bool(val_set.intersection(allowed))

    def _check_single_range(
        self,
        record: JsonDict,
        f: GoldRangeFilter,
    ) -> bool:
        """Check a single value against a range filter."""
        val = record.get(f.column)
        if val is None or val == "":
            return False

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            return False

        return self._in_range(num_val, f)

    def _in_range(self, num_val: float, f: GoldRangeFilter) -> bool:
        """Check whether a numeric value falls within a range."""
        min_ok = self._check_min_bound(num_val, f.min_value, f.include_min)
        max_ok = self._check_max_bound(num_val, f.max_value, f.include_max)
        return min_ok and max_ok

    @staticmethod
    def _check_min_bound(val: float, min_val: float | None, inclusive: bool) -> bool:
        """Check the lower bound of a range."""
        if min_val is None:
            return True
        return val >= min_val if inclusive else val > min_val

    @staticmethod
    def _check_max_bound(val: float, max_val: float | None, inclusive: bool) -> bool:
        """Check the upper bound of a range."""
        if max_val is None:
            return True
        return val <= max_val if inclusive else val < max_val

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


_OPERATOR_CHECKERS: dict[
    FilterOperator,
    Callable[
        [
            BaseFilterConfig,
            object,
            frozenset[str] | None,
        ],
        bool,
    ],
] = {
    FilterOperator.IN: BaseFilterConfig._check_op_in,
    FilterOperator.NOT_IN: BaseFilterConfig._check_op_not_in,
    FilterOperator.IS_NULL: BaseFilterConfig._check_op_is_null,
    FilterOperator.IS_NOT_NULL: BaseFilterConfig._check_op_is_not_null,
    FilterOperator.IS_EMPTY: BaseFilterConfig._check_op_is_empty,
    FilterOperator.IS_NOT_EMPTY: BaseFilterConfig._check_op_is_not_empty,
}
