"""Декораторы для регистрации провайдеров.

Предоставляет декларативный API для регистрации адаптеров провайдеров.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from bioetl.composition.providers.provider_registry import (
    AdapterCreator,
    HttpConfig,
    ProviderConfig,
    ProviderRegistry,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort

T = TypeVar("T", bound="DataSourcePort")


def register_provider(
    name: str,
    *,
    http_rate: float = 5.0,
    http_capacity: int = 10,
    requires_http_client: bool = True,
    requires_logger: bool = True,
    rate_overrides: dict[str, float] | None = None,
    custom_creator: AdapterCreator | None = None,
    **default_kwargs: Any,
) -> Callable[[type[T]], type[T]]:
    """Декоратор для регистрации провайдера данных.

    Регистрирует класс адаптера в ProviderRegistry при импорте модуля.

    Args:
        name: Уникальное имя провайдера (например, "chembl", "pubchem")
        http_rate: Rate limit для HTTP клиента (requests/second)
        http_capacity: Ёмкость token bucket
        requires_http_client: Нужен ли HTTP клиент для инициализации
        requires_logger: Нужен ли логгер для инициализации
        rate_overrides: Условные переопределения rate limit.
            Ключ — имя атрибута Settings, значение — новый rate.
        custom_creator: Кастомная функция создания адаптера.
            Если указана, используется вместо стандартной логики.
        **default_kwargs: Дефолтные kwargs для конструктора адаптера

    Returns:
        Декоратор класса

    Example:
        >>> @register_provider(
        ...     "chembl",
        ...     http_rate=10.0,
        ...     http_capacity=20,
        ... )
        ... class ChemblAdapter:
        ...     def __init__(self, http_client, logger=None):
        ...         ...

        >>> # Для провайдеров со сложной логикой инициализации:
        >>> def create_pubmed(http_client, logger, settings, **kwargs):
        ...     api_key = kwargs.get("api_key") or settings.pubmed_api_key
        ...     return PubMedAdapter(http_client, logger, api_key=api_key)
        >>>
        >>> @register_provider(
        ...     "pubmed",
        ...     http_rate=3.0,
        ...     rate_overrides={"pubmed_api_key": 10.0},
        ...     custom_creator=create_pubmed,
        ... )
        ... class PubMedAdapter:
        ...     ...
    """

    def decorator(cls: type[T]) -> type[T]:
        # Создаём HTTP конфигурацию
        http_config: HttpConfig | None = None
        if requires_http_client:
            http_config = HttpConfig(
                rate=http_rate,
                capacity=http_capacity,
                rate_overrides=rate_overrides or {},
            )

        # Создаём конфигурацию провайдера
        config = ProviderConfig(
            adapter_class=cls,
            http_config=http_config,
            requires_http_client=requires_http_client,
            requires_logger=requires_logger,
            default_kwargs=dict(default_kwargs),
            custom_creator=custom_creator,
        )

        # Регистрируем провайдера
        ProviderRegistry.register(name, config)

        # Сохраняем имя провайдера в классе для интроспекции
        cls.__provider_name__ = name  # type: ignore[attr-defined]

        return cls

    return decorator
