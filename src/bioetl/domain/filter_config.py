"""Filter configuration for pipeline filtering.

Defines the configuration for:
- Input filtering: API requests based on input IDs from external sources (CSV files)
- Gold filtering: Configurable column-based filters for Gold layer records
"""

from dataclasses import dataclass
from typing import Any


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


@dataclass(frozen=True)
class GoldFilterConfig:
    """Полная конфигурация Gold фильтров.

    Attributes:
        column_filters: Фильтры по колонкам (значение должно быть в списке).
        required_fields: Обязательные поля (должны быть не null/пустые).
        exclude_if_present: Исключающие поля (если есть значение — запись исключается).
    """

    column_filters: tuple[GoldColumnFilter, ...] = ()
    required_fields: tuple[str, ...] = ()
    exclude_if_present: tuple[str, ...] = ()

    def should_include(self, record: dict[str, Any]) -> bool:
        """Проверяет все правила фильтрации.

        Args:
            record: Запись для проверки.

        Returns:
            True если запись проходит все фильтры, False иначе.
        """
        return (
            self._check_required_fields(record)
            and self._check_exclude_if_present(record)
            and self._check_column_filters(record)
        )

    def _check_required_fields(self, record: dict[str, Any]) -> bool:
        """Проверяет наличие обязательных полей."""
        return all(
            record.get(fld) not in (None, "")
            for fld in self.required_fields
        )

    def _check_exclude_if_present(self, record: dict[str, Any]) -> bool:
        """Проверяет отсутствие исключающих полей."""
        return all(
            record.get(fld) in (None, "")
            for fld in self.exclude_if_present
        )

    def _check_column_filters(self, record: dict[str, Any]) -> bool:
        """Проверяет соответствие значений колонок допустимым."""
        return all(
            str(record.get(f.column)) in f.values
            for f in self.column_filters
        )

    def is_empty(self) -> bool:
        """Проверяет, пуста ли конфигурация фильтров.

        Returns:
            True если нет ни одного фильтра.
        """
        return (
            not self.column_filters
            and not self.required_fields
            and not self.exclude_if_present
        )


@dataclass(frozen=True)
class InputFilterConfig:
    """Configuration for input-based filtering.

    When enabled, the pipeline will only fetch records matching
    the IDs provided in the source file.

    Attributes:
        enabled: Whether filtering is active.
        source_path: Path to the filter source (e.g., CSV file).
        column_name: Name of the column containing filter IDs.
        filter_field: API field to filter by (e.g., molecule_chembl_id).
        batch_size: Number of IDs per API request (ChEMBL limit ~100).
    """

    enabled: bool = False
    source_path: str | None = None
    column_name: str | None = None
    filter_field: str | None = None
    batch_size: int = 100

    def __post_init__(self) -> None:
        """Validate configuration consistency."""
        self._validate_enabled_fields()
        self._validate_batch_size()

    def _validate_enabled_fields(self) -> None:
        """Validate fields required when filtering is enabled."""
        if not self.enabled:
            return
        if not self.source_path:
            raise ValueError("source_path is required when filter is enabled")
        if not self.column_name:
            raise ValueError("column_name is required when filter is enabled")
        if not self.filter_field:
            raise ValueError("filter_field is required when filter is enabled")

    def _validate_batch_size(self) -> None:
        """Validate the batch_size is within a reasonable range."""
        if not (1 <= self.batch_size <= 1000):
            raise ValueError("batch_size must be between 1 and 1000")
