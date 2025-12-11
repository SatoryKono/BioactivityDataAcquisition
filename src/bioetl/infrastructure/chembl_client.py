"""Factories for constructing ChEMBL client stack.

Naming convention:
- create_*() - creates a new instance each time
- get_*() - returns singleton/cached instance
- build_*() - uses builder pattern
"""

from __future__ import annotations

from typing import Any

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.configs import ChemblSourceConfig
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.infrastructure.clients.chembl.factories import (
    create_chembl_client,
    create_chembl_extraction_service,
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
    return create_chembl_client(config, logger=logger, metrics=metrics)


def create_extraction_service(
    config: ChemblSourceConfig,
    *,
    client: DataClientABC | None = None,
    filter_enricher: FilterEnricherABC | None = None,
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

    return create_chembl_extraction_service(
        config,
        logger=logger,
        metrics=metrics,
        client=client,
        filter_enricher=filter_enricher,
    )
