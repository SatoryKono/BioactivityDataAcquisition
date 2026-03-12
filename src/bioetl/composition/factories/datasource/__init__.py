"""Data source factory subpackage."""

from __future__ import annotations

from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

DataSourceCreatorPort = DataSourceCreatorProtocol

__all__ = ["DataSourceCreatorProtocol", "DataSourceFactory", "DataSourceRegistry"]
