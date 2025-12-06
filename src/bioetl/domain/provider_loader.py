from __future__ import annotations

from typing import Protocol

from bioetl.domain.provider_registry import MutableProviderRegistryABC


class ProviderLoaderProtocol(Protocol):
    """Порт для загрузки и валидации реестра провайдеров."""

    def load_registry(
        self, *, registry: MutableProviderRegistryABC | None = None
    ) -> MutableProviderRegistryABC:
        """Загружает реестр провайдеров, возвращая заполненный экземпляр."""


__all__ = ["ProviderLoaderProtocol"]

