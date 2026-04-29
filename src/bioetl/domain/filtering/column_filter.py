"""Column value filter for Gold layer records.

Provides filtering by column values using multiple operators:
- IN: value must be in the allowed list
- NOT_IN: value must not be in the excluded list
- IS_NULL: value must be None or empty string
- IS_NOT_NULL: value must not be None or empty string
- IS_EMPTY: value must be "empty" (None, "", [], {})
- IS_NOT_EMPTY: value must not be "empty"
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

__all__ = [
    "FilterOperator",
    "GoldColumnFilter",
]

FilterScalar: TypeAlias = str | int | bool


class FilterOperator(StrEnum):
    """Comparison operators for column filters.

    Attributes:
        IN: Value must be in the allowed list.
        NOT_IN: Value must not be in the excluded list.
        IS_NULL: Value must be None or an empty string.
        IS_NOT_NULL: Value must not be None or an empty string.
        IS_EMPTY: Value must be "empty" (None, "", [], {}).
        IS_NOT_EMPTY: Value must not be "empty".
    """

    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass(frozen=True, slots=True)
class GoldColumnFilter:
    """Column filter with operator support.

    Attributes:
        column: Column name to filter on.
        operator: Filter operator (default: IN).
        values: Set of values (for IN/NOT_IN, None for NULL operators).
    """

    column: str
    operator: FilterOperator = FilterOperator.IN
    values: frozenset[FilterScalar] | None = None

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.column:
            raise ValueError("column name cannot be empty")
        self._validate_operator_values()

    def _validate_operator_values(self) -> None:
        """Validate that values and operator are consistent."""
        requires_values = self.operator in (FilterOperator.IN, FilterOperator.NOT_IN)
        if requires_values and not self.values:
            raise ValueError(
                f"values required for operator '{self.operator.value}' "
                f"on column '{self.column}'"
            )
        if not requires_values and self.values is not None:
            raise ValueError(
                f"values must be None for operator '{self.operator.value}'"
            )
