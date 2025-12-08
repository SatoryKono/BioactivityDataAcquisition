"""
Domain contracts for data clients.
"""

from abc import ABC, abstractmethod
from typing import Any, Iterator

Record = dict[str, Any]


class DataClientABC(ABC):
    """
    Универсальный контракт клиента источника данных.

    Поддерживает извлечение произвольных сущностей через единый метод
    ``fetch`` с фильтрами, а также побочные операции (пагинация, метаданные,
    освобождение ресурсов).
    """

    @abstractmethod
    def fetch(self, entity: str, **filters: Any) -> Any:
        """
        Выполнить запрос к источнику данных для указанной сущности.

        Args:
            entity: Имя сущности/эндпоинта (provider-specific).
            **filters: Фильтры или параметры запроса.
        """

    @abstractmethod
    def iter_pages(self, request: Any) -> Iterator[Any]:
        """
        Итератор по страницам результатов для заранее построенного запроса.

        request: Объект запроса (зависит от реализации).
        """

    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Метаданные источника (версия, release)."""

    @abstractmethod
    def close(self) -> None:
        """Освободить ресурсы (сессии, соединения)."""
