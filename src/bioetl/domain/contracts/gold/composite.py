"""Composite Gold layer data contracts facade."""

from __future__ import annotations

from bioetl.domain.contracts.gold.composite_bioassay import (
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeTargetGoldSchema,
    CompositeTargetGoldSchemaV31,
)
from bioetl.domain.contracts.gold.composite_molecule import CompositeMoleculeGoldSchema
from bioetl.domain.contracts.gold.composite_publication import (
    CompositePublicationGoldSchema,
)

__all__ = [
    "CompositeActivityGoldSchema",
    "CompositeAssayGoldSchema",
    "CompositeMoleculeGoldSchema",
    "CompositePublicationGoldSchema",
    "CompositeTargetGoldSchema",
    "CompositeTargetGoldSchemaV31",
]
