"""Numeric range filter for Gold layer records.

Provides filtering by numeric column values within a specified range.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "GoldRangeFilter",
]


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
        if not self.column:
            raise ValueError("column name cannot be empty")
        if self.min_value is None and self.max_value is None:
            raise ValueError(
                f"At least one of min_value or max_value must be provided for column '{self.column}'"
            )
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError(
                f"min_value ({self.min_value}) cannot exceed max_value "
                f"({self.max_value}) for column '{self.column}'"
            )
