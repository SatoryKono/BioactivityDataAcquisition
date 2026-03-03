"""Unit tests for uncovered provider creator branches in registration module."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.providers.registration import (
    _create_chembl_data_source,
    _create_pubmed_data_source,
    _create_openalex_data_source,
    _create_pubchem_adapter,
    _create_semanticscholar_data_source,
    _create_uniprot_idmapping_data_source,
    _create_crossref_data_source,
)


@pytest.mark.unit
class TestChemblPublicationTermBranch:
    """Covers publication_term wrapper branch in ChEMBL creator."""

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration.PublicationTermDataSource")
    @patch("bioetl.composition.providers.registration._get_adapter_config")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_wraps_publication_term_adapter(
        self,
        mock_get_factories: MagicMock,
        mock_get_adapter_config: MagicMock,
        mock_publication_term_data_source: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_factory = MagicMock()
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (mock_factory, mock_http_factory)
        mock_get_adapter_config.return_value = MagicMock()
        mock_base_adapter = MagicMock(name="base_adapter")
        mock_wrapped_adapter = MagicMock(name="publication_term_wrapper")
        mock_filtered_adapter = MagicMock(name="filtered")
        mock_factory.create.return_value = mock_base_adapter
        mock_publication_term_data_source.return_value = mock_wrapped_adapter
        mock_wrap_with_filter.return_value = mock_filtered_adapter

        pipeline_config = MagicMock()
        pipeline_config.entity_type = "publication_term"
        pipeline_config.extraction_params = {}

        result = _create_chembl_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=MagicMock(),
        )

        mock_publication_term_data_source.assert_called_once_with(mock_base_adapter)
        mock_wrap_with_filter.assert_called_once()
        assert result is mock_filtered_adapter


@pytest.mark.unit
class TestPubChemCreatorGuard:
    """Covers logger guard in PubChem adapter creation."""

    def test_pubchem_adapter_requires_logger(self) -> None:
        with pytest.raises(ValueError, match="requires logger"):
            _create_pubchem_adapter(logger=None)


@pytest.mark.unit
class TestCrossRefAndOpenAlexCreators:
    """Covers helper branches for CrossRef/OpenAlex providers."""

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration._get_batch_size_from_config")
    @patch("bioetl.composition.providers.registration._create_crossref_adapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_crossref_creator_uses_pipeline_email_and_batch_size(
        self,
        mock_get_factories: MagicMock,
        mock_create_crossref_adapter: MagicMock,
        mock_get_batch_size_from_config: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client
        mock_get_batch_size_from_config.return_value = 77
        mock_adapter = MagicMock()
        mock_create_crossref_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        pipeline_config = MagicMock()
        pipeline_config.source.email = "pipeline@example.org"

        result = _create_crossref_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            metrics=MagicMock(),
            pipeline_name="crossref_publication",
        )

        mock_http_factory.create_for_provider.assert_called_once_with(
            "crossref", settings
        )
        call_kwargs = mock_create_crossref_adapter.call_args.kwargs
        assert call_kwargs["mailto"] == "pipeline@example.org"
        assert call_kwargs["batch_size"] == 77
        assert result is mock_adapter

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration._get_batch_size_from_config")
    @patch("bioetl.composition.providers.registration._create_openalex_adapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_openalex_creator_uses_settings_email_fallback(
        self,
        mock_get_factories: MagicMock,
        mock_create_openalex_adapter: MagicMock,
        mock_get_batch_size_from_config: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client
        mock_get_batch_size_from_config.return_value = 55
        mock_adapter = MagicMock()
        mock_create_openalex_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        pipeline_config = MagicMock()
        pipeline_config.source.email = ""

        result = _create_openalex_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            metrics=MagicMock(),
            pipeline_name="openalex_publication",
        )

        call_kwargs = mock_create_openalex_adapter.call_args.kwargs
        assert call_kwargs["mailto"] == "default@example.org"
        assert call_kwargs["batch_size"] == 55
        assert result is mock_adapter


@pytest.mark.unit
class TestPlaceholderResolution:
    """Covers ${ENV_VAR} placeholder resolution in source config overrides."""

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration._get_batch_size_from_config")
    @patch("bioetl.composition.providers.registration._create_crossref_adapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_crossref_mailto_resolves_from_env_placeholder(
        self,
        mock_get_factories: MagicMock,
        mock_create_crossref_adapter: MagicMock,
        mock_get_batch_size_from_config: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_get_batch_size_from_config.return_value = 50
        mock_adapter = MagicMock()
        mock_create_crossref_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        pipeline_config = MagicMock()
        pipeline_config.source.email = "${BIOETL_CROSSREF_EMAIL}"

        with patch.dict("os.environ", {"BIOETL_CROSSREF_EMAIL": "env@example.org"}):
            _create_crossref_data_source(
                settings=settings,
                pipeline_config=pipeline_config,
                logger=MagicMock(),
            )

        call_kwargs = mock_create_crossref_adapter.call_args.kwargs
        assert call_kwargs["mailto"] == "env@example.org"

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration.PubMedAdapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_pubmed_placeholders_fallback_to_settings_when_env_missing(
        self,
        mock_get_factories: MagicMock,
        mock_pubmed_adapter: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_adapter = MagicMock()
        mock_pubmed_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.pubmed_api_key = MagicMock()
        settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

        pipeline_config = MagicMock()
        pipeline_config.source.email = "${BIOETL_PUBMED_EMAIL}"
        pipeline_config.source.api_key = "${BIOETL_PUBMED_API_KEY}"

        with patch.dict("os.environ", {}, clear=True):
            _create_pubmed_data_source(
                settings=settings,
                pipeline_config=pipeline_config,
                logger=MagicMock(),
            )

        call_kwargs = mock_pubmed_adapter.call_args.kwargs
        assert call_kwargs["email"] == "default@example.org"
        assert call_kwargs["api_key"] == "settings-key"


@pytest.mark.unit
class TestSemanticScholarCreatorBranches:
    """Covers API key warning / non-warning branches."""

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration._get_batch_size_from_config")
    @patch("bioetl.composition.providers.registration.SemanticScholarAdapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_warns_when_api_key_missing(
        self,
        mock_get_factories: MagicMock,
        mock_semanticscholar_adapter: MagicMock,
        mock_get_batch_size_from_config: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_get_batch_size_from_config.return_value = 120
        mock_adapter = MagicMock()
        mock_semanticscholar_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        logger = MagicMock()
        settings = MagicMock()
        settings.semanticscholar_api_key = None

        result = _create_semanticscholar_data_source(
            settings=settings,
            pipeline_config=MagicMock(),
            logger=logger,
        )

        logger.warning.assert_called_once()
        assert mock_semanticscholar_adapter.call_args.kwargs["api_key"] == ""
        assert result is mock_adapter

    @patch("bioetl.composition.providers.registration._wrap_with_filter")
    @patch("bioetl.composition.providers.registration._get_batch_size_from_config")
    @patch("bioetl.composition.providers.registration.SemanticScholarAdapter")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_does_not_warn_when_api_key_present(
        self,
        mock_get_factories: MagicMock,
        mock_semanticscholar_adapter: MagicMock,
        mock_get_batch_size_from_config: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_get_batch_size_from_config.return_value = 100
        mock_adapter = MagicMock()
        mock_semanticscholar_adapter.return_value = mock_adapter
        mock_wrap_with_filter.return_value = mock_adapter

        logger = MagicMock()
        settings = MagicMock()
        settings.semanticscholar_api_key = MagicMock()
        settings.semanticscholar_api_key.get_secret_value.return_value = "secret"

        _create_semanticscholar_data_source(
            settings=settings,
            pipeline_config=MagicMock(),
            logger=logger,
        )

        logger.warning.assert_not_called()
        assert mock_semanticscholar_adapter.call_args.kwargs["api_key"] == "secret"


@pytest.mark.unit
class TestUniProtIdMappingCreatorBranches:
    """Covers override/default and seed-id branches in ID mapping creator."""

    @patch("bioetl.composition.providers.registration.IDMappingDataSource")
    @patch("bioetl.composition.providers.registration.UniProtIDMappingClient")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_uses_api_overrides_and_seed_ids(
        self,
        mock_get_factories: MagicMock,
        mock_uniprot_client: MagicMock,
        mock_idmapping_data_source: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_client = MagicMock()
        mock_http_factory.create_for_provider.return_value = mock_http_client
        mock_client = MagicMock()
        mock_uniprot_client.return_value = mock_client
        mock_ds = MagicMock()
        mock_idmapping_data_source.return_value = mock_ds

        source_api = SimpleNamespace(
            base_url="https://mirror.uniprot.test",
            from_db="CHEMBL_ID",
            to_db="UniProtKB-Swiss-Prot",
        )
        source = SimpleNamespace(api=source_api, input_path="data/input/custom.csv")
        pipeline_config = SimpleNamespace(source=source)
        filter_config = SimpleNamespace(direct_filter_ids=["CHEMBL1", "CHEMBL2"])

        result = _create_uniprot_idmapping_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            filter_config=filter_config,
            metrics=MagicMock(),
        )

        assert (
            mock_uniprot_client.call_args.kwargs["base_url"]
            == "https://mirror.uniprot.test"
        )
        call_kwargs = mock_idmapping_data_source.call_args.kwargs
        assert call_kwargs["input_path"].as_posix() == "data/input/custom.csv"
        assert call_kwargs["from_db"] == "CHEMBL_ID"
        assert call_kwargs["to_db"] == "UniProtKB-Swiss-Prot"
        assert call_kwargs["seed_ids"] == ["CHEMBL1", "CHEMBL2"]
        assert result is mock_ds

    @patch("bioetl.composition.providers.registration.IDMappingDataSource")
    @patch("bioetl.composition.providers.registration.UniProtIDMappingClient")
    @patch("bioetl.composition.providers.registration._get_factories")
    def test_uses_defaults_when_api_and_filter_missing(
        self,
        mock_get_factories: MagicMock,
        mock_uniprot_client: MagicMock,
        mock_idmapping_data_source: MagicMock,
    ) -> None:
        mock_http_factory = MagicMock()
        mock_get_factories.return_value = (MagicMock(), mock_http_factory)
        mock_http_factory.create_for_provider.return_value = MagicMock()
        mock_uniprot_client.return_value = MagicMock()
        mock_ds = MagicMock()
        mock_idmapping_data_source.return_value = mock_ds

        source = SimpleNamespace(api=None, input_path=None)
        pipeline_config = SimpleNamespace(source=source)

        _create_uniprot_idmapping_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            filter_config=None,
        )

        assert (
            mock_uniprot_client.call_args.kwargs["base_url"]
            == "https://rest.uniprot.org"
        )
        call_kwargs = mock_idmapping_data_source.call_args.kwargs
        assert call_kwargs["input_path"].as_posix() == "data/input/target.csv"
        assert call_kwargs["from_db"] == "ChEMBL"
        assert call_kwargs["to_db"] == "UniProtKB"
        assert call_kwargs["seed_ids"] is None
