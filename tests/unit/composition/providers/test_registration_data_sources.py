"""Unit tests for uncovered provider creator branches in registration module."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.providers.registration_biblio import (
    _create_crossref_data_source,
    _create_openalex_adapter_from_settings,
    _create_openalex_data_source,
    _create_pubmed_adapter_from_settings,
    _create_pubmed_data_source,
    _create_semanticscholar_data_source,
)
from bioetl.composition.providers.registration_bio import (
    _create_chembl_data_source,
    _create_pubchem_adapter,
    _create_uniprot_data_source,
    _create_uniprot_idmapping_data_source,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# Common mock target for the generic biblio helper
_BIBLIO_HTTP_DS = (
    "bioetl.composition.providers.registration_biblio._create_http_data_source"
)
_BIBLIO_BATCH = (
    "bioetl.composition.providers.registration_biblio._get_batch_size_from_config"
)


@pytest.mark.unit
class TestChemblPublicationTermBranch:
    """Covers publication_term wrapper branch in ChEMBL creator."""

    @patch("bioetl.composition.providers.registration_bio._wrap_with_filter")
    @patch("bioetl.composition.providers.registration_bio.PublicationTermDataSource")
    @patch("bioetl.composition.providers.registration_bio._get_adapter_config")
    def test_wraps_publication_term_adapter(
        self,
        mock_get_adapter_config: MagicMock,
        mock_publication_term_data_source: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        support = MagicMock()
        mock_get_adapter_config.return_value = MagicMock()
        mock_base_adapter = MagicMock(name="base_adapter")
        mock_wrapped_adapter = MagicMock(name="publication_term_wrapper")
        mock_filtered_adapter = MagicMock(name="filtered")
        support.create_adapter.return_value = mock_base_adapter
        mock_publication_term_data_source.return_value = mock_wrapped_adapter
        mock_wrap_with_filter.return_value = mock_filtered_adapter

        pipeline_config = MagicMock()
        pipeline_config.entity_type = "publication_term"
        pipeline_config.extraction_params = {}

        result = _create_chembl_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            assembly_support=support,
        )

        mock_publication_term_data_source.assert_called_once_with(mock_base_adapter)
        mock_wrap_with_filter.assert_called_once()
        assert result is mock_filtered_adapter


@pytest.mark.unit
class TestChemblTargetProteinClassificationBranch:
    """Covers snapshot-backed target protein classification registration."""

    @patch("bioetl.composition.providers.registration_bio._wrap_with_filter")
    @patch(
        "bioetl.composition.providers.registration_bio."
        "TargetProteinClassificationSnapshotDataSource"
    )
    @patch("bioetl.composition.providers.registration_bio.DeltaReader")
    def test_uses_snapshot_source_without_http_adapter(
        self,
        mock_delta_reader_cls: MagicMock,
        mock_snapshot_source_cls: MagicMock,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        support = MagicMock()
        logger = MagicMock()
        gold_path = Path("/tmp/bioetl-data") / "output" / "gold"
        settings = SimpleNamespace(gold_path=gold_path)
        pipeline_config = MagicMock()
        pipeline_config.entity_type = "target_protein_classification"
        pipeline_config.extraction_params = {
            "target_type": "SINGLE PROTEIN",
            "organism__isnull": "false",
            "tax_id__isnull": "false",
        }
        delta_reader = MagicMock(name="delta_reader")
        snapshot_source = MagicMock(name="snapshot_source")
        filtered_source = MagicMock(name="filtered_source")
        mock_delta_reader_cls.return_value = delta_reader
        mock_snapshot_source_cls.return_value = snapshot_source
        mock_wrap_with_filter.return_value = filtered_source

        result = _create_chembl_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            assembly_support=support,
        )

        assert result is filtered_source
        mock_delta_reader_cls.assert_called_once_with(
            base_path=gold_path,
            logger=logger,
        )
        mock_snapshot_source_cls.assert_called_once_with(
            delta_reader=delta_reader,
            logger=logger,
        )
        support.create_http_client.assert_not_called()
        support.create_adapter.assert_not_called()


@pytest.mark.unit
class TestPubChemCreatorGuard:
    """Covers logger guard and delegation in PubChem adapter creation."""

    def test_pubchem_adapter_requires_logger(self) -> None:
        with pytest.raises(ValueError, match="requires logger"):
            _create_pubchem_adapter(logger=None)

    @patch("bioetl.composition.providers.registration_bio.create_pubchem_adapter")
    def test_pubchem_adapter_delegates_to_factory(
        self,
        mock_create_pubchem_adapter: MagicMock,
    ) -> None:
        logger = MagicMock()
        metrics = MagicMock()
        adapter = MagicMock()
        mock_create_pubchem_adapter.return_value = adapter

        result = _create_pubchem_adapter(
            logger=logger,
            settings=MagicMock(),
            metrics=metrics,
            strict_error_handling=True,
        )

        mock_create_pubchem_adapter.assert_called_once()
        call_kwargs = mock_create_pubchem_adapter.call_args.kwargs
        assert call_kwargs["logger"] is logger
        assert call_kwargs["metrics"] is metrics
        assert call_kwargs["strict_error_handling"] is True
        assert result is adapter


@pytest.mark.unit
class TestCrossRefAndOpenAlexCreators:
    """Covers helper branches for CrossRef/OpenAlex providers."""

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_crossref_creator_uses_pipeline_email_and_batch_size(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 77
        mock_adapter = MagicMock()
        mock_create_http_ds.return_value = mock_adapter

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

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["mailto"] == "pipeline@example.org"
        assert call_kwargs["extra_kwargs"]["batch_size"] == 77
        assert call_kwargs["provider"] == "crossref"
        assert result is mock_adapter

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_crossref_creator_preserves_injected_assembly_support(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 77
        mock_create_http_ds.return_value = MagicMock()

        support = MagicMock(name="assembly_support")
        pipeline_config = MagicMock()
        pipeline_config.source.email = "pipeline@example.org"

        _create_crossref_data_source(
            settings=MagicMock(default_email="default@example.org"),
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            assembly_support=support,
        )

        assert mock_create_http_ds.call_args.kwargs["assembly_support"] is support

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_openalex_creator_uses_settings_email_fallback(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 55
        mock_adapter = MagicMock()
        mock_create_http_ds.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.openalex_api_key = MagicMock()
        settings.openalex_api_key.get_secret_value.return_value = (
            "settings-openalex-key"
        )
        pipeline_config = MagicMock()
        pipeline_config.source.email = ""
        pipeline_config.source.api_key = ""

        result = _create_openalex_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            metrics=MagicMock(),
            pipeline_name="openalex_publication",
        )

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["api_key"] == "settings-openalex-key"
        assert call_kwargs["extra_kwargs"]["mailto"] == "default@example.org"
        assert call_kwargs["extra_kwargs"]["batch_size"] == 55
        assert "settings" not in call_kwargs["extra_kwargs"]
        assert result is mock_adapter

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_openalex_creator_preserves_injected_assembly_support(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 55
        mock_create_http_ds.return_value = MagicMock()

        support = MagicMock(name="assembly_support")
        pipeline_config = MagicMock()
        pipeline_config.source.email = ""
        pipeline_config.source.api_key = ""
        settings = MagicMock(default_email="default@example.org")
        settings.openalex_api_key = None

        _create_openalex_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            assembly_support=support,
        )

        assert mock_create_http_ds.call_args.kwargs["assembly_support"] is support

    @patch("bioetl.composition.providers.registration_biblio.OpenAlexAdapter")
    def test_openalex_adapter_creator_uses_settings_email_fallback(
        self,
        mock_adapter_cls: MagicMock,
    ) -> None:
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter
        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.openalex_api_key = MagicMock()
        settings.openalex_api_key.get_secret_value.return_value = (
            "settings-openalex-key"
        )

        result = _create_openalex_adapter_from_settings(
            http_client=MagicMock(),
            logger=MagicMock(),
            settings=settings,
            batch_size=55,
        )

        mock_adapter_cls.assert_called_once()
        call_kwargs = mock_adapter_cls.call_args.kwargs
        assert call_kwargs["api_key"] == "settings-openalex-key"
        assert call_kwargs["mailto"] == "default@example.org"
        assert call_kwargs["batch_size"] == 55
        assert call_kwargs["fallback_fetch_service"] is not None
        assert result is mock_adapter

    @patch("bioetl.composition.providers.registration_biblio.PubMedAdapter")
    def test_pubmed_adapter_creator_uses_settings_fallbacks(
        self,
        mock_adapter_cls: MagicMock,
    ) -> None:
        mock_adapter = MagicMock()
        mock_adapter_cls.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.pubmed_api_key = MagicMock()
        settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

        result = _create_pubmed_adapter_from_settings(
            http_client=MagicMock(),
            logger=MagicMock(),
            settings=settings,
            batch_size=77,
        )

        mock_adapter_cls.assert_called_once()
        call_kwargs = mock_adapter_cls.call_args.kwargs
        assert call_kwargs["email"] == "default@example.org"
        assert call_kwargs["api_key"] == "settings-key"
        assert call_kwargs["batch_size"] == 77
        assert result is mock_adapter


@pytest.mark.unit
class TestPlaceholderResolution:
    """Covers ${ENV_VAR} placeholder resolution in source config overrides."""

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_crossref_mailto_placeholder_falls_back_to_settings(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 50
        mock_create_http_ds.return_value = MagicMock()

        settings = MagicMock()
        settings.default_email = "default@example.org"
        pipeline_config = MagicMock()
        pipeline_config.source.email = "${BIOETL_CROSSREF_EMAIL}"

        _create_crossref_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
        )

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["mailto"] == "default@example.org"

    @patch(_BIBLIO_HTTP_DS)
    def test_pubmed_placeholders_fallback_to_settings_when_env_missing(
        self,
        mock_create_http_ds: MagicMock,
    ) -> None:
        mock_create_http_ds.return_value = MagicMock()

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

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["email"] == "default@example.org"
        assert call_kwargs["extra_kwargs"]["api_key"] == "settings-key"


@pytest.mark.unit
class TestPubMedCreatorContracts:
    """Covers PubMed-specific creator precedence and passthrough contracts."""

    @patch(_BIBLIO_HTTP_DS)
    def test_pubmed_creator_prefers_pipeline_email_and_api_key_over_settings(
        self,
        mock_create_http_ds: MagicMock,
    ) -> None:
        mock_create_http_ds.return_value = MagicMock()

        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.pubmed_api_key = MagicMock()
        settings.pubmed_api_key.get_secret_value.return_value = "settings-key"

        pipeline_config = MagicMock()
        pipeline_config.source.email = "pipeline@example.org"
        pipeline_config.source.api_key = "pipeline-key"

        _create_pubmed_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
        )

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["email"] == "pipeline@example.org"
        assert call_kwargs["extra_kwargs"]["api_key"] == "pipeline-key"

    @patch(_BIBLIO_HTTP_DS)
    def test_pubmed_creator_forwards_filter_metrics_and_pipeline_name(
        self,
        mock_create_http_ds: MagicMock,
    ) -> None:
        mock_adapter = MagicMock()
        mock_create_http_ds.return_value = mock_adapter

        settings = MagicMock()
        settings.default_email = "default@example.org"
        settings.pubmed_api_key = None
        pipeline_config = MagicMock()
        pipeline_config.source.email = ""
        pipeline_config.source.api_key = ""
        filter_config = MagicMock(name="filter_config")
        metrics = MagicMock(name="metrics")

        result = _create_pubmed_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            filter_config=filter_config,
            metrics=metrics,
            pipeline_name="pubmed_publication",
        )

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["filter_config"] is filter_config
        assert call_kwargs["metrics"] is metrics
        assert call_kwargs["pipeline_name"] == "pubmed_publication"
        assert result is mock_adapter


@pytest.mark.unit
class TestSemanticScholarCreatorBranches:
    """Covers API key warning / non-warning branches."""

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_warns_when_api_key_missing(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 120
        mock_adapter = MagicMock()
        mock_create_http_ds.return_value = mock_adapter

        logger = MagicMock()
        settings = MagicMock()
        settings.semanticscholar_api_key = None

        result = _create_semanticscholar_data_source(
            settings=settings,
            pipeline_config=MagicMock(),
            logger=logger,
        )

        logger.warning.assert_called_once()
        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["api_key"] == ""
        assert result is mock_adapter

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_does_not_warn_when_api_key_present(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 100
        mock_create_http_ds.return_value = MagicMock()

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
        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["extra_kwargs"]["api_key"] == "secret"

    @patch(_BIBLIO_BATCH)
    @patch(_BIBLIO_HTTP_DS)
    def test_forwards_pipeline_name_and_batch_size(
        self,
        mock_create_http_ds: MagicMock,
        mock_get_batch_size: MagicMock,
    ) -> None:
        mock_get_batch_size.return_value = 100
        mock_create_http_ds.return_value = MagicMock()

        settings = MagicMock()
        settings.semanticscholar_api_key = MagicMock()
        settings.semanticscholar_api_key.get_secret_value.return_value = "secret"

        _create_semanticscholar_data_source(
            settings=settings,
            pipeline_config=MagicMock(),
            logger=MagicMock(),
            pipeline_name="semanticscholar_publication",
        )

        call_kwargs = mock_create_http_ds.call_args.kwargs
        assert call_kwargs["pipeline_name"] == "semanticscholar_publication"
        assert call_kwargs["extra_kwargs"]["batch_size"] == 100


@pytest.mark.unit
class TestUniProtIdMappingCreatorBranches:
    """Covers override/default and seed-id branches in ID mapping creator."""

    @patch("bioetl.composition.providers.registration_bio.IDMappingDataSource")
    @patch("bioetl.composition.providers.registration_bio.IDMappingCsvReaderAdapter")
    @patch("bioetl.composition.providers.registration_bio.UniProtIDMappingClient")
    def test_uses_api_overrides_and_seed_ids(
        self,
        mock_uniprot_client: MagicMock,
        mock_idmapping_reader_adapter: MagicMock,
        mock_idmapping_data_source: MagicMock,
    ) -> None:
        support = MagicMock()
        mock_http_client = MagicMock()
        support.create_http_client.return_value = mock_http_client
        mock_client = MagicMock()
        mock_uniprot_client.return_value = mock_client
        mock_reader = MagicMock()
        mock_idmapping_reader_adapter.return_value = mock_reader
        mock_ds = MagicMock()
        mock_idmapping_data_source.return_value = mock_ds

        source_api = SimpleNamespace(
            base_url="https://mirror.uniprot.test",
            from_db="CHEMBL_ID",
            to_db="UniProtKB-Swiss-Prot",
        )
        source = SimpleNamespace(api=source_api, input_path="data/input/custom.csv")
        pipeline_config = cast(PipelineYamlConfig, SimpleNamespace(source=source))
        filter_config = SimpleNamespace(direct_filter_ids=["CHEMBL1", "CHEMBL2"])
        logger = MagicMock()

        result = _create_uniprot_idmapping_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=filter_config,
            metrics=MagicMock(),
            assembly_support=support,
        )

        mock_idmapping_reader_adapter.assert_called_once_with(logger=logger)
        assert (
            mock_uniprot_client.call_args.kwargs["base_url"]
            == "https://mirror.uniprot.test"
        )
        call_kwargs = mock_idmapping_data_source.call_args.kwargs
        assert call_kwargs["id_source_reader"] is mock_reader
        assert call_kwargs["input_path"] == "data/input/custom.csv"
        assert call_kwargs["from_db"] == "CHEMBL_ID"
        assert call_kwargs["to_db"] == "UniProtKB-Swiss-Prot"
        assert call_kwargs["seed_ids"] == ["CHEMBL1", "CHEMBL2"]
        assert result is mock_ds

    @patch("bioetl.composition.providers.registration_bio.IDMappingDataSource")
    @patch("bioetl.composition.providers.registration_bio.IDMappingCsvReaderAdapter")
    @patch("bioetl.composition.providers.registration_bio.UniProtIDMappingClient")
    def test_uses_defaults_when_api_and_filter_missing(
        self,
        mock_uniprot_client: MagicMock,
        mock_idmapping_reader_adapter: MagicMock,
        mock_idmapping_data_source: MagicMock,
    ) -> None:
        support = MagicMock()
        support.create_http_client.return_value = MagicMock()
        mock_uniprot_client.return_value = MagicMock()
        mock_reader = MagicMock()
        mock_idmapping_reader_adapter.return_value = mock_reader
        mock_ds = MagicMock()
        mock_idmapping_data_source.return_value = mock_ds

        source = SimpleNamespace(api=None, input_path=None)
        pipeline_config = cast(PipelineYamlConfig, SimpleNamespace(source=source))
        logger = MagicMock()

        _create_uniprot_idmapping_data_source(
            settings=MagicMock(),
            pipeline_config=pipeline_config,
            logger=logger,
            filter_config=None,
            assembly_support=support,
        )

        mock_idmapping_reader_adapter.assert_called_once_with(logger=logger)
        assert (
            mock_uniprot_client.call_args.kwargs["base_url"]
            == "https://rest.uniprot.org"
        )
        call_kwargs = mock_idmapping_data_source.call_args.kwargs
        assert call_kwargs["id_source_reader"] is mock_reader
        assert call_kwargs["input_path"] == "data/input/target.csv"
        assert call_kwargs["from_db"] == "ChEMBL"
        assert call_kwargs["to_db"] == "UniProtKB"
        assert call_kwargs["seed_ids"] is None


@pytest.mark.unit
class TestUniProtProteinCreatorBranches:
    """Covers public/default and optional-key UniProt data-source wiring."""

    @patch("bioetl.composition.providers.registration_bio._wrap_with_filter")
    def test_uniprot_protein_runs_without_api_key(
        self,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        support = MagicMock()
        support.create_http_client.return_value = MagicMock()
        adapter = MagicMock(name="uniprot_adapter")
        support.create_adapter.return_value = adapter
        mock_wrap_with_filter.return_value = adapter

        settings = MagicMock()
        settings.uniprot_api_key = None
        settings.strict_error_handling = False
        source = SimpleNamespace(api=SimpleNamespace(base_url=None))
        pipeline_config = cast(PipelineYamlConfig, SimpleNamespace(source=source))
        logger = MagicMock()

        result = _create_uniprot_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=logger,
            assembly_support=support,
        )

        call_kwargs = support.create_adapter.call_args.kwargs
        assert call_kwargs["api_key"] is None
        assert call_kwargs["base_url"] == "https://rest.uniprot.org"
        assert result is adapter

    @patch("bioetl.composition.providers.registration_bio._wrap_with_filter")
    def test_uniprot_protein_forwards_optional_api_key(
        self,
        mock_wrap_with_filter: MagicMock,
    ) -> None:
        support = MagicMock()
        support.create_http_client.return_value = MagicMock()
        adapter = MagicMock(name="uniprot_adapter")
        support.create_adapter.return_value = adapter
        mock_wrap_with_filter.return_value = adapter

        settings = MagicMock()
        settings.uniprot_api_key = MagicMock()
        settings.uniprot_api_key.get_secret_value.return_value = "uniprot-secret"
        settings.strict_error_handling = True
        source = SimpleNamespace(
            api=SimpleNamespace(base_url="https://mirror.uniprot.test")
        )
        pipeline_config = cast(PipelineYamlConfig, SimpleNamespace(source=source))

        _create_uniprot_data_source(
            settings=settings,
            pipeline_config=pipeline_config,
            logger=MagicMock(),
            assembly_support=support,
        )

        call_kwargs = support.create_adapter.call_args.kwargs
        assert call_kwargs["api_key"] == "uniprot-secret"
        assert call_kwargs["base_url"] == "https://mirror.uniprot.test"
