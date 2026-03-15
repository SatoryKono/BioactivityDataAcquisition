"""Compatibility facade for legacy ``datasource.factory`` imports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.factories.datasource._registry_compat import (
    _build_data_source_creator,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)
from bioetl.domain.ports import DataSourcePort

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

DataSourceCreatorPort = DataSourceCreatorProtocol


def create(
    provider: str,
    http_client: UnifiedHTTPClient | None = None,
    logger: LoggerPort | None = None,
    settings: Settings | None = None,
    **kwargs: object,
) -> DataSourcePort:
    """Create a data source adapter via the retained legacy module path."""
    adapter = DataSourceFactory.create(
        provider,
        http_client=http_client,
        logger=logger,
        settings=settings,
        **kwargs,
    )
    assert isinstance(adapter, DataSourcePort), (
        f"Adapter for provider '{provider}' must implement DataSourcePort, "
        f"got {type(adapter)}"
    )
    return adapter

__all__ = [
    "DataSourceCreatorPort",
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "_build_data_source_creator",
    "create",
]
