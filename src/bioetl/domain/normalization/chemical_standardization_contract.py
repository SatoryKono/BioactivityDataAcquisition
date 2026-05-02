"""Pure normalization contract for governed chemical standardization fields."""

from __future__ import annotations

from typing import Literal

from bioetl.domain.normalization._pubchem_standardization_catalog import (
    PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES,
)

ChemicalStandardizationStatus = Literal[
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
]

CHEMICAL_STANDARDIZATION_POLICY_VERSION = (
    PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION
)
CHEMICAL_STANDARDIZATION_STATUSES: tuple[ChemicalStandardizationStatus, ...] = tuple(
    PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES
)

__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ChemicalStandardizationStatus",
]
