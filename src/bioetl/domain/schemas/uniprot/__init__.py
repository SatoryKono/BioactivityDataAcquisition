"""Public UniProt schema seam."""

from __future__ import annotations

from bioetl.domain.schemas.uniprot.protein import (
    ENTRY_TYPES,
    PROTEIN_EXISTENCE_LEVELS,
    PROTEIN_FLAGS,
    UniprotTargetSchema,
)

__all__ = [
    "ENTRY_TYPES",
    "PROTEIN_EXISTENCE_LEVELS",
    "PROTEIN_FLAGS",
    "UniprotTargetSchema",
]
