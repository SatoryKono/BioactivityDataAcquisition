"""Domain abstractions for provider registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable

from bioetl.domain.providers import ProviderDefinition, ProviderId


class ProviderRegistryError(Exception):
    """Базовая ошибка реестра провайдеров."""


class ProviderNotRegisteredError(ProviderRegistryError):
    """Провайдер не зарегистрирован."""

    def __init__(self, provider_id: ProviderId) -> None:
        super().__init__(f"Provider '{provider_id.value}' is not registered")
        self.provider_id = provider_id


class ProviderAlreadyRegisteredError(ProviderRegistryError):
    """Провайдер уже зарегистрирован."""

    def __init__(self, provider_id: ProviderId) -> None:
        super().__init__(f"Provider '{provider_id.value}' is already registered")
        self.provider_id = provider_id


class ProviderRegistryABC(ABC):
    """Абстрактный базовый класс для реестра провайдеров."""

    @abstractmethod
    def register_provider(self, definition: ProviderDefinition) -> None:
        """Регистрирует провайдер в реестре."""

    @abstractmethod
    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Получает определение провайдера по идентификатору."""

    @abstractmethod
    def list_providers(self) -> list[ProviderDefinition]:
        """Возвращает список всех зарегистрированных провайдеров."""

    @abstractmethod
    def reset_provider_registry(self) -> None:
        """Очищает реестр провайдеров."""

    @abstractmethod
    def restore_provider_registry(self, definitions: list[ProviderDefinition]) -> None:
        """Восстанавливает реестр из списка определений."""


@runtime_checkable
class ProviderRegistryLoaderABC(Protocol):
    """Протокол для загрузчика реестра провайдеров."""

    def get_providers(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> list[ProviderDefinition]:
        """Загружает провайдеры из конфигурации и регистрирует их."""

    def get_registry(
        self, *, registry: ProviderRegistryABC | None = None
    ) -> ProviderRegistryABC:
        """Загружает провайдеры и возвращает заполненный реестр."""


def get_provider_registry() -> ProviderRegistryABC:
    """Factory для получения registry.

    Возвращает реализацию ProviderRegistryABC из infrastructure слоя.
    Конфигурируется через DI контейнер.
    """
    from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

    return InMemoryProviderRegistry()


# Backward compatibility alias
def default_provider_registry() -> ProviderRegistryABC:
    """DEPRECATED: Use get_provider_registry() instead.

    Возвращает in-memory реализацию реестра провайдеров по умолчанию.
    """
    return get_provider_registry()


# Re-export for backward compatibility (will be removed in future)
# Import is done lazily to avoid circular imports at module load time
def __getattr__(name: str):
    """Lazy import for backward compatibility."""
    if name == "InMemoryProviderRegistry":
        from bioetl.infrastructure.provider_registry import InMemoryProviderRegistry

        return InMemoryProviderRegistry
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Domain abstractions
    "ProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    # Domain errors
    "ProviderRegistryError",
    "ProviderNotRegisteredError",
    "ProviderAlreadyRegisteredError",
    # Factory function
    "get_provider_registry",
    # Backward compatibility (deprecated - use infrastructure.provider_registry)
    "InMemoryProviderRegistry",
    "default_provider_registry",
]
