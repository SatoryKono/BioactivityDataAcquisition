"""Domain layer data contracts.

This package contains Pandera DataFrameModel schemas for data validation
at the Gold layer. Contracts define the structure and validation rules
for data as it moves through the ETL pipeline.

Subpackages:
    gold: Gold layer schemas organized by provider

Example usage:
    >>> from bioetl.domain.contracts import ChEMBLActivityGoldSchema
    >>> df = pd.read_parquet("data/gold/chembl_activity/")
    >>> ChEMBLActivityGoldSchema.validate(df)

    >>> from bioetl.domain.contracts.gold import chembl
    >>> chembl.ChEMBLActivityGoldSchema.validate(df)
"""

from __future__ import annotations

# Re-export all Gold schemas for convenience
from bioetl.domain.contracts.gold import (
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
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
from bioetl.domain.contracts.gold._base import DATE_REGEX

__all__ = [
    "DATE_REGEX",
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
    "SemanticScholarPublicationGoldSchema",
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
