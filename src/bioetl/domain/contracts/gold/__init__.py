"""Gold layer data contracts organized by provider.

This package contains Pandera DataFrameModel schemas for Gold layer validation,
organized by data provider for easy navigation.

Submodules:
    chembl: ChEMBL bioactivity database schemas
    pubchem: PubChem compound schemas
    uniprot: UniProt protein database schemas
    publications: Cross-provider publication schemas (PubMed, CrossRef, OpenAlex, SemanticScholar)

Example usage:
    >>> from bioetl.domain.contracts.gold import chembl
    >>> df = pd.read_parquet("data/gold/chembl_activity/")
    >>> chembl.ChEMBLActivityGoldSchema.validate(df)

    >>> from bioetl.domain.contracts.gold.publications import PubMedPublicationGoldSchema
    >>> PubMedPublicationGoldSchema.validate(pubmed_df)
"""

from __future__ import annotations

# Import all schemas for flat namespace access
from bioetl.domain.contracts.gold.chembl import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLDocumentGoldSchema,
    ChEMBLDocumentSimilarityGoldSchema,
    ChEMBLDocumentTermGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
)
from bioetl.domain.contracts.gold.pubchem import PubChemCompoundGoldSchema
from bioetl.domain.contracts.gold.publication_base import PublicationGoldBaseSchema
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
    "ChEMBLActivityGoldSchema",
    "ChEMBLAssayGoldSchema",
    "ChEMBLAssayParametersGoldSchema",
    "ChEMBLCellLineGoldSchema",
    "ChEMBLCompoundRecordGoldSchema",
    "ChEMBLDocumentGoldSchema",
    "ChEMBLDocumentSimilarityGoldSchema",
    "ChEMBLDocumentTermGoldSchema",
    "ChEMBLMoleculeGoldSchema",
    "ChEMBLProteinClassGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "CrossRefPublicationGoldSchema",
    "OpenAlexPublicationGoldSchema",
    "PubChemCompoundGoldSchema",
    "PubMedPublicationGoldSchema",
    "PublicationGoldBaseSchema",
    "SemanticScholarPublicationGoldSchema",
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
