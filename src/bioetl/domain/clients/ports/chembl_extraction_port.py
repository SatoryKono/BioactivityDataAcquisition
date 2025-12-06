"""ChEMBL extraction port definitions."""

from __future__ import annotations

from abc import ABC

from bioetl.domain.contracts import ExtractionServiceABC


class ChemblExtractionPort(ExtractionServiceABC, ABC):
    """Port contract for ChEMBL extraction services."""


__all__ = ["ChemblExtractionPort"]
