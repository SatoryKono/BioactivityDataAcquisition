"""In-memory implementation of provider registry.

This module contains the concrete implementation of ProviderRegistryABC
stored in memory. It serves as a default implementation for the application.
"""

from __future__ import annotations

from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
    ProviderRegistryABC,
)
from bioetl.domain.providers import ProviderDefinition, ProviderId


class InMemoryProviderRegistry(ProviderRegistryABC):
    """Реализация реестра провайдеров в памяти.

    Concrete implementation of the provider registry that stores
    provider definitions in memory.
    """

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


__all__ = [
    "InMemoryProviderRegistry",
]
