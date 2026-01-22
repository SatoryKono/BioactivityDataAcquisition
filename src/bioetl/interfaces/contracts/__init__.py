"""Data contracts for BioETL Gold layer.

DEPRECATED: This module re-exports schemas from bioetl.domain.contracts for
backward compatibility. New code should import from bioetl.domain.contracts.

This package provides Pandera DataFrameModel schemas for Gold layer validation.
Schemas are independent of pipeline implementations and can be imported by
data consumers (analysts, downstream applications) for validation and documentation.

Usage for analysts:
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

# Re-export all Gold schemas from domain.contracts for backward compatibility
from bioetl.domain.contracts.gold import (
    # ChEMBL schemas
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
    # CrossRef schemas
    CrossRefPublicationGoldSchema,
    # OpenAlex schemas
    OpenAlexPublicationGoldSchema,
    # PubChem schemas
    PubChemCompoundGoldSchema,
    # PubMed schemas
    PubMedPublicationGoldSchema,
    # SemanticScholar schemas
    SemanticScholarPublicationGoldSchema,
    # UniProt schemas
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
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
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
