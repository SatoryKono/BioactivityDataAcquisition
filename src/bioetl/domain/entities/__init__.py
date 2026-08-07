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


_CHEMBL_MODULE = "bioetl.domain.entities.chembl"
_CHEMBL_STRUCTURES_MODULE = "bioetl.domain.entities.chembl_structures"
_CHEMBL_ACTIVITY_MODULE = "bioetl.domain.entities.chembl_activity"
_CHEMBL_ASSAY_PARAMETERS_MODULE = "bioetl.domain.entities.chembl_assay_parameters"

_ENTITY_IMPORTS = {
    "ActivityRecord": (_CHEMBL_MODULE, "ActivityRecord"),
    "ArticleRecord": ("bioetl.domain.entities.pubmed", "ArticleRecord"),
    "Assay": (_CHEMBL_ACTIVITY_MODULE, "Assay"),
    "AssayParameters": (
        _CHEMBL_ASSAY_PARAMETERS_MODULE,
        "AssayParameters",
    ),
    "AssayRecord": (_CHEMBL_MODULE, "AssayRecord"),
    "BaseEntity": ("bioetl.domain.entities.base", "BaseEntity"),
    "Bioactivity": ("bioetl.domain.entities.bioactivity", "Bioactivity"),
    "BioactivityState": ("bioetl.domain.entities.bioactivity", "BioactivityState"),
    "CellLine": (_CHEMBL_STRUCTURES_MODULE, "CellLine"),
    "CellLineRecord": (_CHEMBL_MODULE, "CellLineRecord"),
    "ChemblPublication": (
        _CHEMBL_STRUCTURES_MODULE,
        "ChemblPublication",
    ),
    "ChemblPublicationRecord": (
        _CHEMBL_MODULE,
        "ChemblPublicationRecord",
    ),
    "ChemblPublicationSimilarity": (
        _CHEMBL_STRUCTURES_MODULE,
        "ChemblPublicationSimilarity",
    ),
    "ChemblPublicationTerm": (
        _CHEMBL_STRUCTURES_MODULE,
        "ChemblPublicationTerm",
    ),
    "ChemblPublicationTermRecord": (
        _CHEMBL_MODULE,
        "ChemblPublicationTermRecord",
    ),
    "CompoundLinkRecord": (_CHEMBL_MODULE, "CompoundLinkRecord"),
    "CompoundRecord": (
        "bioetl.domain.entities.chembl_compound_record",
        "CompoundRecord",
    ),
    "CrossRefPublicationEntity": (
        "bioetl.domain.entities.crossref",
        "CrossRefPublicationEntity",
    ),
    "Molecule": (_CHEMBL_STRUCTURES_MODULE, "Molecule"),
    "MoleculeRecord": (_CHEMBL_MODULE, "MoleculeRecord"),
    "OpenAlexPublicationEntity": (
        "bioetl.domain.entities.openalex",
        "OpenAlexPublicationEntity",
    ),
    "LOOKUP_METHODS": (
        "bioetl.domain.entities.openalex",
        "LOOKUP_METHODS",
    ),
    "ProteinClassification": (
        _CHEMBL_STRUCTURES_MODULE,
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
        _CHEMBL_MODULE,
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
    "Target": (_CHEMBL_STRUCTURES_MODULE, "Target"),
    "TargetComponent": (_CHEMBL_STRUCTURES_MODULE, "TargetComponent"),
    "TargetComponentRecord": (_CHEMBL_MODULE, "TargetComponentRecord"),
    "TargetProteinClassification": (
        _CHEMBL_STRUCTURES_MODULE,
        "TargetProteinClassification",
    ),
    "TargetRecord": (_CHEMBL_MODULE, "TargetRecord"),
    "Tissue": ("bioetl.domain.entities.chembl_tissue", "Tissue"),
    "TissueRecord": (_CHEMBL_MODULE, "TissueRecord"),
    "UniprotTarget": ("bioetl.domain.entities.uniprot", "UniprotTarget"),
}


@functools.lru_cache(maxsize=1)
def _get_entity_imports() -> dict[str, tuple[str, str]]:
    return _ENTITY_IMPORTS


__all__: list[str] = []  # Populated lazily on first access


def __getattr__(name: str) -> object:  # pragma: no cover
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
