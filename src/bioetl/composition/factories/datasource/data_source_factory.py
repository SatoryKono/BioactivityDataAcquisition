"""Canonical data-source factory module.

Provides data-source factory and registry entrypoints with descriptive naming.
The legacy ``factory`` module remains for backward compatibility.
"""

from __future__ import annotations

from bioetl.composition.factories.datasource.factory import (
    DataSourceCreatorProtocol,
    DataSourceFactory,
    DataSourceRegistry,
)

DataSourceCreatorPort = DataSourceCreatorProtocol

__all__ = ["DataSourceCreatorProtocol", "DataSourceFactory", "DataSourceRegistry"]
