"""Domain abstractions for provider registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

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


# Global registry instance
_PROVIDER_REGISTRY: ProviderRegistryABC | None = None


def set_provider_registry(registry: ProviderRegistryABC) -> None:
    """Sets the global provider registry instance.

    This should be called by the application entry point or configuration loader
    to inject the concrete implementation (Dependency Injection).
    """
    global _PROVIDER_REGISTRY
    _PROVIDER_REGISTRY = registry


def get_provider_registry() -> ProviderRegistryABC:
    """Access point for the provider registry.

    Returns the global registry instance.
    Raises RuntimeError if the registry has not been initialized.
    """
    if _PROVIDER_REGISTRY is None:
        raise RuntimeError(
            "Provider registry has not been initialized. "
            "Call set_provider_registry() with a concrete implementation first."
        )
    return _PROVIDER_REGISTRY


# Backward compatibility alias
def default_provider_registry() -> ProviderRegistryABC:
    """DEPRECATED: Use get_provider_registry() instead."""
    return get_provider_registry()


def __getattr__(name: str) -> Any:
    """Lazy import for backward compatibility."""
    if name == "InMemoryProviderRegistry":
        raise ImportError(
            "InMemoryProviderRegistry is no longer available in bioetl.domain. "
            "Import it from bioetl.infrastructure.provider_registry instead."
        )
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
    "set_provider_registry",
    # Backward compatibility
    "default_provider_registry",
]
