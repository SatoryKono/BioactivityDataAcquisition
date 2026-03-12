"""Unit tests for provider factory_loader module.

Tests that lazy factory resolution functions return the correct classes
and avoid circular imports via deferred import pattern.
"""

from __future__ import annotations

import pytest

from bioetl.composition.providers.factory_loader import (
    get_data_source_factory,
    get_http_client_factory,
)


@pytest.mark.unit
class TestGetDataSourceFactory:
    """Tests for get_data_source_factory lazy resolver."""

    def test_returns_data_source_factory_class(self) -> None:
        """get_data_source_factory should return the DataSourceFactory class."""
        from bioetl.composition.factories.datasource.data_source_factory import (
            DataSourceFactory,
        )

        result = get_data_source_factory()

        assert result is DataSourceFactory

    def test_returns_class_not_instance(self) -> None:
        """Should return the class itself, not an instantiated object."""
        result = get_data_source_factory()

        assert isinstance(result, type)

    def test_consistent_across_calls(self) -> None:
        """Multiple calls should return the same class object."""
        result1 = get_data_source_factory()
        result2 = get_data_source_factory()

        assert result1 is result2


@pytest.mark.unit
class TestGetHttpClientFactory:
    """Tests for get_http_client_factory lazy resolver."""

    def test_returns_http_client_factory_class(self) -> None:
        """get_http_client_factory should return the HttpClientFactory class."""
        from bioetl.composition.factories.datasource.http_client import (
            HttpClientFactory,
        )

        result = get_http_client_factory()

        assert result is HttpClientFactory

    def test_returns_class_not_instance(self) -> None:
        """Should return the class itself, not an instantiated object."""
        result = get_http_client_factory()

        assert isinstance(result, type)

    def test_consistent_across_calls(self) -> None:
        """Multiple calls should return the same class object."""
        result1 = get_http_client_factory()
        result2 = get_http_client_factory()

        assert result1 is result2
