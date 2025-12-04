"""ChEMBL provider components and registration."""

from __future__ import annotations

from bioetl.application.services.chembl_extraction import ChemblExtractionService
from bioetl.core.provider_registry import (
    ProviderAlreadyRegisteredError,
    get_provider,
    register_provider,
)
from bioetl.core.providers import (
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)
from bioetl.infrastructure.chembl_client import (
    create_client,
    create_extraction_service,
)
from bioetl.infrastructure.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.config.models import ChemblSourceConfig


class ChemblProviderComponents(
    ProviderComponents[ChemblSourceConfig, ChemblDataClientABC, ChemblExtractionService]
):
    """Factory set for building ChEMBL provider components."""

    def create_client(self, config: ChemblSourceConfig) -> ChemblDataClientABC:
        return create_client(config)

    def create_extraction_service(
        self, client: ChemblDataClientABC, config: ChemblSourceConfig
    ) -> ChemblExtractionService:
        return create_extraction_service(config, client=client)


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
