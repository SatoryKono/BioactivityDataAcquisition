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


class InMemoryProviderRegistry(ProviderRegistryABC):
    """Реализация реестра провайдеров в памяти."""

    def __init__(self) -> None:
        self._providers: dict[ProviderId, ProviderDefinition] = {}

    def register_provider(self, definition: ProviderDefinition) -> None:
        """Регистрирует провайдер в реестре."""
        if definition.id in self._providers:
            raise ProviderAlreadyRegisteredError(definition.id)
        self._providers[definition.id] = definition

    def get_provider(self, provider_id: ProviderId) -> ProviderDefinition:
        """Получает определение провайдера по идентификатору."""
        if provider_id not in self._providers:
            raise ProviderNotRegisteredError(provider_id)
        return self._providers[provider_id]

    def list_providers(self) -> list[ProviderDefinition]:
        """Возвращает список всех зарегистрированных провайдеров."""
        return list(self._providers.values())

    def reset_provider_registry(self) -> None:
        """Очищает реестр провайдеров."""
        self._providers.clear()

    def restore_provider_registry(self, definitions: list[ProviderDefinition]) -> None:
        """Восстанавливает реестр из списка определений."""
        self._providers.clear()
        for definition in definitions:
            self._providers[definition.id] = definition


def default_provider_registry() -> ProviderRegistryABC:
    """Возвращает in-memory реализацию реестра провайдеров по умолчанию."""

    return InMemoryProviderRegistry()


__all__ = [
    "ProviderRegistryError",
    "ProviderNotRegisteredError",
    "ProviderAlreadyRegisteredError",
    "ProviderRegistryABC",
    "ProviderRegistryLoaderABC",
    "InMemoryProviderRegistry",
    "default_provider_registry",
]
