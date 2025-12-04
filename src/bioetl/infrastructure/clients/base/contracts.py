from abc import ABC, abstractmethod
from typing import Any, Generic, Iterator, TypeVar

T = TypeVar("T")
Record = dict[str, Any]


class SourceClientABC(ABC):
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


class RequestBuilderABC(ABC):
    """
    Паттерн Builder для создания запросов.
    """

    @abstractmethod
    def build(self, params: dict[str, Any]) -> Any:
        """Создает объект запроса из параметров."""

    @abstractmethod
    def with_pagination(self, offset: int, limit: int) -> "RequestBuilderABC":
        """Добавляет параметры пагинации."""


class ResponseParserABC(ABC):
    """
    Разбор ответов API.
    """

    @abstractmethod
    def parse(self, raw_response: Any) -> list[Record]:
        """Парсит сырой ответ в список записей."""

    @abstractmethod
    def extract_metadata(self, raw_response: Any) -> dict[str, Any]:
        """Извлекает метаданные из ответа (например, общее кол-во)."""


class PaginatorABC(ABC):
    """
    Стратегия пагинации.
    """

    @abstractmethod
    def get_items(self, response: Any) -> list[Record]:
        """Извлекает элементы из ответа."""

    @abstractmethod
    def get_next_marker(self, response: Any) -> str | int | None:
        """Возвращает маркер следующей страницы (offset, cursor, url)."""

    @abstractmethod
    def has_more(self, response: Any) -> bool:
        """Проверяет, есть ли еще страницы."""


class RateLimiterABC(ABC):
    """
    Ограничение частоты запросов.
    """

    @abstractmethod
    def acquire(self) -> None:
        """Запрашивает разрешение на выполнение (блокирует при необходимости)."""

    @abstractmethod
    def wait_if_needed(self) -> None:
        """Ожидает, если лимит исчерпан."""


class RetryPolicyABC(ABC):
    """
    Политика повторных попыток.
    """

    @property
    @abstractmethod
    def max_attempts(self) -> int:
        """Максимальное количество попыток."""

    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Определяет, нужно ли повторять попытку."""

    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        """Возвращает задержку перед следующей попыткой (в секундах)."""


class CacheABC(ABC, Generic[T]):
    """
    Интерфейс кэширования.
    """

    @abstractmethod
    def get(self, key: str) -> T | None:
        """Получает значение из кэша или ``None``, если его нет или оно истекло."""

    @abstractmethod
    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Сохраняет значение в кэш с опциональным TTL в секундах."""

    @abstractmethod
    def invalidate(self, key: str) -> None:
        """Удаляет значение из кэша."""
    
    @abstractmethod
    def clear(self) -> None:
        """Очищает весь кэш."""


class SecretProviderABC(ABC):
    """
    Поставщик секретов (env, vault).
    """

    @abstractmethod
    def get_secret(self, name: str) -> str | None:
        """Возвращает значение секрета."""


class SideInputProviderABC(ABC):
    """
    Провайдер побочных данных (справочников).
    """

    @abstractmethod
    def get_side_input(self, name: str) -> Any:
        """Возвращает справочник (обычно DataFrame)."""

    @abstractmethod
    def refresh(self, name: str) -> None:
        """Обновляет справочник."""

