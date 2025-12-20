"""Unit tests for legacy pipeline factory classes.

These tests cover the deprecated BasePipelineFactory subclasses.
"""

import warnings
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
class TestBasePipelineFactoryDeprecation:
    """Tests for BasePipelineFactory deprecation."""

    def test_subclassing_emits_deprecation_warning(self):
        """Test that subclassing BasePipelineFactory emits DeprecationWarning."""
        from bioetl.composition.factories.base_pipeline_factory import (
            BasePipelineFactory,
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            class TestFactory(BasePipelineFactory):
                pipeline_name = "test"
                pipeline_class = MagicMock

                @classmethod
                def create_data_source(cls, settings, pipeline_config, filter_config=None):
                    return MagicMock()

            # Check that a deprecation warning was issued
            assert len(w) >= 1
            assert any(issubclass(warning.category, DeprecationWarning) for warning in w)
            assert any("GenericPipelineFactory" in str(warning.message) for warning in w)


@pytest.mark.unit
class TestPubMedPublicationsPipelineFactory:
    """Tests for PubMedPublicationsPipelineFactory."""

    @patch("bioetl.composition.factories.pubmed_publications.HttpClientFactory")
    @patch("bioetl.composition.factories.pubmed_publications.PubMedAdapter")
    def test_create_data_source_basic(self, mock_adapter_class, mock_http_factory):
        """Test basic data source creation."""
        # Import triggers deprecation warning, catch it
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.pubmed_publications import (
                PubMedPublicationsPipelineFactory,
            )

        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client

        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter

        # Create mock settings
        settings = MagicMock()
        settings.pubmed_api_key = None
        settings.default_email = "test@example.com"

        # Create mock pipeline config
        pipeline_config = MagicMock()
        pipeline_config.source.api_key = None
        pipeline_config.source.email = None

        result = PubMedPublicationsPipelineFactory.create_data_source(
            settings, pipeline_config
        )

        assert result == mock_adapter
        mock_http_factory.create_for_provider.assert_called_once_with("pubmed", settings)
        mock_adapter_class.assert_called_once()

    @patch("bioetl.composition.factories.pubmed_publications.HttpClientFactory")
    @patch("bioetl.composition.factories.pubmed_publications.PubMedAdapter")
    def test_create_data_source_with_api_key_from_config(
        self, mock_adapter_class, mock_http_factory
    ):
        """Test data source creation with API key from pipeline config."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.pubmed_publications import (
                PubMedPublicationsPipelineFactory,
            )

        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_adapter_class.return_value = MagicMock()

        settings = MagicMock()
        settings.pubmed_api_key = MagicMock()
        settings.pubmed_api_key.get_secret_value.return_value = "settings_key"
        settings.default_email = "default@example.com"

        pipeline_config = MagicMock()
        pipeline_config.source.api_key = "config_key"
        pipeline_config.source.email = "config@example.com"

        PubMedPublicationsPipelineFactory.create_data_source(settings, pipeline_config)

        # Should use config API key, not settings
        call_kwargs = mock_adapter_class.call_args[1]
        assert call_kwargs["api_key"] == "config_key"
        assert call_kwargs["email"] == "config@example.com"

    @patch("bioetl.composition.factories.pubmed_publications.HttpClientFactory")
    @patch("bioetl.composition.factories.pubmed_publications.PubMedAdapter")
    @patch("bioetl.composition.factories.pubmed_publications.FilteredDataSource")
    @patch("bioetl.composition.factories.pubmed_publications.CsvFilterReader")
    def test_create_data_source_with_filter(
        self,
        mock_csv_reader_class,
        mock_filtered_ds_class,
        mock_adapter_class,
        mock_http_factory,
    ):
        """Test data source creation with filter config."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.pubmed_publications import (
                PubMedPublicationsPipelineFactory,
            )

        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_adapter = MagicMock()
        mock_adapter_class.return_value = mock_adapter
        mock_filtered_ds = MagicMock()
        mock_filtered_ds_class.return_value = mock_filtered_ds

        settings = MagicMock()
        settings.pubmed_api_key = None
        settings.default_email = "test@example.com"

        pipeline_config = MagicMock()
        pipeline_config.source.api_key = None
        pipeline_config.source.email = None

        filter_config = MagicMock()
        filter_config.enabled = True

        result = PubMedPublicationsPipelineFactory.create_data_source(
            settings, pipeline_config, filter_config
        )

        assert result == mock_filtered_ds
        mock_filtered_ds_class.assert_called_once()


@pytest.mark.unit
class TestUniProtProteinPipelineFactory:
    """Tests for UniProtProteinPipelineFactory."""

    @patch("bioetl.composition.factories.uniprot_protein.HttpClientFactory")
    @patch("bioetl.composition.factories.uniprot_protein.DataSourceFactory")
    def test_create_data_source_basic(self, mock_ds_factory, mock_http_factory):
        """Test basic data source creation."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.uniprot_protein import (
                UniProtProteinPipelineFactory,
            )

        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client

        mock_data_source = MagicMock()
        mock_ds_factory.create.return_value = mock_data_source

        settings = MagicMock()
        settings.strict_error_handling = True

        pipeline_config = MagicMock()
        pipeline_config.source.api.base_url = None

        result = UniProtProteinPipelineFactory.create_data_source(
            settings, pipeline_config
        )

        assert result == mock_data_source
        mock_http_factory.create_for_provider.assert_called_once_with("uniprot", settings)
        mock_ds_factory.create.assert_called_once_with(
            "uniprot",
            http_client=mock_http_client,
            base_url="https://rest.uniprot.org",
            strict_error_handling=True,
        )

    @patch("bioetl.composition.factories.uniprot_protein.HttpClientFactory")
    @patch("bioetl.composition.factories.uniprot_protein.DataSourceFactory")
    def test_create_data_source_with_custom_base_url(
        self, mock_ds_factory, mock_http_factory
    ):
        """Test data source creation with custom base URL."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.uniprot_protein import (
                UniProtProteinPipelineFactory,
            )

        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_ds_factory.create.return_value = MagicMock()

        settings = MagicMock()
        settings.strict_error_handling = False

        pipeline_config = MagicMock()
        pipeline_config.source.api.base_url = "https://custom.uniprot.org"

        UniProtProteinPipelineFactory.create_data_source(settings, pipeline_config)

        call_kwargs = mock_ds_factory.create.call_args[1]
        assert call_kwargs["base_url"] == "https://custom.uniprot.org"

    @patch("bioetl.composition.factories.uniprot_protein.HttpClientFactory")
    @patch("bioetl.composition.factories.uniprot_protein.DataSourceFactory")
    @patch("bioetl.composition.factories.uniprot_protein.FilteredDataSource")
    @patch("bioetl.composition.factories.uniprot_protein.CsvFilterReader")
    def test_create_data_source_with_filter(
        self,
        mock_csv_reader_class,
        mock_filtered_ds_class,
        mock_ds_factory,
        mock_http_factory,
    ):
        """Test data source creation with filter config."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from bioetl.composition.factories.uniprot_protein import (
                UniProtProteinPipelineFactory,
            )

        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_data_source = MagicMock()
        mock_ds_factory.create.return_value = mock_data_source
        mock_filtered_ds = MagicMock()
        mock_filtered_ds_class.return_value = mock_filtered_ds

        settings = MagicMock()
        settings.strict_error_handling = True

        pipeline_config = MagicMock()
        pipeline_config.source.api.base_url = None

        filter_config = MagicMock()
        filter_config.enabled = True

        result = UniProtProteinPipelineFactory.create_data_source(
            settings, pipeline_config, filter_config
        )

        assert result == mock_filtered_ds
        mock_filtered_ds_class.assert_called_once()


@pytest.mark.unit
class TestBasePipelineFactoryBuildServices:
    """Tests for BasePipelineFactory.build_services method."""

    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    def test_build_services_loads_config_when_not_provided(
        self, mock_services_factory, mock_load_config
    ):
        """Test build_services loads config when not provided."""
        from bioetl.composition.factories.base_pipeline_factory import (
            BasePipelineFactory,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            class TestFactory(BasePipelineFactory):
                pipeline_name = "test_pipeline"
                pipeline_class = MagicMock

                @classmethod
                def create_data_source(cls, settings, pipeline_config, filter_config=None):
                    return MagicMock()

        mock_config = MagicMock()
        mock_load_config.return_value = mock_config
        mock_services_factory.create_common_services.return_value = MagicMock()

        settings = MagicMock()
        logger = MagicMock()

        TestFactory.build_services(settings, logger)

        mock_load_config.assert_called_once_with("test_pipeline")

    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    def test_build_services_uses_provided_config(
        self, mock_services_factory, mock_load_config
    ):
        """Test build_services uses provided config instead of loading."""
        from bioetl.composition.factories.base_pipeline_factory import (
            BasePipelineFactory,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            class TestFactory(BasePipelineFactory):
                pipeline_name = "test_pipeline"
                pipeline_class = MagicMock

                @classmethod
                def create_data_source(cls, settings, pipeline_config, filter_config=None):
                    return MagicMock()

        provided_config = MagicMock()
        mock_services_factory.create_common_services.return_value = MagicMock()

        settings = MagicMock()
        logger = MagicMock()

        TestFactory.build_services(settings, logger, config=provided_config)

        mock_load_config.assert_not_called()


@pytest.mark.unit
class TestBasePipelineFactoryCreateWithServices:
    """Tests for BasePipelineFactory.create_with_services method."""

    @patch("bioetl.composition.factories.base_pipeline_factory.load_pipeline_config")
    @patch("bioetl.composition.factories.base_pipeline_factory.yaml_config_to_domain")
    @patch("bioetl.composition.factories.base_pipeline_factory.BaseServicesFactory")
    def test_create_with_services(
        self, mock_services_factory, mock_yaml_to_domain, mock_load_config
    ):
        """Test create_with_services creates pipeline instance."""
        from bioetl.composition.factories.base_pipeline_factory import (
            BasePipelineFactory,
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            mock_pipeline_class = MagicMock()
            mock_pipeline_instance = MagicMock()
            mock_pipeline_class.create.return_value = mock_pipeline_instance

            class TestFactory(BasePipelineFactory):
                pipeline_name = "test_pipeline"
                pipeline_class = mock_pipeline_class

                @classmethod
                def create_data_source(cls, settings, pipeline_config, filter_config=None):
                    return MagicMock()

        mock_yaml_config = MagicMock()
        mock_load_config.return_value = mock_yaml_config
        mock_domain_config = MagicMock()
        mock_yaml_to_domain.return_value = mock_domain_config
        mock_services = MagicMock()
        mock_services_factory.create_common_services.return_value = mock_services

        runtime = MagicMock()
        settings = MagicMock()
        logger = MagicMock()

        result = TestFactory.create_with_services(runtime, settings, logger)

        assert result == mock_pipeline_instance
        mock_pipeline_class.create.assert_called_once_with(
            runtime=runtime,
            services=mock_services,
            config=mock_domain_config,
        )
