"""Provider registry resolution service.

This service encapsulates the logic for obtaining and caching provider registries
through various sources (direct injection, lazy provider, loader).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from bioetl.domain.provider_registry import (
        ProviderRegistryABC,
        ProviderRegistryFactory,
        ProviderRegistryLoaderABC,
    )
    from bioetl.domain.providers import ProviderDefinition


class ProviderRegistryResolver:
    """Resolves and caches provider registry instances.

    This service implements a fallback chain for registry resolution:
    1. Use directly injected registry if available
    2. Try to load via registry loader
    3. Fall back to provider callback

    The resolved registry is cached for subsequent calls.

    Args:
        provider_registry: Optional pre-configured provider registry.
        provider_registry_provider: Callable that returns a provider registry.
        provider_registry_factory: Factory for creating provider registries.
        provider_loader: Loader for provider definitions.
        provider_loader_factory: Factory for creating provider loaders.
    """

    def __init__(
        self,
        *,
        provider_registry: "ProviderRegistryABC | None" = None,
        provider_registry_provider: "Callable[[], ProviderRegistryABC] | None" = None,
        provider_registry_factory: "ProviderRegistryFactory",
        provider_loader: "ProviderRegistryLoaderABC | None" = None,
        provider_loader_factory: "Callable[[], ProviderRegistryLoaderABC] | None" = None,
    ) -> None:
        self._provider_registry = provider_registry
        self._provider_registry_provider = provider_registry_provider
        self._provider_registry_factory = provider_registry_factory
        self._provider_loader = provider_loader
        self._provider_loader_factory = provider_loader_factory

    @property
    def registry_factory(self) -> "ProviderRegistryFactory":
        """Access the registry factory."""
        return self._provider_registry_factory

    @property
    def provider_loader(self) -> "ProviderRegistryLoaderABC | None":
        """Access the provider loader (may be None)."""
        return self._provider_loader

    @property
    def provider_loader_factory(
        self,
    ) -> "Callable[[], ProviderRegistryLoaderABC] | None":
        """Access the provider loader factory (may be None)."""
        return self._provider_loader_factory

    def get_registry(self) -> "ProviderRegistryABC":
        """Get the provider registry, resolving through fallback chain.

        Returns:
            The resolved provider registry.

        Raises:
            RuntimeError: If no registry source is configured.
        """
        if self._provider_registry is not None:
            return self._provider_registry

        registry = self._load_registry_via_loader()
        if registry is not None:
            return registry

        return self._resolve_registry_from_provider()

    def serialize_registry(self) -> "list[ProviderDefinition] | None":
        """Serialize current registry for subprocess transfer.

        Returns:
            List of provider definitions if registry exists, None otherwise.
        """
        if self._provider_registry is None:
            return None
        return list(self._provider_registry.list_providers())

    def _load_registry_via_loader(self) -> "ProviderRegistryABC | None":
        """Try to load registry via loader."""
        loader = self._provider_loader
        if loader is None and self._provider_loader_factory is not None:
            loader = self._provider_loader_factory()
            self._provider_loader = loader

        if loader is None:
            return None

        registry = loader.get_registry(registry=self._provider_registry_factory())
        self._provider_registry = registry
        return registry

    def _resolve_registry_from_provider(self) -> "ProviderRegistryABC":
        """Get registry via provider callback (fallback)."""
        if self._provider_registry_provider is None:
            raise RuntimeError("Provider registry is not configured")

        registry = self._provider_registry_provider()
        if registry is None:
            raise RuntimeError("Provider registry provider returned None")

        self._provider_registry = registry
        return registry

    @staticmethod
    def build_for_subprocess(
        *,
        loader: "ProviderRegistryLoaderABC | None",
        registry_payload: "list[ProviderDefinition] | None",
        registry_factory: "ProviderRegistryFactory",
    ) -> "ProviderRegistryABC":
        """Build registry for subprocess execution.

        This static method reconstructs a registry in a subprocess
        from serialized data.

        Args:
            loader: Optional provider loader.
            registry_payload: Optional serialized provider definitions.
            registry_factory: Factory for creating registry instances.

        Returns:
            Configured provider registry.
        """
        if registry_payload is not None:
            registry = registry_factory()
            registry.restore_provider_registry(registry_payload)
            return registry

        if loader is not None:
            return loader.get_registry(registry=registry_factory())

        return registry_factory()


__all__ = ["ProviderRegistryResolver"]
