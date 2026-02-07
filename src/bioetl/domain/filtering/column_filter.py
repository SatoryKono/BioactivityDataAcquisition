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


class FilterOperator(StrEnum):
    """Операторы сравнения для column filters.

    Attributes:
        IN: Значение должно быть в списке допустимых.
        NOT_IN: Значение не должно быть в списке исключаемых.
        IS_NULL: Значение должно быть None или пустой строкой.
        IS_NOT_NULL: Значение не должно быть None или пустой строкой.
        IS_EMPTY: Значение должно быть "пустым" (None, "", [], {}).
        IS_NOT_EMPTY: Значение не должно быть "пустым".
    """

    IN = "in"
    NOT_IN = "not_in"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


@dataclass(frozen=True, slots=True)
class GoldColumnFilter:
    """Фильтр по колонке с поддержкой операторов.

    Attributes:
        column: Имя колонки для фильтрации.
        operator: Оператор фильтрации (default: IN).
        values: Множество значений (для IN/NOT_IN, None для NULL-операторов).
    """

    column: str
    operator: FilterOperator = FilterOperator.IN
    values: frozenset[str] | None = None

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.column:
            raise ValueError("column name cannot be empty")
        self._validate_operator_values()

    def _validate_operator_values(self) -> None:
        """Валидирует соответствие values и operator."""
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
