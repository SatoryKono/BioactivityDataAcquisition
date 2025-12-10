"""Factories for constructing ChEMBL client stack."""

from __future__ import annotations

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.infrastructure.clients.chembl.factories import (
    default_chembl_client,
    default_chembl_extraction_service,
)

__all__ = ["create_client", "create_extraction_service"]


def create_client(
    config: ChemblSourceConfig,
    *,
    logger: Any | None = None,
    metrics: Any | None = None,
) -> DataClientABC:
    """Create a fully configured ChEMBL client from source config."""

    if logger is None or metrics is None:
        raise ValueError("logger and metrics are required")
    return default_chembl_client(config, logger=logger, metrics=metrics)


def create_extraction_service(
    config: ChemblSourceConfig,
    *,
    client: DataClientABC | None = None,
    field_provider: DefaultFieldProviderABC | None = None,
    logger: Any | None = None,
    metrics: Any | None = None,
) -> ExtractionServiceABC:
    """Create extraction service using provided or default ChEMBL client."""

    if client is None:
        if logger is None or metrics is None:
            raise ValueError(
                "logger and metrics are required when client is not provided"
            )
        client = create_client(config, logger=logger, metrics=metrics)

    return default_chembl_extraction_service(
        config,
        logger=logger,
        metrics=metrics,
        client=client,
        field_provider=field_provider,
    )
