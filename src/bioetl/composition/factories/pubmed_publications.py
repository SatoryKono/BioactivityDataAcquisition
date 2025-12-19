# src/bioetl/composition/factories/pubmed_publications.py
from __future__ import annotations
from typing import TYPE_CHECKING

from bioetl.application.pipelines.pubmed.publications import PubMedPublicationsPipeline
from bioetl.application.registry import PipelineRegistry
from bioetl.infrastructure.adapters.pubmed.pubmed_client import PubMedAdapter
from bioetl.infrastructure.adapters.http.circuit_breaker import CircuitBreaker
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucket
from bioetl.composition.factories.base_pipeline_factory import BasePipelineFactory
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
        # NCBI рекомендует 3 запроса в секунду без API ключа, 10 с ключом.
        # Используем значение из pipeline_config.source или из settings.
        configured_api_key = pipeline_config.source.api_key
        # Check if settings.pubmed_api_key is SecretStr and has a value
        settings_api_key_value = settings.pubmed_api_key.get_secret_value() if settings.pubmed_api_key else None
        
        # Prioritize api_key from pipeline config, then from settings
        api_key_to_use = configured_api_key if configured_api_key is not None else settings_api_key_value

        rate = 10.0 if api_key_to_use else 3.0
        
        http_client = UnifiedHTTPClient(
            TokenBucket(rate=rate, capacity=rate * 2),
            CircuitBreaker(provider="pubmed")
        )

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
