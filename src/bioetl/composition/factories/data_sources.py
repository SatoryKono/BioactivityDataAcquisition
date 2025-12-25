"""DataSourceFactory for creating data source adapters.

Implements Abstract Factory pattern for data sources.
Uses ProviderRegistry for unified provider registration.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded
from bioetl.domain.ports import DataSourcePort, LoggerPort

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings


class DataSourceFactory:
    """Factory for creating data source adapters.

    Uses ProviderRegistry for provider lookup and adapter creation.
    Falls back to legacy static mapping for backward compatibility.
    """

    # Legacy mapping for backward compatibility
    # Will be removed after full migration to ProviderRegistry
    _adapters: ClassVar[dict[str, tuple[str, str]]] = {
        "chembl": ("bioetl.infrastructure.adapters.chembl.client", "ChemblAdapter"),
        "pubchem": ("bioetl.infrastructure.adapters.pubchem.client", "PubChemAdapter"),
        "uniprot": ("bioetl.infrastructure.adapters.uniprot.client", "UniProtAdapter"),
    }

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None = None,
        logger: LoggerPort | None = None,
        settings: Settings | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Create a data source adapter.

        First attempts to use ProviderRegistry for provider lookup.
        Falls back to legacy static mapping if provider not found in registry.

        Args:
            provider: The name of the data provider (e.g., 'chembl', 'pubchem').
            http_client: The shared HTTP client to use (only for adapters that support it).
            logger: LoggerPort instance for structured logging.
            settings: Application settings (for custom creators).
            **kwargs: Additional keyword arguments to pass to the adapter constructor.

        Returns:
            An instance of the requested data source adapter.

        Raises:
            ValueError: If the provider is unknown.
        """
        # Ensure providers are loaded
        ensure_providers_loaded()

        # Remove filter_config from kwargs - it's handled by FilteredDataSource wrapper
        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}

        # Try ProviderRegistry first
        if ProviderRegistry.is_registered(provider):
            return ProviderRegistry.create_adapter(
                provider,
                http_client=http_client,
                logger=logger,
                settings=settings,
                **adapter_kwargs,
            )

        # Legacy fallback for backward compatibility
        return cls._create_legacy(provider, http_client, logger, **adapter_kwargs)

    @classmethod
    def _create_legacy(
        cls,
        provider: str,
        http_client: UnifiedHTTPClient | None,
        logger: LoggerPort | None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Legacy adapter creation method.

        Used for backward compatibility with adapters not yet migrated
        to ProviderRegistry.

        Args:
            provider: Provider name
            http_client: HTTP client
            logger: Logger
            **kwargs: Additional arguments

        Returns:
            DataSourcePort instance

        Raises:
            ValueError: If provider is unknown
        """
        if provider not in cls._adapters:
            raise ValueError(f"Unknown provider: {provider}")

        module_path, class_name = cls._adapters[provider]
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)

        if provider == "chembl":
            return adapter_cls(http_client=http_client, logger=logger, **kwargs)

        if provider == "uniprot":
            return adapter_cls(http_client=http_client, logger=logger, **kwargs)

        # PubChem manages its own client, only needs logger
        return adapter_cls(logger=logger, **kwargs)

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all available providers.

        Returns providers from both ProviderRegistry and legacy mapping.
        """
        ensure_providers_loaded()
        registry_providers = set(ProviderRegistry.list_providers())
        legacy_providers = set(cls._adapters.keys())
        return sorted(registry_providers | legacy_providers)
