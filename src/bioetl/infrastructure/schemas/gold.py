"""Gold layer Pandera schemas for data validation.

Defines the Pandera DataFrameModels for various entities in the Gold layer.
Used for validating data quality before writing to the Gold layer.
"""

from typing import Optional
import pandera.pandas as pa
from pandera.typing import Series


class ChEMBLActivityGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Activity in Gold layer."""

    # Core identifiers
    activity_id: Series[str] = pa.Field(nullable=False)
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=False)

    # Values
    standard_type: Series[str] = pa.Field(nullable=True)
    standard_value: Series[float] = pa.Field(nullable=True)
    standard_units: Series[str] = pa.Field(nullable=True)
    pchembl_value: Series[float] = pa.Field(nullable=True, ge=0)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns


class PubChemCompoundGoldSchema(pa.DataFrameModel):
    """Schema for PubChem Compound in Gold layer."""

    cid: Series[str] = pa.Field(nullable=False)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[str] = pa.Field(nullable=True)
    canonical_smiles: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = False


class UniProtProteinGoldSchema(pa.DataFrameModel):
    """Schema for UniProt Protein in Gold layer."""

    accession: Series[str] = pa.Field(nullable=False)
    entry_name: Series[str] = pa.Field(nullable=True)
    protein_name: Series[str] = pa.Field(nullable=True)
    sequence_length: Series[int] = pa.Field(nullable=True, ge=0)

    class Config:
        strict = False


class PubMedPublicationGoldSchema(pa.DataFrameModel):
    """Schema for PubMed Publication in Gold layer."""

    pmid: Series[str] = pa.Field(nullable=False)
    article_title: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = False
