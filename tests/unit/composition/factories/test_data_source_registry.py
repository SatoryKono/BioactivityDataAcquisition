"""Tests for DataSourceRegistry.

Verifies data source creator registration and retrieval.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bioetl.composition.factories.data_source_registry import (
    DataSourceRegistry,
    _wrap_with_filter,
    create_chembl_data_source,
    create_pubchem_data_source,
    create_pubmed_data_source,
    create_uniprot_data_source,
)


class TestDataSourceRegistry:
    """Tests for DataSourceRegistry class."""

    def test_get_chembl_creator(self):
        """Verify chembl creator can be retrieved."""
        creator = DataSourceRegistry.get("chembl")
        assert creator is not None
        assert callable(creator)
        assert creator == create_chembl_data_source

    def test_get_pubchem_creator(self):
        """Verify pubchem creator can be retrieved."""
        creator = DataSourceRegistry.get("pubchem")
        assert creator is not None
        assert callable(creator)
        assert creator == create_pubchem_data_source

    def test_get_uniprot_creator(self):
        """Verify uniprot creator can be retrieved."""
        creator = DataSourceRegistry.get("uniprot")
        assert creator is not None
        assert callable(creator)
        assert creator == create_uniprot_data_source

    def test_get_pubmed_creator(self):
        """Verify pubmed creator can be retrieved."""
        creator = DataSourceRegistry.get("pubmed")
        assert creator is not None
        assert callable(creator)
        assert creator == create_pubmed_data_source

    def test_get_unknown_provider_raises_key_error(self):
        """Verify unknown provider raises KeyError with helpful message."""
        with pytest.raises(KeyError) as exc_info:
            DataSourceRegistry.get("unknown_provider")

        error_message = str(exc_info.value)
        assert "unknown_provider" in error_message
        assert "Available:" in error_message

    def test_list_providers(self):
        """Verify list_providers returns all registered providers."""
        providers = DataSourceRegistry.list_providers()

        assert isinstance(providers, list)
        assert "chembl" in providers
        assert "pubchem" in providers
        assert "uniprot" in providers
        assert "pubmed" in providers
        assert len(providers) >= 4

    def test_register_new_provider(self):
        """Verify new provider can be registered."""

        def mock_creator(**kwargs):
            return MagicMock()

        # Register new provider
        DataSourceRegistry.register("test_provider", mock_creator)

        try:
            # Verify it can be retrieved
            creator = DataSourceRegistry.get("test_provider")
            assert creator == mock_creator
            assert "test_provider" in DataSourceRegistry.list_providers()
        finally:
            # Cleanup: remove test provider
            del DataSourceRegistry._creators["test_provider"]

    def test_register_overwrites_existing(self):
        """Verify registering existing provider overwrites."""
        original_creator = DataSourceRegistry.get("chembl")

        def new_creator(**kwargs):
            return MagicMock()

        try:
            DataSourceRegistry.register("chembl", new_creator)
            assert DataSourceRegistry.get("chembl") == new_creator
        finally:
            # Restore original
            DataSourceRegistry.register("chembl", original_creator)


class TestWrapWithFilter:
    """Tests for _wrap_with_filter helper function."""

    def test_returns_original_when_no_filter(self):
        """Verify original data source returned when filter is None."""
        mock_data_source = MagicMock()

        result = _wrap_with_filter(mock_data_source, None)

        assert result is mock_data_source

    def test_returns_original_when_filter_disabled(self):
        """Verify original data source returned when filter is disabled."""
        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = False

        result = _wrap_with_filter(mock_data_source, mock_filter)

        assert result is mock_data_source

    def test_wraps_when_filter_enabled(self):
        """Verify FilteredDataSource is created when filter is enabled."""
        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True

        result = _wrap_with_filter(mock_data_source, mock_filter)

        # Result should be different from original (wrapped)
        assert result is not mock_data_source
        # Should be FilteredDataSource instance
        from bioetl.application.core.filtered_data_source import FilteredDataSource

        assert isinstance(result, FilteredDataSource)

    def test_wraps_with_metrics(self):
        """Verify metrics are passed to FilteredDataSource."""
        mock_data_source = MagicMock()
        mock_filter = MagicMock()
        mock_filter.enabled = True
        mock_metrics = MagicMock()

        result = _wrap_with_filter(
            mock_data_source, mock_filter, metrics=mock_metrics, pipeline_name="test"
        )

        from bioetl.application.core.filtered_data_source import FilteredDataSource

        assert isinstance(result, FilteredDataSource)


class TestCreateChemblDataSource:
    """Tests for create_chembl_data_source function."""

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_creates_chembl_adapter(self, mock_ds_factory, mock_http_factory):
        """Verify ChEMBL adapter is created with correct parameters."""
        mock_settings = MagicMock()
        mock_config = MagicMock()
        mock_logger = MagicMock()
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = create_chembl_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        mock_http_factory.create_for_provider.assert_called_once_with(
            "chembl", mock_settings
        )
        mock_ds_factory.create.assert_called_once()
        assert result is mock_adapter

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_wraps_with_filter_when_configured(self, mock_ds_factory, mock_http_factory):
        """Verify filter wrapping works for ChEMBL."""
        mock_settings = MagicMock()
        mock_config = MagicMock()
        mock_logger = MagicMock()
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        mock_filter = MagicMock()
        mock_filter.enabled = True

        result = create_chembl_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
            filter_config=mock_filter,
        )

        # Should return FilteredDataSource wrapper
        from bioetl.application.core.filtered_data_source import FilteredDataSource

        assert isinstance(result, FilteredDataSource)


class TestCreatePubchemDataSource:
    """Tests for create_pubchem_data_source function."""

    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_creates_pubchem_adapter_with_rate_limit(self, mock_ds_factory):
        """Verify PubChem adapter is created with rate limit."""
        mock_settings = MagicMock()
        mock_settings.strict_error_handling = False
        mock_config = MagicMock()
        mock_logger = MagicMock()
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = create_pubchem_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        mock_ds_factory.create.assert_called_once_with(
            "pubchem",
            http_client=None,
            logger=mock_logger,
            rate=5.0,
            strict_error_handling=False,
        )
        assert result is mock_adapter


class TestCreateUniprotDataSource:
    """Tests for create_uniprot_data_source function."""

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_creates_uniprot_adapter_with_base_url(
        self, mock_ds_factory, mock_http_factory
    ):
        """Verify UniProt adapter is created with base URL."""
        mock_settings = MagicMock()
        mock_settings.strict_error_handling = True
        mock_config = MagicMock()
        mock_config.source.api.base_url = "https://custom.uniprot.org"
        mock_logger = MagicMock()
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        result = create_uniprot_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        mock_ds_factory.create.assert_called_once()
        call_kwargs = mock_ds_factory.create.call_args[1]
        assert call_kwargs["base_url"] == "https://custom.uniprot.org"
        assert call_kwargs["strict_error_handling"] is True

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.composition.factories.data_source_registry.DataSourceFactory")
    def test_uses_default_base_url(self, mock_ds_factory, mock_http_factory):
        """Verify default base URL when not configured."""
        mock_settings = MagicMock()
        mock_settings.strict_error_handling = False
        mock_config = MagicMock()
        mock_config.source.api.base_url = None
        mock_logger = MagicMock()
        mock_adapter = MagicMock()
        mock_ds_factory.create.return_value = mock_adapter

        create_uniprot_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        call_kwargs = mock_ds_factory.create.call_args[1]
        assert call_kwargs["base_url"] == "https://rest.uniprot.org"


class TestCreatePubmedDataSource:
    """Tests for create_pubmed_data_source function."""

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter")
    def test_creates_pubmed_adapter_with_config_api_key(
        self, mock_adapter_class, mock_http_factory
    ):
        """Verify PubMed adapter uses config API key over settings."""
        mock_settings = MagicMock()
        mock_settings.pubmed_api_key = MagicMock()
        mock_settings.pubmed_api_key.get_secret_value.return_value = "settings_key"
        mock_settings.default_email = "default@example.com"

        mock_config = MagicMock()
        mock_config.source.api_key = "config_key"
        mock_config.source.email = "config@example.com"

        mock_logger = MagicMock()
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client

        create_pubmed_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        mock_adapter_class.assert_called_once()
        call_kwargs = mock_adapter_class.call_args[1]
        assert call_kwargs["api_key"] == "config_key"
        assert call_kwargs["email"] == "config@example.com"

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter")
    def test_falls_back_to_settings_api_key(
        self, mock_adapter_class, mock_http_factory
    ):
        """Verify PubMed adapter falls back to settings API key."""
        mock_settings = MagicMock()
        mock_settings.pubmed_api_key = MagicMock()
        mock_settings.pubmed_api_key.get_secret_value.return_value = "settings_key"
        mock_settings.default_email = "default@example.com"

        mock_config = MagicMock()
        mock_config.source.api_key = None  # Not in config
        mock_config.source.email = None

        mock_logger = MagicMock()
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client

        create_pubmed_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        call_kwargs = mock_adapter_class.call_args[1]
        assert call_kwargs["api_key"] == "settings_key"
        assert call_kwargs["email"] == "default@example.com"

    @patch("bioetl.composition.factories.data_source_registry.HttpClientFactory")
    @patch("bioetl.infrastructure.adapters.pubmed.pubmed_client.PubMedAdapter")
    def test_handles_no_api_key(self, mock_adapter_class, mock_http_factory):
        """Verify PubMed adapter works without API key."""
        mock_settings = MagicMock()
        mock_settings.pubmed_api_key = None
        mock_settings.default_email = "default@example.com"

        mock_config = MagicMock()
        mock_config.source.api_key = None
        mock_config.source.email = None

        mock_logger = MagicMock()
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client

        create_pubmed_data_source(
            settings=mock_settings,
            pipeline_config=mock_config,
            logger=mock_logger,
        )

        call_kwargs = mock_adapter_class.call_args[1]
        assert call_kwargs["api_key"] is None
        assert call_kwargs["email"] == "default@example.com"


class TestDataSourceCreatorProtocol:
    """Tests for DataSourceCreator protocol compliance."""

    def test_all_creators_match_protocol(self):
        """Verify all registered creators match the protocol signature."""
        from inspect import signature

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
