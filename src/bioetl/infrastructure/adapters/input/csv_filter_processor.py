"""CSV Filter Processor.

Обработчик данных для CSV-фильтров. Содержит логику трансформации
Polars DataFrame в результаты фильтрации.
"""

from __future__ import annotations

__all__ = ["CsvFilterProcessor"]

from collections import Counter
from typing import TYPE_CHECKING

import polars as pl

from bioetl.domain.filtering import FilterColumn
from bioetl.domain.transformations import safe_str

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort


class CsvFilterProcessor:
    """Процессор для обработки данных фильтров из CSV."""

    def __init__(self, logger: LoggerPort | None = None) -> None:
        """Инициализация процессора.

        Args:
            logger: Порт для логирования.
        """
        self._logger = logger

    def extract_column_ids(self, df: pl.DataFrame, column_name: str) -> list[str]:
        """Извлекает и очищает ID из указанной колонки.

        Returns:
            Список непустых очищенных строковых значений.
        """
        if column_name not in df.columns:
            available = ", ".join(df.columns)
            raise ValueError(
                f"Column '{column_name}' not found in CSV. Available columns: {available}"
            )

        # Безопасное извлечение значений и конвертация в строку (обработка float ID)
        raw_values = df.select(pl.col(column_name)).to_series().to_list()
        result = [
            s
            for v in raw_values
            if (s_val := safe_str(v, "")) is not None and (s := s_val.strip()) != ""
        ]
        return result

    def compute_duplicate_stats(
        self, all_ids: list[str]
    ) -> tuple[tuple[str, ...], int, int, frozenset[str]]:
        """Вычисляет уникальные ID и статистику дубликатов.

        Returns:
            Кортеж (уникальные ID, общее кол-во, кол-во дублей, множество дублей).
        """
        total_count = len(all_ids)
        id_counts = Counter(all_ids)
        duplicates = frozenset(
            id_val for id_val, count in id_counts.items() if count > 1
        )
        unique_ids = tuple(sorted(set(all_ids)))
        unique_count = len(unique_ids)
        duplicate_count = total_count - unique_count
        return unique_ids, unique_count, duplicate_count, duplicates

    def extract_column_ids_map(
        self, df: pl.DataFrame, columns: list[FilterColumn]
    ) -> dict[str, tuple[str, ...]]:
        """Извлекает карту уникальных ID по колонкам.

        Returns:
            Словарь соответствия имени поля фильтра и кортежа уникальных ID.
        """
        return {
            col.filter_field: tuple(
                sorted(set(self.extract_column_ids(df, col.column_name)))
            )
            for col in columns
        }

    def build_valid_combinations(
        self, df: pl.DataFrame, column_names: list[str]
    ) -> set[tuple[str, ...]]:
        """Создает набор валидных построчных комбинаций значений.

        Returns:
            Множество кортежей значений строк, где все колонки непусты.
        """
        combinations: set[tuple[str, ...]] = set()
        for row in df.select(column_names).iter_rows():
            combo = tuple(
                s_val.strip() if (s_val := safe_str(val, "")) is not None else ""
                for val in row
            )
            if all(combo):  # Пропуск строк с пустыми значениями
                combinations.add(combo)
        return combinations

    def build_fallback_rows(
        self,
        df: pl.DataFrame,
        primary_column: str,
        fallback_column: str,
        all_ids: list[str],
        fallback_mapping: dict[str, str],
    ) -> int:
        """Обрабатывает строки для построения списка ID и карты fallback.

        Returns:
            Количество записей только с заголовком (без основного ID).
        """
        title_only_count = 0
        for row in df.iter_rows(named=True):
            primary_str = (
                str(row.get(primary_column, "")).strip()
                if row.get(primary_column)
                else ""
            )
            fallback_str = (
                str(row.get(fallback_column, "")).strip()
                if row.get(fallback_column)
                else ""
            )

            if primary_str:
                all_ids.append(primary_str)
                if fallback_str:
                    fallback_mapping[primary_str] = fallback_str
            elif fallback_str:
                marker = f"__title_only_{title_only_count}__"
                all_ids.append(marker)
                fallback_mapping[marker] = fallback_str
                title_only_count += 1
        return title_only_count
