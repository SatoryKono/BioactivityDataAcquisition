"""DataSourceFactory for creating data source adapters.

Implements Abstract Factory pattern for data sources.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, ClassVar

from bioetl.domain.ports import DataSourcePort, LoggerPort

if TYPE_CHECKING:
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient


class DataSourceFactory:
    """Factory for creating data source adapters."""

    _adapters: ClassVar[dict[str, tuple[str, str]]] = {
        "chembl": ("bioetl.infrastructure.adapters.chembl.client", "ChemblAdapter"),
        "pubchem": ("bioetl.infrastructure.adapters.pubchem.client", "PubChemAdapter"),
        "uniprot": ("bioetl.infrastructure.adapters.uniprot.client", "UniProtAdapter"),
    }

    @classmethod
    def create(
        cls,
        provider: str,
        http_client: "UnifiedHTTPClient | None" = None,
        logger: LoggerPort | None = None,
        **kwargs: Any,
    ) -> DataSourcePort:
        """Create a data source adapter.

        Args:
            provider: The name of the data provider (e.g., 'chembl', 'pubchem').
            http_client: The shared HTTP client to use (only for adapters that support it).
            logger: LoggerPort instance for structured logging.
            **kwargs: Additional keyword arguments to pass to the adapter constructor.

        Returns:
            An instance of the requested data source adapter.

        Raises:
            ValueError: If the provider is unknown.
        """
        if provider not in cls._adapters:
            raise ValueError(f"Unknown provider: {provider}")

        module_path, class_name = cls._adapters[provider]
        module = importlib.import_module(module_path)
        adapter_cls = getattr(module, class_name)

        # Remove filter_config from kwargs - it's handled by FilteredDataSource wrapper,
        # not by the adapters themselves
        adapter_kwargs = {k: v for k, v in kwargs.items() if k != "filter_config"}

        if provider == "chembl":
            return adapter_cls(http_client=http_client, logger=logger, **adapter_kwargs)

        if provider == "uniprot":
            return adapter_cls(http_client=http_client, logger=logger, **adapter_kwargs)

        # PubChem manages its own client, only needs logger
        return adapter_cls(logger=logger, **adapter_kwargs)
