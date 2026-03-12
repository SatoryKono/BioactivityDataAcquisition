"""Lazy factory loader helpers for provider registration internals."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory,
    )
    from bioetl.composition.factories.datasource.http_client import HttpClientFactory


__all__ = [
    "get_data_source_factory",
    "get_http_client_factory",
]


def get_data_source_factory() -> type[DataSourceFactory]:
    """Resolve DataSourceFactory lazily to avoid circular imports.

    Returns:
        Data source factory.
    """
    from bioetl.composition.factories.datasource.data_source_factory import (
        DataSourceFactory,
    )

    return DataSourceFactory


def get_http_client_factory() -> type[HttpClientFactory]:
    """Resolve HttpClientFactory lazily to avoid circular imports.

    Returns:
        Http client factory.
    """
    from bioetl.composition.factories.datasource.http_client import HttpClientFactory

    return HttpClientFactory
