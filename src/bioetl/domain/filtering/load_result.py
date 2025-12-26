"""Filter load result.

Provides the result container for loading filter IDs with deduplication metadata.
"""

from __future__ import annotations

from dataclasses import dataclass


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
