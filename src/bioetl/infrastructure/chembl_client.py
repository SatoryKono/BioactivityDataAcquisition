"""Factories for constructing ChEMBL client stack."""

from __future__ import annotations

from bioetl.application.services.chembl_extraction import ChemblExtractionServiceImpl
from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_client,
    default_chembl_extraction_service,
)
from bioetl.infrastructure.config.models import ChemblSourceConfig

__all__ = ["create_client", "create_extraction_service"]


def create_client(config: ChemblSourceConfig) -> ChemblDataClientABC:
    """Create a fully configured ChEMBL client from source config."""

    return default_chembl_client(config)


def create_extraction_service(
    config: ChemblSourceConfig, *, client: ChemblDataClientABC | None = None
) -> ChemblExtractionServiceImpl:
    """Create extraction service using provided or default ChEMBL client."""

    resolved_client = client or create_client(config)
    return default_chembl_extraction_service(config, client=resolved_client)
