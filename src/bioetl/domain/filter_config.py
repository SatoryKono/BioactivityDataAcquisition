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


@dataclass(frozen=True)
class GoldFilterConfig:
    """Полная конфигурация Gold фильтров.

    Attributes:
        column_filters: Фильтры по колонкам (значение должно быть в списке).
        range_filters: Фильтры диапазонов значений.
        required_fields: Обязательные поля (должны быть не null/пустые).
        exclude_if_present: Исключающие поля (если есть значение — запись исключается).
    """

    column_filters: tuple[GoldColumnFilter, ...] = ()
    range_filters: tuple[GoldRangeFilter, ...] = ()
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
            and self._check_range_filters(record)
        )

    def _check_required_fields(self, record: dict[str, Any]) -> bool:
        """Проверяет наличие обязательных полей."""
        return all(record.get(fld) not in (None, "") for fld in self.required_fields)

    def _check_exclude_if_present(self, record: dict[str, Any]) -> bool:
        """Проверяет отсутствие исключающих полей."""
        return all(record.get(fld) in (None, "") for fld in self.exclude_if_present)

    def _check_column_filters(self, record: dict[str, Any]) -> bool:
        """Проверяет соответствие значений колонок допустимым."""
        return all(str(record.get(f.column)) in f.values for f in self.column_filters)

    def _check_range_filters(self, record: dict[str, Any]) -> bool:
        """Проверяет попадание значений в диапазоны."""
        return all(self._check_single_range(record, f) for f in self.range_filters)

    def _check_single_range(self, record: dict[str, Any], f: GoldRangeFilter) -> bool:
        """Проверяет одно значение на попадание в диапазон."""
        val = record.get(f.column)
        if val is None or val == "":
            return False

        try:
            num_val = float(val)
        except (ValueError, TypeError):
            return False

        return self._in_range(num_val, f)

    def _in_range(self, num_val: float, f: GoldRangeFilter) -> bool:
        """Проверяет, находится ли значение в диапазоне."""
        min_ok = self._check_min_bound(num_val, f.min_value, f.include_min)
        max_ok = self._check_max_bound(num_val, f.max_value, f.include_max)
        return min_ok and max_ok

    @staticmethod
    def _check_min_bound(val: float, min_val: float | None, inclusive: bool) -> bool:
        """Проверяет нижнюю границу диапазона."""
        if min_val is None:
            return True
        return val >= min_val if inclusive else val > min_val

    @staticmethod
    def _check_max_bound(val: float, max_val: float | None, inclusive: bool) -> bool:
        """Проверяет верхнюю границу диапазона."""
        if max_val is None:
            return True
        return val <= max_val if inclusive else val < max_val

    def is_empty(self) -> bool:
        """Проверяет, пуста ли конфигурация фильтров.

        Returns:
            True если нет ни одного фильтра.
        """
        return (
            not self.column_filters
            and not self.range_filters
            and not self.required_fields
            and not self.exclude_if_present
        )


@dataclass(frozen=True)
class FilterLoadResult:
    """Результат загрузки фильтра ID с метаданными о дубликатах.

    Attributes:
        ids: Уникальные отсортированные ID.
        total_count: Всего записей в источнике (до дедупликации).
        unique_count: Количество уникальных ID.
        duplicate_count: Количество удалённых дубликатов.
        duplicates: ID, которые встречались более одного раза.
    """

    ids: tuple[str, ...]
    total_count: int
    unique_count: int
    duplicate_count: int
    duplicates: frozenset[str]

    def __post_init__(self) -> None:
        """Validate result consistency."""
        if self.unique_count != len(self.ids):
            raise ValueError(
                f"unique_count ({self.unique_count}) must match len(ids) ({len(self.ids)})"
            )
        if self.duplicate_count != self.total_count - self.unique_count:
            raise ValueError(
                f"duplicate_count ({self.duplicate_count}) must equal "
                f"total_count - unique_count ({self.total_count - self.unique_count})"
            )

    @property
    def has_duplicates(self) -> bool:
        """Проверяет, были ли найдены дубликаты."""
        return self.duplicate_count > 0


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
