"""List-based filters for Gold layer records.

Provides filtering by list length and list content.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GoldListLengthFilter:
    """Фильтр по длине списка в колонке.

    Attributes:
        column: Имя колонки (должна содержать список).
        min_length: Минимальная длина.
        max_length: Максимальная длина.
    """

    column: str
    min_length: int | None = None
    max_length: int | None = None

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.column:
            raise ValueError("column name cannot be empty")
        if self.min_length is None and self.max_length is None:
            raise ValueError(
                f"At least one of min_length or max_length must be provided for column '{self.column}'"
            )


@dataclass(frozen=True, slots=True)
class GoldListContainsFilter:
    """Фильтр на содержание значений в списке (subset).

    Attributes:
        column: Имя колонки (список).
        values: Допустимые значения.
        mode: 'all' (все элементы списка должны быть в values) или 'any' (хотя бы один).
    """

    column: str
    values: frozenset[str]
    mode: str = "all"  # "all" or "any"

    def __post_init__(self) -> None:
        if not self.column:
            raise ValueError("column name cannot be empty")
        if not self.values:
            raise ValueError(f"values for column '{self.column}' cannot be empty")
        if self.mode not in ("all", "any"):
            raise ValueError("mode must be 'all' or 'any'")
