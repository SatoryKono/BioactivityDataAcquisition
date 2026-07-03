"""Pandera schema for UniProt Target entity.

Aligned with RULES.md v5.24 and UniProt REST API.
Split into sub-modules to comply with LOC limits.
"""

from __future__ import annotations

from bioetl.domain.schemas.uniprot._annotations import UniprotAnnotationSchema
from bioetl.domain.schemas.uniprot._core import (
    ENTRY_TYPES,
    PROTEIN_EXISTENCE_LEVELS,
    PROTEIN_FLAGS,
    UniprotCoreSchema,
)
from bioetl.domain.schemas.uniprot._features import UniprotFeatureSchema
from bioetl.domain.schemas.uniprot._xrefs import UniprotXrefSchema


class UniprotTargetSchema(
    UniprotCoreSchema,
    UniprotAnnotationSchema,
    UniprotXrefSchema,
    UniprotFeatureSchema,
):
    """UniProt Target validation schema for Silver layer.

    Represents a UniProtKB protein entry (Swiss-Prot or TrEMBL).
    Inherits fields from core, annotation, xref and feature sub-schemas.
    """

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = False
        coerce = True
        name = "UniprotTargetSchema"
        description = "UniProt Target Silver layer validation"


__all__ = [
    "ENTRY_TYPES",
    "PROTEIN_EXISTENCE_LEVELS",
    "PROTEIN_FLAGS",
    "UniprotTargetSchema",
]
