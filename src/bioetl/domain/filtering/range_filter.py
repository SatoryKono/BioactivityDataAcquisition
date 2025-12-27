"""Numeric range filter for Gold layer records.

Provides filtering by numeric column values within a specified range.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldRangeFilter:
    """Фильтр числового диапазона для колонки.

    Attributes:
        column: Имя колонки.
        min_value: Минимальное значение.
        max_value: Максимальное значение.
        include_min: Включать ли минимум (>=). Default: True.
        include_max: Включать ли максимум (<=). Default: True.
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
