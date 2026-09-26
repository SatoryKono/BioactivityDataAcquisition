"""Canonical UniProt controlled-vocabulary catalog for domain/runtime use."""

from __future__ import annotations

UNIPROT_ENTRY_TYPES: tuple[str, ...] = (
    "UniProtKB reviewed (Swiss-Prot)",
    "UniProtKB unreviewed (TrEMBL)",
)

UNIPROT_PROTEIN_FLAGS: tuple[str, ...] = (
    "Fragment",
    "Precursor",
    "Fragments",
)

UNIPROT_PROTEIN_EXISTENCE_LEVELS: tuple[str, ...] = (
    "Evidence at protein level",
    "Evidence at transcript level",
    "Inferred from homology",
    "Predicted",
    "Uncertain",
)

UNIPROT_MAPPING_STATUSES: tuple[str, ...] = (
    "found",
    "not_found",
    "error",
    "multiple",
)

UNIPROT_ENUM_CATALOG: dict[str, dict[str, tuple[str, ...]]] = {
    "protein": {
        "entry_types": UNIPROT_ENTRY_TYPES,
        "protein_flags": UNIPROT_PROTEIN_FLAGS,
        "protein_existence_levels": UNIPROT_PROTEIN_EXISTENCE_LEVELS,
    },
    "idmapping": {
        "mapping_statuses": UNIPROT_MAPPING_STATUSES,
    },
}

__all__ = [
    "UNIPROT_ENTRY_TYPES",
    "UNIPROT_ENUM_CATALOG",
    "UNIPROT_MAPPING_STATUSES",
    "UNIPROT_PROTEIN_EXISTENCE_LEVELS",
    "UNIPROT_PROTEIN_FLAGS",
]
