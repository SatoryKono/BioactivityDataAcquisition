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

# Re-export all Gold schemas for convenient access:
# ChEMBL, Composite, CrossRef, OpenAlex, PubChem, PubMed,
# SemanticScholar, and UniProt schemas.
from bioetl.domain.contracts.gold import (
    DATE_REGEX,
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
    ChEMBLTissueGoldSchema,
    CompositeActivityGoldSchema,
    CompositeAssayGoldSchema,
    CompositeMoleculeGoldSchema,
    CompositePublicationGoldSchema,
    CompositeTargetGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
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
