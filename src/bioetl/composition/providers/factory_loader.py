"""Lazy factory loader helpers for provider registration internals."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any


def get_data_source_factory() -> Any:  # Any: lazy-resolved factory ...
    """Resolve DataSourceFactory lazily to avoid circular imports."""
    from bioetl.composition.factories.data_source_factory import DataSourceFactory

    return DataSourceFactory


def get_http_client_factory() -> Any:  # Any: lazy-resolved factory ...
    """Resolve HttpClientFactory lazily to avoid circular imports."""
    from bioetl.composition.factories.http_client_factory import HttpClientFactory

    return HttpClientFactory
