"""Governed PubChem standardization vocabulary shared across domain owners."""

from __future__ import annotations

PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION = "pubchem-basic-v1"

PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES: tuple[str, ...] = (
    "standardized",
    "partial",
    "invalid",
    "missing_structure",
)

PUBCHEM_STANDARDIZATION_ENUM_CATALOG: dict[str, tuple[str, ...]] = {
    "chemical_standardization_statuses": PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES,
    "chemical_standardization_policy_versions": (
        PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    ),
}

__all__ = [
    "PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION",
    "PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES",
    "PUBCHEM_STANDARDIZATION_ENUM_CATALOG",
]
