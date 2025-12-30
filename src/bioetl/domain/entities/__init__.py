"""Domain entities for BioETL.

Contains two categories of domain objects:

1. **Domain Entities** (dataclass): Rich domain objects with lineage fields
   - Validated on construction (__post_init__)
   - Include run_id, content_hash for data lineage

2. **DTO Models** (Pydantic): Type-safe data transfer objects
   - Use extra='forbid' to detect API changes early
   - frozen=True ensures immutability
   - Adapters return DTOs, transformers convert to Domain Entities

Implements part of the Domain Layer (RULES.md §1, §8.2).

Field Classification:
- REQUIRED: Fields validated on construction
- API-OPTIONAL: Fields from external APIs (may be None)
- COMPUTED: Derived fields (calculated from other fields)
"""

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import Bioactivity, BioactivityState

# ChEMBL DTOs (Pydantic)
from bioetl.domain.entities.chembl import (
    ActivityRecord,
    AssayRecord,
    CellLineRecord,
    DocumentRecord,
    MoleculeRecord,
    TargetComponentRecord,
    TargetRecord,
)

# ChEMBL Domain Entities (dataclass)
from bioetl.domain.entities.chembl_activity import Assay
from bioetl.domain.entities.chembl_compound_record import CompoundRecord
from bioetl.domain.entities.chembl_structures import (
    CellLine,
    Document,
    Molecule,
    Target,
    TargetComponent,
)

# CrossRef DTO + Entity
from bioetl.domain.entities.crossref import PublicationRecord, Work

# PubChem DTO + Entity
from bioetl.domain.entities.pubchem import Compound, PubChemCompoundRecord

# PubMed DTO + Entity
from bioetl.domain.entities.pubmed import ArticleRecord, Publication

# UniProt Entity
from bioetl.domain.entities.uniprot import Protein

__all__ = [
    "ActivityRecord",
    "ArticleRecord",
    "Assay",
    "AssayRecord",
    "BaseEntity",
    "Bioactivity",
    "BioactivityState",
    "CellLine",
    "CellLineRecord",
    "Compound",
    "CompoundRecord",
    "Document",
    "DocumentRecord",
    "Molecule",
    "MoleculeRecord",
    "Protein",
    "PubChemCompoundRecord",
    "Publication",
    "PublicationRecord",
    "Target",
    "TargetComponent",
    "TargetComponentRecord",
    "TargetRecord",
    "Work",
]
