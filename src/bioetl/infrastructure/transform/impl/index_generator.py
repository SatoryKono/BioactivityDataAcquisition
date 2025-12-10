"""Infrastructure implementation of IndexGenerator."""

from __future__ import annotations

from bioetl.domain.transform.contracts import IndexGeneratorABC


class SequentialIndexGenerator(IndexGeneratorABC):
    """
    Генератор последовательных индексов.

    Stateful: сохраняет текущее значение счётчика между вызовами.
    Используется для присвоения уникальных индексов строкам данных.
    """

    def __init__(self, start: int = 0) -> None:
        """
        Args:
            start: Начальное значение счётчика (по умолчанию 0).
        """
        self._start = start
        self._counter = start

    def next_index(self) -> int:
        """Возвращает следующий индекс и увеличивает счётчик."""
        idx = self._counter
        self._counter += 1
        return idx

    def reset(self) -> None:
        """Сбрасывает счётчик в начальное состояние."""
        self._counter = self._start

    def generate_range(self, count: int) -> list[int]:
        """
        Генерирует диапазон индексов для batch операций.

        Args:
            count: Количество индексов для генерации.

        Returns:
            Список последовательных индексов.
        """
        start = self._counter
        self._counter += count
        return list(range(start, start + count))


__all__ = ["SequentialIndexGenerator"]
