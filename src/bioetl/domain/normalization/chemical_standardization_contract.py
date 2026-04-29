"""Pure normalization contract for governed chemical standardization fields."""

from __future__ import annotations

from typing import Literal

ChemicalStandardizationStatus = Literal[
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
]

CHEMICAL_STANDARDIZATION_POLICY_VERSION = "pubchem-basic-v1"
CHEMICAL_STANDARDIZATION_STATUSES: tuple[ChemicalStandardizationStatus, ...] = (
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
)

__all__ = [
    "CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "CHEMICAL_STANDARDIZATION_STATUSES",
    "ChemicalStandardizationStatus",
]
