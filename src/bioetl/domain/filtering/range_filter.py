"""Numeric range filter for Gold layer records.

Provides filtering by numeric column values within a specified range.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GoldRangeFilter",
]


def _require_column(column: str) -> None:
    if not column:
        raise ValueError("column name cannot be empty")


def _require_ordered_float_bounds(
    min_value: float | None, max_value: float | None, column: str
) -> None:
    if min_value is not None and max_value is not None and min_value > max_value:
        raise ValueError(
            f"min_value ({min_value}) cannot exceed max_value "
            f"({max_value}) for column '{column}'"
        )


@dataclass(frozen=True, slots=True)
class GoldRangeFilter:
    """Numeric range filter for a column.

    Attributes:
        column: Column name.
        min_value: Minimum value.
        max_value: Maximum value.
        include_min: Whether to include the minimum (>=). Default: True.
        include_max: Whether to include the maximum (<=). Default: True.
    """

    column: str
    min_value: float | None = None
    max_value: float | None = None
    include_min: bool = True
    include_max: bool = True

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        _require_column(self.column)
        if self.min_value is None and self.max_value is None:
            raise ValueError(
                f"At least one of min_value or max_value must be provided for column '{self.column}'"
            )
        _require_ordered_float_bounds(self.min_value, self.max_value, self.column)
