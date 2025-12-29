"""Domain entities for BioETL.

Defines rich domain objects with invariants and business logic.
Implements part of the Domain Layer (RULES.md §1).

These entities are distinct from:
- DTOs/TypedDicts (used for serialization/transport)
- Infrastructure Schemas (PyArrow/Pandera used for validation)

Design Principles:
- Immutable (frozen dataclasses with slots=True for memory efficiency)
- Validated on construction (__post_init__)
- Pure Python (no external dependencies)

Field Classification:
- REQUIRED: Fields validated in __post_init__ (must be non-None)
- API-OPTIONAL: Fields from external APIs (may be None)
- COMPUTED: Derived fields (calculated from other fields)

See base.py for RequiredEntityFields Protocol for type-safe required field checks.
"""

from bioetl.domain.entities.base import BaseEntity, RequiredEntityFields
from bioetl.domain.entities.chembl_activity import Activity, Assay
from bioetl.domain.entities.chembl_structures import (
    CellLine,
    Document,
    Molecule,
    Target,
    TargetComponent,
)
from bioetl.domain.entities.crossref import Work
from bioetl.domain.entities.pubchem import Compound
from bioetl.domain.entities.pubmed import Publication
from bioetl.domain.entities.uniprot import Protein

__all__ = [
    "Activity",
    "Assay",
    "BaseEntity",
    "CellLine",
    "Compound",
    "Document",
    "Molecule",
    "Protein",
    "Publication",
    "RequiredEntityFields",
    "Target",
    "TargetComponent",
    "Work",
]
