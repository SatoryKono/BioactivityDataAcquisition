"""Provider Registry - единый реестр провайдеров данных.

Централизует регистрацию провайдеров, устраняя необходимость
изменять несколько файлов при добавлении нового провайдера.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


@dataclass(frozen=True)
class HttpConfig:
    """Конфигурация HTTP клиента для провайдера.

    Attributes:
        rate: Базовый rate limit (requests/second)
        capacity: Ёмкость token bucket
        rate_overrides: Условные переопределения rate limit.
            Ключ — имя атрибута Settings (например, "pubmed_api_key"),
            значение — новый rate при наличии этого атрибута.
    """

    rate: float = 5.0
    capacity: int = 10
    rate_overrides: dict[str, float] = field(default_factory=dict)


# Type alias для creator function
AdapterCreator = Callable[..., "DataSourcePort"]


@dataclass(frozen=True)
class ProviderConfig:
    """Полная конфигурация провайдера.

    Attributes:
        adapter_class: Класс адаптера, реализующий DataSourcePort
        http_config: Конфигурация HTTP клиента (None если провайдер
            управляет своим клиентом самостоятельно)
        requires_http_client: Нужен ли HTTP клиент для инициализации
        requires_logger: Нужен ли логгер для инициализации
        default_kwargs: Дополнительные kwargs для конструктора адаптера
        custom_creator: Кастомная функция создания адаптера для
            сложных случаев (например, PubMed с API key логикой)
    """

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, Any] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None


class ProviderRegistry:
    """Единый реестр провайдеров данных.

    Централизует:
    - Регистрацию адаптеров провайдеров
    - Конфигурацию HTTP клиентов
    - Создание экземпляров адаптеров

    Example:
        >>> from bioetl.composition.providers import ProviderRegistry, register_provider
        >>>
        >>> @register_provider("mydb", http_rate=10.0)
        ... class MyDBAdapter:
        ...     pass
        >>>
        >>> adapter = ProviderRegistry.create_adapter("mydb", http_client=client)
    """

    _providers: ClassVar[dict[str, ProviderConfig]] = {}

    @classmethod
    def register(cls, name: str, config: ProviderConfig) -> None:
        """Регистрирует провайдера.

        При повторной регистрации того же провайдера конфигурация перезаписывается.
        Это позволяет корректно работать при reload модулей.

        Args:
            name: Уникальное имя провайдера (например, "chembl", "pubchem")
            config: Конфигурация провайдера
        """
        cls._providers[name] = config

    @classmethod
    def get(cls, name: str) -> ProviderConfig:
        """Возвращает конфигурацию провайдера.

        Args:
            name: Имя провайдера

        Returns:
            Конфигурация провайдера

        Raises:
            KeyError: Если провайдер не зарегистрирован
        """
        if name not in cls._providers:
            available = ", ".join(sorted(cls._providers.keys()))
            raise KeyError(f"Unknown provider: {name}. Available: {available}")
        return cls._providers[name]

    @classmethod
    def is_registered(cls, name: str) -> bool:
        """Проверяет, зарегистрирован ли провайдер.

        Args:
            name: Имя провайдера

        Returns:
            True если провайдер зарегистрирован
        """
        return name in cls._providers

    @classmethod
    def create_adapter(
        cls,
        name: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Создаёт экземпляр адаптера провайдера.

        Args:
            name: Имя провайдера
            http_client: HTTP клиент (требуется для провайдеров с requires_http_client=True)
            logger: Логгер (требуется для провайдеров с requires_logger=True)
            settings: Настройки приложения (для кастомных creators)
            **kwargs: Дополнительные аргументы для конструктора

        Returns:
            Экземпляр адаптера, реализующий DataSourcePort

        Raises:
            KeyError: Если провайдер не зарегистрирован
            ValueError: Если требуемый http_client или logger не передан
        """
        config = cls.get(name)

        # Use custom creator if available
        if config.custom_creator:
            return config.custom_creator(
                http_client=http_client,
                logger=logger,
                settings=settings,
                **kwargs,
            )

        # Standard creation logic
        init_kwargs: dict[str, Any] = {**config.default_kwargs, **kwargs}

        if config.requires_http_client:
            if http_client is None:
                raise ValueError(
                    f"Provider '{name}' requires http_client but none was provided. "
                    "Ensure http_client is passed from Composition Root."
                )
            init_kwargs["http_client"] = http_client

        if config.requires_logger:
            if logger is None:
                raise ValueError(
                    f"Provider '{name}' requires logger but none was provided. "
                    "Ensure logger is passed from Composition Root."
                )
            init_kwargs["logger"] = logger

        return config.adapter_class(**init_kwargs)

    @classmethod
    def get_http_config(cls, name: str) -> HttpConfig | None:
        """Возвращает HTTP конфигурацию провайдера.

        Args:
            name: Имя провайдера

        Returns:
            HttpConfig или None если провайдер не использует общий HTTP клиент
        """
        config = cls.get(name)
        return config.http_config

    @classmethod
    def list_providers(cls) -> list[str]:
        """Список всех зарегистрированных провайдеров.

        Returns:
            Отсортированный список имён провайдеров
        """
        return sorted(cls._providers.keys())

    @classmethod
    def clear(cls) -> None:
        """Очищает реестр. Используется для тестов."""
        cls._providers.clear()

    @classmethod
    def _reset_for_testing(cls) -> None:
        """Сбрасывает реестр для изолированного тестирования.

        Warning:
            Только для использования в тестах!
        """
        cls.clear()
