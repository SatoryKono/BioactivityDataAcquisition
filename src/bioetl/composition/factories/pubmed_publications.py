# src/bioetl/composition/factories/pubmed_publications.py
from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
from bioetl.composition.factories.http_client_factory import HttpClientFactory
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter
from bioetl.infrastructure.schemas.silver import PUBMED_PUBLICATION_SCHEMA

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

class PubMedPublicationsPipelineFactory(BasePipelineFactory[PubMedPublicationsPipeline]):
    """Фабрика для создания пайплайна PubMed Publications."""

    pipeline_name = "pubmed_publications"
    pipeline_class = PubMedPublicationsPipeline
    silver_schema = PUBMED_PUBLICATION_SCHEMA

    @classmethod
    def create_data_source(
        cls,
        settings: Settings,
        pipeline_config: PipelineYamlConfig,
    ) -> DataSourcePort:
        """Создает источник данных PubMed."""
        # Use HttpClientFactory for centralized config
        http_client = HttpClientFactory.create_for_provider("pubmed", settings)

        # Determine email and API key for PubMed specific config
        # Note: HttpClientFactory already handles rate/capacity based on settings,
        # but PubMedAdapter also needs the API key for request params.

        configured_api_key = pipeline_config.source.api_key
        # Check if settings.pubmed_api_key is SecretStr and has a value
        settings_api_key_value = settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None

        # Prioritize api_key from pipeline config, then from settings
        api_key_to_use = configured_api_key if configured_api_key is not None else settings_api_key_value

        email_to_use = pipeline_config.source.email or settings.default_email

        return PubMedAdapter(
            http_client=http_client,
            email=email_to_use,
            api_key=api_key_to_use
        )

# Регистрация делает пайплайн доступным для запуска через CLI
PipelineRegistry.register(
    "pubmed_publications", PubMedPublicationsPipelineFactory, PUBMED_PUBLICATION_SCHEMA
)
