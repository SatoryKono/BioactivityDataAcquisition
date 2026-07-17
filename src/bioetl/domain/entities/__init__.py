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

import functools
from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.entities.base import BaseEntity as BaseEntity
    from bioetl.domain.entities.bioactivity import (
        Bioactivity as Bioactivity,
    )
    from bioetl.domain.entities.bioactivity import (
        BioactivityState as BioactivityState,
    )

    # ChEMBL DTOs (Pydantic)
    from bioetl.domain.entities.chembl import (
        ActivityRecord as ActivityRecord,
    )
    from bioetl.domain.entities.chembl import (
        AssayRecord as AssayRecord,
    )
    from bioetl.domain.entities.chembl import (
        CellLineRecord as CellLineRecord,
    )
    from bioetl.domain.entities.chembl import (
        ChemblPublicationRecord as ChemblPublicationRecord,
    )
    from bioetl.domain.entities.chembl import (
        ChemblPublicationTermRecord as ChemblPublicationTermRecord,
    )
    from bioetl.domain.entities.chembl import (
        CompoundLinkRecord as CompoundLinkRecord,
    )
    from bioetl.domain.entities.chembl import (
        MoleculeRecord as MoleculeRecord,
    )
    from bioetl.domain.entities.chembl import (
        PublicationSimilarityRecord as PublicationSimilarityRecord,
    )
    from bioetl.domain.entities.chembl import (
        TargetComponentRecord as TargetComponentRecord,
    )
    from bioetl.domain.entities.chembl import (
        TargetRecord as TargetRecord,
    )
    from bioetl.domain.entities.chembl import (
        TissueRecord as TissueRecord,
    )

    # ChEMBL Domain Entities (dataclass)
    from bioetl.domain.entities.chembl_activity import Assay as Assay
    from bioetl.domain.entities.chembl_assay_parameters import (
        AssayParameters as AssayParameters,
    )
    from bioetl.domain.entities.chembl_compound_record import (
        CompoundRecord as CompoundRecord,
    )
    from bioetl.domain.entities.chembl_structures import (
        CellLine as CellLine,
    )
    from bioetl.domain.entities.chembl_structures import (
        ChemblPublication as ChemblPublication,
    )
    from bioetl.domain.entities.chembl_structures import (
        ChemblPublicationSimilarity as ChemblPublicationSimilarity,
    )
    from bioetl.domain.entities.chembl_structures import (
        ChemblPublicationTerm as ChemblPublicationTerm,
    )
    from bioetl.domain.entities.chembl_structures import (
        Molecule as Molecule,
    )
    from bioetl.domain.entities.chembl_structures import (
        ProteinClassification as ProteinClassification,
    )
    from bioetl.domain.entities.chembl_structures import (
        Target as Target,
    )
    from bioetl.domain.entities.chembl_structures import (
        TargetComponent as TargetComponent,
    )
    from bioetl.domain.entities.chembl_structures import (
        TargetProteinClassification as TargetProteinClassification,
    )
    from bioetl.domain.entities.chembl_subcellular_fraction import (
        SubcellularFraction as SubcellularFraction,
    )
    from bioetl.domain.entities.chembl_tissue import Tissue as Tissue

    # CrossRef DTO + Entity
    from bioetl.domain.entities.crossref import (
        CrossRefPublicationEntity as CrossRefPublicationEntity,
    )
    from bioetl.domain.entities.crossref import (
        PublicationRecord as PublicationRecord,
    )

    # OpenAlex Entity
    from bioetl.domain.entities.openalex import (
        OpenAlexPublicationEntity as OpenAlexPublicationEntity,
    )

    # PubChem DTO + Entity
    from bioetl.domain.entities.pubchem import (
        PubchemMolecule as PubchemMolecule,
    )
    from bioetl.domain.entities.pubchem import (
        PubchemMoleculeRecord as PubchemMoleculeRecord,
    )

    # Publication Base (for type hints in composite pipelines)
    from bioetl.domain.entities.publication_base import (
        PublicationEntityBase as PublicationEntityBase,
    )

    # PubMed DTO + Entity
    from bioetl.domain.entities.pubmed import (
        ArticleRecord as ArticleRecord,
    )
    from bioetl.domain.entities.pubmed import (
        PubMedPublicationEntity as PubMedPublicationEntity,
    )

    # Semantic Scholar Entity
    from bioetl.domain.entities.semanticscholar import (
        SemanticScholarPublicationEntity as SemanticScholarPublicationEntity,
    )

    # UniProt Entity
    from bioetl.domain.entities.uniprot import UniprotTarget as UniprotTarget


_ENTITY_IMPORTS = {
    "ActivityRecord": ("bioetl.domain.entities.chembl", "ActivityRecord"),
    "ArticleRecord": ("bioetl.domain.entities.pubmed", "ArticleRecord"),
    "Assay": ("bioetl.domain.entities.chembl_activity", "Assay"),
    "AssayParameters": (
        "bioetl.domain.entities.chembl_assay_parameters",
        "AssayParameters",
    ),
    "AssayRecord": ("bioetl.domain.entities.chembl", "AssayRecord"),
    "BaseEntity": ("bioetl.domain.entities.base", "BaseEntity"),
    "Bioactivity": ("bioetl.domain.entities.bioactivity", "Bioactivity"),
    "BioactivityState": ("bioetl.domain.entities.bioactivity", "BioactivityState"),
    "CellLine": ("bioetl.domain.entities.chembl_structures", "CellLine"),
    "CellLineRecord": ("bioetl.domain.entities.chembl", "CellLineRecord"),
    "ChemblPublication": (
        "bioetl.domain.entities.chembl_structures",
        "ChemblPublication",
    ),
    "ChemblPublicationRecord": (
        "bioetl.domain.entities.chembl",
        "ChemblPublicationRecord",
    ),
    "ChemblPublicationSimilarity": (
        "bioetl.domain.entities.chembl_structures",
        "ChemblPublicationSimilarity",
    ),
    "ChemblPublicationTerm": (
        "bioetl.domain.entities.chembl_structures",
        "ChemblPublicationTerm",
    ),
    "ChemblPublicationTermRecord": (
        "bioetl.domain.entities.chembl",
        "ChemblPublicationTermRecord",
    ),
    "CompoundLinkRecord": ("bioetl.domain.entities.chembl", "CompoundLinkRecord"),
    "CompoundRecord": (
        "bioetl.domain.entities.chembl_compound_record",
        "CompoundRecord",
    ),
    "CrossRefPublicationEntity": (
        "bioetl.domain.entities.crossref",
        "CrossRefPublicationEntity",
    ),
    "Molecule": ("bioetl.domain.entities.chembl_structures", "Molecule"),
    "MoleculeRecord": ("bioetl.domain.entities.chembl", "MoleculeRecord"),
    "OpenAlexPublicationEntity": (
        "bioetl.domain.entities.openalex",
        "OpenAlexPublicationEntity",
    ),
    "ProteinClassification": (
        "bioetl.domain.entities.chembl_structures",
        "ProteinClassification",
    ),
    "PubMedPublicationEntity": (
        "bioetl.domain.entities.pubmed",
        "PubMedPublicationEntity",
    ),
    "PubchemMolecule": ("bioetl.domain.entities.pubchem", "PubchemMolecule"),
    "PubchemMoleculeRecord": (
        "bioetl.domain.entities.pubchem",
        "PubchemMoleculeRecord",
    ),
    "PublicationEntityBase": (
        "bioetl.domain.entities.publication_base",
        "PublicationEntityBase",
    ),
    "PublicationRecord": ("bioetl.domain.entities.crossref", "PublicationRecord"),
    "PublicationSimilarityRecord": (
        "bioetl.domain.entities.chembl",
        "PublicationSimilarityRecord",
    ),
    "SemanticScholarPublicationEntity": (
        "bioetl.domain.entities.semanticscholar",
        "SemanticScholarPublicationEntity",
    ),
    "SubcellularFraction": (
        "bioetl.domain.entities.chembl_subcellular_fraction",
        "SubcellularFraction",
    ),
    "Target": ("bioetl.domain.entities.chembl_structures", "Target"),
    "TargetComponent": ("bioetl.domain.entities.chembl_structures", "TargetComponent"),
    "TargetComponentRecord": ("bioetl.domain.entities.chembl", "TargetComponentRecord"),
    "TargetProteinClassification": (
        "bioetl.domain.entities.chembl_structures",
        "TargetProteinClassification",
    ),
    "TargetRecord": ("bioetl.domain.entities.chembl", "TargetRecord"),
    "Tissue": ("bioetl.domain.entities.chembl_tissue", "Tissue"),
    "TissueRecord": ("bioetl.domain.entities.chembl", "TissueRecord"),
    "UniprotTarget": ("bioetl.domain.entities.uniprot", "UniprotTarget"),
}


@functools.lru_cache(maxsize=1)
def _get_entity_imports() -> dict[str, tuple[str, str]]:
    return _ENTITY_IMPORTS


__all__: list[str] = []  # Populated lazily on first access


def __getattr__(name: str) -> object:  # pragma: no cover
    if TYPE_CHECKING:
        raise AttributeError
    # Populate __all__ lazily on first access
    if not __all__:
        __all__.extend(_get_entity_imports().keys())

    entity_imports = _get_entity_imports()
    if name not in entity_imports:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attr_name = entity_imports[name]
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    # Ensure __all__ is populated before returning dir
    if not __all__:
        __all__.extend(_get_entity_imports().keys())
    return sorted(set(globals()) | set(__all__))
