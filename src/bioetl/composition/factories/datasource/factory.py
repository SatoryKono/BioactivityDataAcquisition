"""Compatibility facade for legacy ``datasource.factory`` imports."""

from __future__ import annotations

from bioetl.composition.factories.datasource._registry_compat import (
    _build_data_source_creator,
)
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

DataSourceCreatorPort = DataSourceCreatorProtocol

__all__ = [
    "DataSourceCreatorProtocol",
    "DataSourceCreatorPort",
    "DataSourceFactory",
    "DataSourceRegistry",
    "_build_data_source_creator",
]
