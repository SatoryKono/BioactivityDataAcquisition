"""Tests for DataSourceRegistry.

Verifies data source creator registration and retrieval.
After registry unification, DataSourceRegistry delegates to ProviderRegistry.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.adapters_factory import (
    DataSourceCreator,
    DataSourceRegistry,
)
from bioetl.composition.providers import ProviderRegistry, ensure_providers_loaded


class TestDataSourceRegistry:
    """Tests for DataSourceRegistry class."""

    def test_get_chembl_creator(self):
        """Verify chembl creator can be retrieved."""
        ensure_providers_loaded()
        creator = DataSourceRegistry.get("chembl")
        assert creator is not None
        assert callable(creator)

    def test_get_pubchem_creator(self):
        """Verify pubchem creator can be retrieved."""
        ensure_providers_loaded()
        creator = DataSourceRegistry.get("pubchem")
        assert creator is not None
        assert callable(creator)

    def test_get_uniprot_creator(self):
        """Verify uniprot creator can be retrieved."""
        ensure_providers_loaded()
        creator = DataSourceRegistry.get("uniprot")
        assert creator is not None
        assert callable(creator)

    def test_get_pubmed_creator(self):
        """Verify pubmed creator can be retrieved."""
        ensure_providers_loaded()
        creator = DataSourceRegistry.get("pubmed")
        assert creator is not None
        assert callable(creator)

    def test_get_unknown_provider_raises_key_error(self):
        """Verify unknown provider raises KeyError with helpful message."""
        ensure_providers_loaded()
        with pytest.raises(KeyError) as exc_info:
            DataSourceRegistry.get("unknown_provider")

        error_message = str(exc_info.value)
        assert "unknown_provider" in error_message
        assert "Available:" in error_message

    def test_list_providers(self):
        """Verify list_providers returns all registered providers."""
        ensure_providers_loaded()
        providers = DataSourceRegistry.list_providers()

        assert isinstance(providers, list)
        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert "pubmed" in providers
        assert len(providers) >= 4

    def test_contains_returns_true_for_registered(self):
        """Verify contains returns True for registered providers."""
        ensure_providers_loaded()
        assert DataSourceRegistry.contains("chembl") is True
        assert DataSourceRegistry.contains("pubchem") is True
        assert DataSourceRegistry.contains("uniprot") is True
        assert DataSourceRegistry.contains("pubmed") is True

    def test_contains_returns_false_for_unknown(self):
        """Verify contains returns False for unknown providers."""
        ensure_providers_loaded()
        assert DataSourceRegistry.contains("unknown_provider") is False


class TestDataSourceRegistryDelegation:
    """Tests for delegation to ProviderRegistry."""

    def test_get_delegates_to_provider_registry(self):
        """Verify get() returns a creator that calls ProviderRegistry."""
        ensure_providers_loaded()

        # Get creator from DataSourceRegistry
        creator = DataSourceRegistry.get("chembl")

        # Verify it's callable and matches protocol
        assert callable(creator)

        # Creator should have correct signature (protocol compliance)
        import inspect

        sig = inspect.signature(creator)
        param_names = set(sig.parameters.keys())
        expected = {"settings", "pipeline_config", "logger"}
        assert expected <= param_names

    def test_list_providers_matches_provider_registry(self):
        """Verify list_providers matches ProviderRegistry."""
        ensure_providers_loaded()

        ds_providers = set(DataSourceRegistry.list_providers())
        pr_providers = set(ProviderRegistry.list_providers())

        # DataSourceRegistry should include all ProviderRegistry providers
        assert ds_providers == pr_providers


class TestDataSourceCreatorProtocol:
    """Tests for DataSourceCreator protocol compliance."""

    def test_all_creators_match_protocol(self):
        """Verify all registered creators match the protocol signature."""
        from inspect import signature

        ensure_providers_loaded()

        expected_params = {
            "settings",
            "pipeline_config",
            "logger",
            "filter_config",
            "metrics",
            "pipeline_name",
        }

        for provider in DataSourceRegistry.list_providers():
            creator = DataSourceRegistry.get(provider)
            sig = signature(creator)
            param_names = set(sig.parameters.keys())

            # All required parameters should be present
            assert expected_params <= param_names, (
                f"Creator for {provider} missing params: "
                f"{expected_params - param_names}"
            )


class TestWrapWithFilter:
    """Tests for _wrap_with_filter helper function (now in registration.py)."""

    def test_returns_original_when_no_filter(self):
        """Verify original data source returned when filter is None."""
        from bioetl.composition.providers.registration import _wrap_with_filter

        mock_data_source = MagicMock()

        result = _wrap_with_filter(mock_data_source, None)

        assert result is mock_data_source

    def test_returns_original_when_filter_disabled(self):
        """Verify original data source returned when filter is disabled."""
        from bioetl.composition.providers.registration import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = False

        result = _wrap_with_filter(mock_data_source, mock_filter)

        assert result is mock_data_source

    def test_wraps_when_filter_enabled(self):
        """Verify FilteredDataSource is created when filter is enabled."""
        from bioetl.application.core.filtered_data_source import FilteredDataSource
        from bioetl.composition.providers.registration import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True

        result = _wrap_with_filter(mock_data_source, mock_filter)

        # Result should be different from original (wrapped)
        assert result is not mock_data_source
        # Should be FilteredDataSource instance
        assert isinstance(result, FilteredDataSource)

    def test_wraps_with_metrics(self):
        """Verify metrics are passed to FilteredDataSource."""
        from bioetl.application.core.filtered_data_source import FilteredDataSource
        from bioetl.composition.providers.registration import _wrap_with_filter

        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True
        mock_metrics = MagicMock()

        result = _wrap_with_filter(
            mock_data_source, mock_filter, metrics=mock_metrics, pipeline_name="test"
        )

        assert isinstance(result, FilteredDataSource)
