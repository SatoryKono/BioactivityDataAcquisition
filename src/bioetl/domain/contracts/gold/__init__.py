"""Gold layer data contracts organized by provider.

This package contains Pandera DataFrameModel schemas for Gold layer validation,
organized by data provider for easy navigation.

Submodules:
    chembl: ChEMBL bioactivity database schemas
    pubchem: PubChem compound schemas
    uniprot: UniProt protein database schemas
    publications: Cross-provider publication schemas (PubMed, CrossRef, OpenAlex, SemanticScholar)
    composite: Composite pipeline schemas (merged multi-source entities)

Example usage:
    >>> from bioetl.domain.contracts.gold import chembl
    >>> df = pd.read_parquet("data/gold/chembl_activity/")
    >>> chembl.ChEMBLActivityGoldSchema.validate(df)

    >>> from bioetl.domain.contracts.gold.publications import PubMedPublicationGoldSchema
    >>> PubMedPublicationGoldSchema.validate(pubmed_df)

    >>> from bioetl.domain.contracts.gold.composite import CompositePublicationGoldSchema
    >>> CompositePublicationGoldSchema.validate(composite_df)
"""

from __future__ import annotations

# Import all schemas for flat namespace access
from bioetl.domain.contracts.gold._base import DATE_REGEX
from bioetl.domain.contracts.gold.chembl import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTargetProteinClassificationGoldSchema,
    ChEMBLTissueGoldSchema,
)
from bioetl.domain.contracts.gold.composite import (
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CompositeTargetGoldSchema,
)
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from bioetl.domain.contracts.gold.publications import (
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
)
from bioetl.domain.contracts.gold.uniprot import (
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

__all__ = [
    "DATE_REGEX",
    "ChEMBLActivityGoldSchema",
    "ChEMBLAssayGoldSchema",
    "ChEMBLAssayParametersGoldSchema",
    "ChEMBLCellLineGoldSchema",
    "ChEMBLCompoundRecordGoldSchema",
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
    "ChEMBLPublicationGoldSchema",
    "ChEMBLPublicationSimilarityGoldSchema",
    "ChEMBLPublicationTermGoldSchema",
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetProteinClassificationGoldSchema",
    "ChEMBLTissueGoldSchema",
    "CompositeActivityGoldSchema",
    "CompositeAssayGoldSchema",
    "CompositeMoleculeGoldSchema",
    "CompositePublicationGoldSchema",
    "CompositeTargetGoldSchema",
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubChemCompoundGoldSchema",
    "PubMedPublicationGoldSchema",
    "SemanticScholarPublicationGoldSchema",
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
