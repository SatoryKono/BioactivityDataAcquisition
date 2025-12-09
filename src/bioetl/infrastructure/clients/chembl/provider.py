"""ChEMBL provider components and registration."""

from __future__ import annotations

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.domain.providers import ProviderComponents, ProviderDefinition, ProviderId
from bioetl.domain.transform.contracts import (
    NormalizationConfigProviderProtocol,
    NormalizationServiceABC,
)
from bioetl.infrastructure.chembl_client import (
    create_client,
    create_extraction_service,
)
from bioetl.infrastructure.transform.factories import default_normalization_service


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
        field_provider: DefaultFieldProviderABC | None = None,
    ) -> ExtractionServiceABC:
        """Construct extraction service with optional prebuilt client."""
        return create_extraction_service(
            config, client=client, field_provider=field_provider
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
        return default_normalization_service(pipeline_config)


def register_chembl_provider() -> ProviderDefinition:
    """Create ChEMBL provider definition."""

    definition = ProviderDefinition(
        id=ProviderId.CHEMBL,
        config_type=ChemblSourceConfig,
        components=ChemblProviderComponentsFactory(),
        description="ChEMBL data provider",
    )
    return definition


__all__ = [
    "ChemblProviderComponentsFactory",
    "register_chembl_provider",
]
