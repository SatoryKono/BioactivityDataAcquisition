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

.. versionchanged:: 2.0.0
    Entity Naming Unification for Ubiquitous Language alignment:
    - ChemblPublication (canonical) replaces Document (deprecated alias)
    - PubchemMolecule (canonical) replaces Compound (deprecated alias)
    - UniprotTarget (canonical) replaces Protein (deprecated alias)
    Deprecated aliases remain for backward compatibility.
"""

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import Bioactivity, BioactivityState

# ChEMBL DTOs (Pydantic)
from bioetl.domain.entities.chembl import (
    ActivityRecord,
    AssayRecord,
    CellLineRecord,
    DocumentRecord,
    DocumentTermRecord,
    MoleculeRecord,
    TargetComponentRecord,
    TargetRecord,
)

# ChEMBL Domain Entities (dataclass)
from bioetl.domain.entities.chembl_activity import Assay
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.entities.chembl_compound_record import CompoundRecord
from bioetl.domain.entities.chembl_structures import (
    CellLine,
    ChemblPublication,  # Canonical name (v2.0)
    Document,  # Deprecated alias → ChemblPublication
    DocumentSimilarity,
    DocumentTerm,
    Molecule,
    ProteinClassification,
    Target,
    TargetComponent,
)

# CrossRef DTO + Entity
from bioetl.domain.entities.crossref import PublicationEntity, PublicationRecord

# PubChem DTO + Entity
from bioetl.domain.entities.pubchem import (
    Compound,  # Deprecated alias → PubchemMolecule
    PubChemCompoundRecord,
    PubchemMolecule,  # Canonical name (v2.0)
)

# PubMed DTO + Entity
from bioetl.domain.entities.pubmed import ArticleRecord, Publication

# Semantic Scholar Entity
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity

# UniProt Entity
from bioetl.domain.entities.uniprot import (
    Protein,  # Deprecated alias → UniprotTarget
    UniprotTarget,  # Canonical name (v2.0)
)

__all__ = [
    "ActivityRecord",
    "ArticleRecord",
    "Assay",
    "AssayParameters",
    "AssayRecord",
    "BaseEntity",
    "Bioactivity",
    "BioactivityState",
    "CellLine",
    "CellLineRecord",
    "ChemblPublication",  # Canonical (v2.0)
    "Compound",  # Deprecated → PubchemMolecule
    "CompoundRecord",
    "Document",  # Deprecated → ChemblPublication
    "DocumentRecord",
    "DocumentSimilarity",
    "DocumentTerm",
    "DocumentTermRecord",
    "Molecule",
    "MoleculeRecord",
    "Protein",  # Deprecated → UniprotTarget
    "ProteinClassification",
    "PubChemCompoundRecord",
    "PubchemMolecule",  # Canonical (v2.0)
    "Publication",
    "PublicationEntity",
    "PublicationRecord",
    "SemanticScholarPublicationEntity",
    "Target",
    "TargetComponent",
    "TargetComponentRecord",
    "TargetRecord",
    "UniprotTarget",  # Canonical (v2.0)
]
