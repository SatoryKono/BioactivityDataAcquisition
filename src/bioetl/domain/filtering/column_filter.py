"""Column value filter for Gold layer records.

Provides filtering by column values using an inclusion list.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldColumnFilter:
    """Фильтр по колонке со списком допустимых значений.

    Attributes:
        column: Имя колонки для фильтрации.
        values: Множество допустимых значений (оператор "in").
    """

    column: str
    values: frozenset[str]

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.column:
            raise ValueError("column name cannot be empty")
        if not self.values:
            raise ValueError(f"values for column '{self.column}' cannot be empty")
