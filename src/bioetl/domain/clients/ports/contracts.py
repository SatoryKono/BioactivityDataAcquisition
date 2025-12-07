"""ChEMBL extraction port definitions."""

from __future__ import annotations

from abc import ABC

from bioetl.domain.contracts import ExtractionServiceABC


class ChemblExtractionPortABC(ExtractionServiceABC, ABC):
    """ChEMBL extraction port contract.

    Public interface:
        - Delegates extraction lifecycle to :class:`ExtractionServiceABC` for ChEMBL entities.

    Localization: en.
    Default implementation: :func:`bioetl.infrastructure.clients.chembl.factories.default_chembl_extraction_service`.
    Concrete implementation: :class:`bioetl.infrastructure.clients.chembl.chembl_extraction_client_impl.ChemblExtractionClientImpl`.
    """


__all__ = ["ChemblExtractionPortABC"]
