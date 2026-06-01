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

from __future__ import annotations

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.bioactivity import Bioactivity, BioactivityState

# ChEMBL DTOs (Pydantic)
from bioetl.domain.entities.chembl import (
    ActivityRecord,
    AssayRecord,
    CellLineRecord,
    ChemblPublicationRecord,
    ChemblPublicationTermRecord,
    CompoundLinkRecord,
    MoleculeRecord,
    PublicationSimilarityRecord,
    TargetComponentRecord,
    TargetRecord,
    TissueRecord,
)

# ChEMBL Domain Entities (dataclass)
from bioetl.domain.entities.chembl_activity import Assay
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.entities.chembl_compound_record import CompoundRecord
from bioetl.domain.entities.chembl_structures import (
    CellLine,
    ChemblPublication,
    ChemblPublicationSimilarity,
    ChemblPublicationTerm,
    Molecule,
    ProteinClassification,
    Target,
    TargetComponent,
    TargetProteinClassification,
)
from bioetl.domain.entities.chembl_subcellular_fraction import SubcellularFraction
from bioetl.domain.entities.chembl_tissue import Tissue

# CrossRef DTO + Entity
from bioetl.domain.entities.crossref import (
    CrossRefPublicationEntity,
    PublicationRecord,
)

# OpenAlex Entity
from bioetl.domain.entities.openalex import OpenAlexPublicationEntity

# PubChem DTO + Entity
from bioetl.domain.entities.pubchem import (
    PubchemMolecule,
    PubchemMoleculeRecord,
)

# Publication Base (for type hints in composite pipelines)
from bioetl.domain.entities.publication_base import PublicationEntityBase

# PubMed DTO + Entity
from bioetl.domain.entities.pubmed import (
    ArticleRecord,
    PubMedPublicationEntity,
)

# Semantic Scholar Entity
from bioetl.domain.entities.semanticscholar import SemanticScholarPublicationEntity

# UniProt Entity
from bioetl.domain.entities.uniprot import UniprotTarget

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
    "ChemblPublication",
    "ChemblPublicationRecord",
    "ChemblPublicationSimilarity",
    "ChemblPublicationTerm",
    "ChemblPublicationTermRecord",
    "CompoundLinkRecord",
    "CompoundRecord",  # ChEMBL compound_record (molecule-document link)
    "CrossRefPublicationEntity",
    "Molecule",
    "MoleculeRecord",
    "OpenAlexPublicationEntity",
    "ProteinClassification",
    "PubMedPublicationEntity",
    "PubchemMolecule",
    "PubchemMoleculeRecord",
    "PublicationEntityBase",
    "PublicationRecord",
    "PublicationSimilarityRecord",
    "SemanticScholarPublicationEntity",
    "SubcellularFraction",
    "Target",
    "TargetComponent",
    "TargetComponentRecord",
    "TargetProteinClassification",
    "TargetRecord",
    "Tissue",
    "TissueRecord",
    "UniprotTarget",
]
