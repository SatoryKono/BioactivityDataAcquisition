"""
Domain contracts for data clients.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterator

Record = dict[str, Any]


class DataClientABC(ABC):
    """
    Основной контракт клиента источника данных.
    Определяет методы для извлечения данных и метаданных.
    """

    @abstractmethod
    def fetch_one(self, id: str) -> Record:
        """Получить одну запись по ID."""

    @abstractmethod
    def fetch_many(self, ids: list[str]) -> list[Record]:
        """Получить несколько записей по списку ID."""

    @abstractmethod
    def iter_pages(self, request: Any) -> Iterator[Any]:
        """
        Итератор по страницам результатов.
        request: Объект запроса (зависит от реализации).
        """

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Метаданные источника (версия, release)."""

    @abstractmethod
    def close(self) -> None:
        """Освободить ресурсы (сессии, соединения)."""
