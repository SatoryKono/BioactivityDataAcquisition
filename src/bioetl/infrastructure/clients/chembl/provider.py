"""ChEMBL provider components and registration."""

from __future__ import annotations

from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    get_provider,
    register_provider,
)
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.domain.transform.contracts import (
    NormalizationConfigProvider,
    NormalizationServiceABC,
)
from bioetl.domain.transform.factories import default_normalization_service
from bioetl.infrastructure.chembl_client import (
    create_client,
    create_extraction_service,
)
from bioetl.infrastructure.config.models import ChemblSourceConfig


class ChemblProviderComponents(
    ProviderComponents[
        ChemblDataClientABC,
        ExtractionServiceABC,
        NormalizationServiceABC,
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
    ) -> ExtractionServiceABC:
        return create_extraction_service(config, client=client)

    def create_normalization_service(
        self,
        config: ChemblSourceConfig,
        *,
        client: ChemblDataClientABC | None = None,
        pipeline_config: NormalizationConfigProvider | None = None,
    ) -> NormalizationServiceABC:
        _ = client  # signature compatibility; normalization independent from client
        if pipeline_config is None:
            raise ValueError(
                "NormalizationConfigProvider is required to build normalization service"
            )
        return default_normalization_service(pipeline_config)


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
