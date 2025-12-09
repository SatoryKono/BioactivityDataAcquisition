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
    def build_with_pagination(self, offset: int, limit: int) -> "RequestBuilderABC":
        """Добавляет параметры пагинации."""


class ResponseParserABC(ABC, Generic[RecordT]):
    """
    Разбор ответов API.
    """

    @abstractmethod
    def parse_response(self, raw_response: dict[str, object]) -> list[RecordT]:
        """Парсит сырой ответ в список типизированных записей."""

    @abstractmethod
    def extract_metadata(self, raw_response: dict[str, object]) -> dict[str, int | str | None]:
        """Извлекает метаданные из ответа (например, общее кол-во)."""


class ApiClientABC(ABC):
    """
    Абстракция API-клиента, не зависящая от транспорта.
    Поддерживает хуки жизненного цикла запросов.

    Default factory:
    ``bioetl.infrastructure.clients.base.factories.default_api_client``.

    Common implementation:
    ``bioetl.infrastructure.clients.base.impl.unified_api_client_impl.UnifiedAPIClientImpl``.
    """

    @abstractmethod
    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        """Execute an HTTP-style request and return the raw response object."""

    @abstractmethod
    def close(self) -> None:
        """Release underlying resources (sessions, pools)."""


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
    def get_backoff(self, attempt: int) -> float:
        """Возвращает задержку перед следующей попыткой (в секундах)."""


class CacheABC(ABC, Generic[T]):
    """
    Интерфейс кэширования.
    """

    def get(self, key: str) -> T | None:
        """
        Возвращает значение из кэша или ``None``.
        Делегирует в ``get_value``.
        """

        return self.get_value(key)

    @abstractmethod
    def get_value(self, key: str) -> T | None:
        """Получает значение из кэша или ``None``, если его нет или оно истекло."""

    def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """
        Сохраняет значение в кэш с опциональным TTL.
        Делегирует в ``apply_set``.
        """

        self.apply_set(key, value, ttl)

    @abstractmethod
    def apply_set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Сохраняет значение в кэш с опциональным TTL в секундах."""

    def invalidate(self, key: str) -> None:
        """
        Удаляет значение из кэша.
        Делегирует в ``apply_invalidate``.
        """

        self.apply_invalidate(key)

    @abstractmethod
    def apply_invalidate(self, key: str) -> None:
        """Удаляет значение из кэша."""

    def clear(self) -> None:
        """
        Полностью очищает кэш.
        Делегирует в ``apply_clear``.
        """

        self.apply_clear()

    @abstractmethod
    def apply_clear(self) -> None:
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
