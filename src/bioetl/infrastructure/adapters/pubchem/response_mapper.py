"""Response mapping helpers for PubChem adapter fetch strategies."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord
    from bioetl.infrastructure.adapters.pubchem.entity_mapper import PubChemEntityMapper

__all__ = ["PubChemResponseMapper", "normalize_pubchem_results"]


def normalize_pubchem_results(results: object) -> list[object]:
    """Normalize pubchempy responses to a concrete list."""
    if isinstance(results, list):
        return results
    if isinstance(results, tuple):
        return list(results)
    return []


class PubChemResponseMapper:
    """Map normalized PubChem API objects into bronze records."""

    def __init__(self, mapper: PubChemEntityMapper) -> None:
        self._mapper = mapper

    def map_compounds(self, compounds: list[object]) -> list[BronzeRecord]:
        """Map normalized compound results."""
        return [self._mapper.compound_to_dict(compound) for compound in compounds]

    def map_substances(self, substances: list[object]) -> list[BronzeRecord]:
        """Map normalized substance results."""
        return [self._mapper.substance_to_dict(substance) for substance in substances]

    def map_assays(self, assays: list[object]) -> list[BronzeRecord]:
        """Map normalized assay results."""
        return [self._mapper.assay_to_dict(assay) for assay in assays]
