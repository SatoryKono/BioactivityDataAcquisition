"""Provider Registry - единый реестр провайдеров данных.

Централизует регистрацию провайдеров, устраняя необходимость
изменять несколько файлов при добавлении нового провайдера.

После унификации с DataSourceRegistry, этот модуль также отвечает за
высокоуровневое создание data sources с поддержкой фильтрации.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar, Protocol

if TYPE_CHECKING:
    from bioetl.domain.filter_config import InputFilterConfig
    from bioetl.domain.ports import DataSourcePort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


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


# Type alias для low-level adapter creator
AdapterCreator = Callable[..., "DataSourcePort"]


class DataSourceCreator(Protocol):
    """Protocol for high-level data source creator functions.

    These functions create fully configured data sources with filtering support.
    """

    def __call__(
        self,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Create a configured data source.

        Args:
            settings: Application settings
            pipeline_config: Pipeline configuration from YAML
            logger: LoggerPort instance for structured logging
            filter_config: Optional filter configuration
            metrics: Optional metrics port for recording filter statistics
            pipeline_name: Pipeline name for metrics labels

        Returns:
            Configured DataSourcePort instance
        """
        ...


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
        data_source_creator: Высокоуровневая функция создания data source
            с поддержкой фильтрации. Если указана, используется вместо
            стандартной логики в create_data_source().
    """

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, Any] = field(default_factory=dict)
    custom_creator: AdapterCreator | None = None
    data_source_creator: DataSourceCreator | None = None


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
    def create_data_source(
        cls,
        name: str,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
        logger: LoggerPort,
        filter_config: InputFilterConfig | None = None,
        metrics: MetricsPort | None = None,
        pipeline_name: str = "unknown",
    ) -> DataSourcePort:
        """Создаёт полностью настроенный data source с поддержкой фильтрации.

        Высокоуровневый метод, объединяющий функциональность ProviderRegistry
        и бывшего DataSourceRegistry. Использует data_source_creator из
        конфигурации провайдера, если он указан.

        Args:
            name: Имя провайдера
            settings: Настройки приложения
            pipeline_config: Конфигурация пайплайна из YAML
            logger: LoggerPort для структурированного логирования
            filter_config: Опциональная конфигурация фильтрации
            metrics: Опциональный MetricsPort для статистики
            pipeline_name: Имя пайплайна для меток метрик

        Returns:
            Настроенный DataSourcePort с поддержкой фильтрации

        Raises:
            KeyError: Если провайдер не зарегистрирован
            ValueError: Если data_source_creator не задан для провайдера
        """
        config = cls.get(name)

        if config.data_source_creator is None:
            raise ValueError(
                f"Provider '{name}' does not have a data_source_creator configured. "
                "Register the provider with a data_source_creator in registration.py."
            )

        return config.data_source_creator(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name=pipeline_name,
        )

    @classmethod
    def has_data_source_creator(cls, name: str) -> bool:
        """Проверяет, есть ли у провайдера data_source_creator.

        Args:
            name: Имя провайдера

        Returns:
            True если провайдер имеет data_source_creator
        """
        if not cls.is_registered(name):
            return False
        config = cls.get(name)
        return config.data_source_creator is not None

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
