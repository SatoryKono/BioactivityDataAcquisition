"""ChEMBL provider components and registration."""

from __future__ import annotations

from bioetl.application.services.chembl_extraction import ChemblExtractionServiceImpl
from bioetl.domain.normalization_service import ChemblNormalizationService
from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    get_provider,
    register_provider,
)
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.infrastructure.chembl_client import (
    create_client,
    create_extraction_service,
)
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.config.models import ChemblSourceConfig, PipelineConfig


class ChemblProviderComponents(
    ProviderComponents[
        ChemblDataClientABC,
        ChemblExtractionServiceImpl,
        ChemblNormalizationService,
        object,
    ]
):
    """Factory set for building ChEMBL provider components."""

    def create_client(self, config: ChemblSourceConfig) -> ChemblDataClientABC:
        return create_client(config)

    def create_extraction_service(
        self,
        config: ChemblSourceConfig,
        *,
        client: ChemblDataClientABC | None = None,
    ) -> ChemblExtractionServiceImpl:
        return create_extraction_service(config, client=client)

    def create_normalization_service(
        self,
        config: ChemblSourceConfig,
        *,
        client: ChemblDataClientABC | None = None,
        pipeline_config: PipelineConfig | None = None,
    ) -> ChemblNormalizationService:
        _ = client  # signature compatibility; normalization independent from client
        if pipeline_config is None:
            raise ValueError("PipelineConfig is required to build normalization service")
        return ChemblNormalizationService(pipeline_config)


def register_chembl_provider() -> ProviderDefinition:
    """Register ChEMBL provider in the global registry."""

    definition = ProviderDefinition(
        id=ProviderId.CHEMBL,
        config_type=ChemblSourceConfig,
        components=ChemblProviderComponents(),
        description="ChEMBL data provider",
    )
    try:
        register_provider(definition)
    except ProviderAlreadyRegisteredError:
        return get_provider(ProviderId.CHEMBL)
    return definition


__all__ = [
    "ChemblProviderComponents",
    "register_chembl_provider",
]
