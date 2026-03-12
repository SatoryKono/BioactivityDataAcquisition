"""Canonical data-source factory module.

Provides data-source factory and registry entrypoints with descriptive naming.
The legacy ``factory`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.datasource.factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
    _build_data_source_creator,
)

DataSourceCreatorPort = DataSourceCreatorProtocol


def get_data_source_creator(provider: str) -> DataSourceCreatorProtocol:
    """Return the canonical provider-bound data-source creator."""
    return _build_data_source_creator(provider)


__all__ = [
    "DataSourceCreatorProtocol",
    "DataSourceFactory",
    "DataSourceRegistry",
    "get_data_source_creator",
]
