"""Domain entities for BioETL.

Defines rich domain objects with invariants and business logic.
Implements part of the Domain Layer (RULES.md §1).

These entities are distinct from:
- DTOs/TypedDicts (used for serialization/transport)
- Infrastructure Schemas (PyArrow/Pandera used for validation)

Design Principles:
- Immutable (frozen dataclasses)
- Validated on construction (__post_init__)
- Pure Python (no external dependencies)
"""

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.chembl_activity import Activity, Assay
from bioetl.domain.entities.chembl_structures import (
    Document,
    Molecule,
    Target,
    TargetComponent,
)
from bioetl.domain.entities.pubchem import Compound
from bioetl.domain.entities.pubmed import Publication
from bioetl.domain.entities.uniprot import Protein

__all__ = [
    "Activity",
    "Assay",
    "BaseEntity",
    "Compound",
    "Document",
    "Molecule",
    "Protein",
    "Publication",
    "Target",
    "TargetComponent",
]
