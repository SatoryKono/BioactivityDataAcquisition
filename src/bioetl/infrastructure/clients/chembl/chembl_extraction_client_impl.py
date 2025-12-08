"""Chembl extraction port implementation."""

from __future__ import annotations

from bioetl.domain.clients.chembl.contracts import ChemblDataClientABC
from bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl import (
    ChemblExtractionServiceImpl,
)


class ChemblExtractionClientImpl(ChemblExtractionServiceImpl):
    """ChEMBL extraction client ready for injection."""

    def __init__(self, client: ChemblDataClientABC, *, batch_size: int = 1000) -> None:
        super().__init__(client=client, batch_size=batch_size)


__all__ = ["ChemblExtractionClientImpl"]
