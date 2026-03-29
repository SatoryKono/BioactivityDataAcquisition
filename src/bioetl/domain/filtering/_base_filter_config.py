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

__all__ = ["BaseFilterConfig", "FilterDecision"]


@dataclass(frozen=True, slots=True)
class FilterDecision:
    """Structured result of evaluating a record against filter rules."""

    include: bool
    reason_code: str | None = None
    rule_type: str | None = None
    field: str | None = None
    operator: str | None = None
    expected: object | None = None
    actual: object | None = None
    message: str | None = None

    @classmethod
    def allowed(cls) -> FilterDecision:
        """Build an allow decision."""
        return cls(include=True)

    @classmethod
    def rejected(
        cls,
        *,
        reason_code: str,
        rule_type: str,
        field: str,
        message: str,
        operator: str | None = None,
        expected: object | None = None,
        actual: object | None = None,
    ) -> FilterDecision:
        """Build a reject decision."""
        return cls(
            include=False,
            reason_code=reason_code,
            rule_type=rule_type,
            field=field,
            operator=operator,
            expected=expected,
            actual=actual,
            message=message,
        )

    def to_dict(self) -> JsonDict:
        """Convert the decision into JSON-serializable metadata."""
        return {
            "include": self.include,
            "reason_code": self.reason_code,
            "rule_type": self.rule_type,
            "field": self.field,
            "operator": self.operator,
            "expected": self.expected,
            "actual": self.actual,
            "message": self.message,
        }


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
        """Create same-type filter config from another base config.

        Args:
            other: Source BaseFilterConfig whose fields will be copied.

        Returns:
            New instance of the calling class with all filter fields copied from other.
        """
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

        Args:
            record: Dictionary of record fields to evaluate against all configured filters.

        Returns:
            True if the record passes all configured filter rules, False otherwise.
        """
        return self.evaluate(record).include

    def evaluate(self, record: JsonDict) -> FilterDecision:
        """Evaluate all filter rules and return the first blocking decision."""
        evaluators = (
            self._evaluate_required_fields,
            self._evaluate_exclude_if_present,
            self._evaluate_column_filters,
            self._evaluate_range_filters,
            self._evaluate_list_length_filters,
            self._evaluate_list_contains_filters,
        )
        for evaluator in evaluators:
            decision = evaluator(record)
            if not decision.include:
                return decision
        return FilterDecision.allowed()

    def _evaluate_required_fields(self, record: JsonDict) -> FilterDecision:
        """Evaluate required-field rules."""
        for field in self.required_fields:
            actual = record.get(field)
            if actual in (None, ""):
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

    def _evaluate_exclude_if_present(self, record: JsonDict) -> FilterDecision:
        """Evaluate exclusion-by-presence rules."""
        for field in self.exclude_if_present:
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

    def _evaluate_column_filters(self, record: JsonDict) -> FilterDecision:
        """Evaluate configured column filters."""
        for column_filter in self.column_filters:
            if self._check_single_column(record, column_filter):
                continue
            actual = record.get(column_filter.column)
            expected = (
                sorted(column_filter.values) if column_filter.values is not None else None
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

    def _evaluate_range_filters(self, record: JsonDict) -> FilterDecision:
        """Evaluate numeric range filters."""
        for range_filter in self.range_filters:
            if self._check_single_range(record, range_filter):
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

    def _evaluate_list_length_filters(self, record: JsonDict) -> FilterDecision:
        """Evaluate list-length filters."""
        for list_filter in self.list_length_filters:
            if self._check_single_list_length(record, list_filter):
                continue
            actual = self._get_list_length(record.get(list_filter.column))
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

    def _evaluate_list_contains_filters(self, record: JsonDict) -> FilterDecision:
        """Evaluate list-contains filters."""
        for contains_filter in self.list_contains_filters:
            if self._check_single_list_contains(record, contains_filter):
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
    FilterOperator, Callable[[BaseFilterConfig, object, frozenset[str] | None], bool]
] = {
    FilterOperator.IN: BaseFilterConfig._check_op_in,
    FilterOperator.NOT_IN: BaseFilterConfig._check_op_not_in,
    FilterOperator.IS_NULL: BaseFilterConfig._check_op_is_null,
    FilterOperator.IS_NOT_NULL: BaseFilterConfig._check_op_is_not_null,
    FilterOperator.IS_EMPTY: BaseFilterConfig._check_op_is_empty,
    FilterOperator.IS_NOT_EMPTY: BaseFilterConfig._check_op_is_not_empty,
}
