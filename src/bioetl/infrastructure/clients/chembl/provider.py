"""ChEMBL provider components and registration."""

from __future__ import annotations

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig, HttpClientConfig
from bioetl.domain.observability.contracts import LoggingPortABC, MetricsPortABC
from bioetl.domain.ports.entity_models import EntityModelRegistryABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.infrastructure.chembl_client import (
    create_client,
    create_extraction_service,
)
from bioetl.infrastructure.transform.factories import create_normalization_service


class ChemblProviderComponentsFactory(
    ProviderComponents[
        DataClientABC,
        ExtractionServiceABC,
        NormalizationServiceABC,
        object,
    ]
):
    """Factory set for building ChEMBL provider components."""

    def create_client(self, config: ChemblSourceConfig) -> DataClientABC:
        """Build configured ChEMBL data client."""
        return create_client(config)

    def create_extraction_service(
        self,
        config: ChemblSourceConfig,
        *,
        client: DataClientABC | None = None,
        filter_enricher: FilterEnricherABC | None = None,
        logger: LoggingPortABC | None = None,
        metrics: MetricsPortABC | None = None,
    ) -> ExtractionServiceABC:
        """Construct extraction service with optional prebuilt client."""
        return create_extraction_service(
            config,
            client=client,
            filter_enricher=filter_enricher,
            logger=logger,
            metrics=metrics,
        )

    def create_normalization_service(
        self,
        config: ChemblSourceConfig,
        *,
        client: DataClientABC | None = None,
        pipeline_config: NormalizationConfigProviderProtocol | None = None,
    ) -> NormalizationServiceABC:
        """Create normalization service using pipeline configuration."""
        _ = client  # signature compatibility; normalization independent from client
        if pipeline_config is None:
            raise ValueError(
                (
                    "NormalizationConfigProviderProtocol is required to build "
                    "normalization service"
                )
            )
        return create_normalization_service(pipeline_config)

    def create_entity_model_registry(self) -> EntityModelRegistryABC:
        """Create provider-specific entity model registry."""
        from bioetl.infrastructure.chembl.model_registry import (
            get_chembl_model_registry,
        )

        return get_chembl_model_registry()


def register_chembl_provider(
    http: HttpClientConfig | None = None,
) -> ProviderDefinition:
    """Create ChEMBL provider definition."""
    definition = ProviderDefinition(
        id=ProviderId.CHEMBL,
        config_type=ChemblSourceConfig,
        components=ChemblProviderComponentsFactory(),
        description="ChEMBL data provider",
        http=http,
    )
    return definition


__all__ = [
    "ChemblProviderComponentsFactory",
    "register_chembl_provider",
]
