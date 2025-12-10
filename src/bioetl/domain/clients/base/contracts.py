"""Base contracts for data source helpers."""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")
RecordT = TypeVar("RecordT", bound=BaseModel)
RecordModel = BaseModel


class RequestBuilderABC(ABC):
    """
    Паттерн Builder для создания запросов.
    """

    @abstractmethod
    def build_request(self, params: dict[str, Any]) -> Any:
        """Создает объект запроса из параметров."""

    @abstractmethod
    def build(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        """Создает запрос для указанного endpoint с параметрами."""

    @abstractmethod
    def build_with_pagination(self, offset: int, limit: int) -> "RequestBuilderABC":
        """Добавляет параметры пагинации."""

    def with_pagination(self, offset: int, limit: int) -> "RequestBuilderABC":
        """Alias for build_with_pagination."""
        return self.build_with_pagination(offset, limit)


class ResponseParserABC(ABC, Generic[RecordT]):
    """
    Разбор ответов API.
    """

    def parse(self, raw_response: dict[str, object]) -> list[RecordT]:
        """Alias for parse_response."""
        return self.parse_response(raw_response)

    @abstractmethod
    def parse_response(self, raw_response: dict[str, object]) -> list[RecordT]:
        """Парсит сырой ответ в список типизированных записей."""

    @abstractmethod
    def extract_metadata(
        self, raw_response: dict[str, object]
    ) -> dict[str, int | str | None]:
        """Извлекает метаданные из ответа (например, общее кол-во)."""


class PaginatorABC(ABC):
    """
    Стратегия пагинации.
    """

    @abstractmethod
    def get_items(self, response: Any) -> list[RecordModel]:
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
    def get_backoff(self, attempt: int) -> float:
        """Возвращает задержку перед следующей попыткой (в секундах)."""


class CacheABC(ABC, Generic[T]):
    """
    Интерфейс кэширования.
    """

    @abstractmethod
    def get(self, key: str) -> T | None:
        """Возвращает значение из кэша или ``None``."""

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


class ApiClientABC(ABC):
    """
    Низкоуровневый HTTP‑клиент.

    Обеспечивает базовый интерфейс для выполнения запросов и закрытия
    соединений. Реализации должны обеспечивать таймауты, ретраи и
    корректную обработку ошибок.
    """

    @abstractmethod
    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Выполняет HTTP‑запрос и возвращает объект ответа."""

    @abstractmethod
    def close(self) -> None:
        """Закрывает клиент/сессию."""
