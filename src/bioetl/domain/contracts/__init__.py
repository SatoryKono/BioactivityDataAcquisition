"""Data contracts for BioETL Gold layer.

This package provides Pandera DataFrameModel schemas for Gold layer validation.
Schemas are part of the domain layer and can be imported by any layer for
validation and documentation.

Usage:
    >>> from bioetl.domain.contracts import ChEMBLActivityGoldSchema
    >>> import pandas as pd
    >>> df = pd.read_parquet("data/gold/chembl_activity/")
    >>> ChEMBLActivityGoldSchema.validate(df)

    # Or import by provider:
    >>> from bioetl.domain.contracts.gold import chembl
    >>> chembl.ChEMBLActivityGoldSchema.validate(df)

Available schemas by provider:
    - ChEMBL: Activity, Assay, Target, Molecule, etc.
    - PubChem: Compound
    - UniProt: Protein, IDMapping
    - PubMed: Publication
    - CrossRef: Publication
    - OpenAlex: Publication
    - SemanticScholar: Publication

See also:
    - docs/03-data-contracts/ for detailed schema documentation
    - ADR-018 for Gold strict validation rationale
"""

from __future__ import annotations

# Re-export all Gold schemas for convenient access
from bioetl.domain.contracts.gold import (  # ChEMBL schemas; Composite schemas; CrossRef schemas; OpenAlex schemas; PubChem schemas; PubMed schemas; SemanticScholar schemas; UniProt schemas
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
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)

# Utilities
from bioetl.domain.contracts.gold._base import DATE_REGEX

__all__ = [
    # Utilities
    "DATE_REGEX",
    # ChEMBL
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
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTissueGoldSchema",
    # Composite
    "CompositeMoleculeGoldSchema",
    "CompositePublicationGoldSchema",
    # CrossRef
    "CrossRefPublicationGoldSchema",
    # OpenAlex
    "OpenAlexPublicationGoldSchema",
    # PubChem
    "PubChemCompoundGoldSchema",
    # PubMed
    "PubMedPublicationGoldSchema",
    # SemanticScholar
    "SemanticScholarPublicationGoldSchema",
    # UniProt
    "UniProtIDMappingGoldSchema",
    "UniProtProteinGoldSchema",
]
