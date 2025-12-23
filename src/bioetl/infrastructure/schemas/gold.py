"""Gold layer Pandera schemas for data validation.

Defines the Pandera DataFrameModels for various entities in the Gold layer.
Used for validating data quality before writing to the Gold layer.
"""

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
    """Schema for PubMed Publication in Gold layer.

    Fields match Publication entity from domain/entities.py.
    """

    pmid: Series[str] = pa.Field(nullable=False)
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)

    class Config:
        strict = False


class ChEMBLAssayGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Assay in Gold layer.

    Validated fields for high-quality assay data export.
    """

    # Core identifiers
    assay_chembl_id: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=True)
    document_chembl_id: Series[str] = pa.Field(nullable=True)

    # Assay type
    assay_type: Series[str] = pa.Field(nullable=False)
    assay_type_description: Series[str] = pa.Field(nullable=True)

    # BAO annotations
    bao_format: Series[str] = pa.Field(nullable=True)
    bao_label: Series[str] = pa.Field(nullable=True)

    # Quality indicators
    confidence_score: Series[int] = pa.Field(nullable=True, ge=0, le=9)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns


class ChEMBLTargetGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target in Gold layer.

    Validated fields for high-quality target data export.
    """

    # Primary identifier
    target_chembl_id: Series[str] = pa.Field(nullable=False)

    # Key metadata
    pref_name: Series[str] = pa.Field(nullable=True)
    target_type: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
    protein_classifications: Series[str] = pa.Field(nullable=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns


class ChEMBLTargetComponentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target Component in Gold layer.

    Validated fields for high-quality target component data export.
    """

    # Primary identifier
    component_id: Series[int] = pa.Field(nullable=False)

    # Key metadata
    accession: Series[str] = pa.Field(nullable=True)
    component_type: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
    protein_classifications: Series[str] = pa.Field(nullable=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns


class ChEMBLDocumentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document in Gold layer.

    Validated fields for high-quality document data export.
    """

    # Primary identifier
    document_chembl_id: Series[str] = pa.Field(nullable=False)

    # Key metadata
    title: Series[str] = pa.Field(nullable=True)
    doc_type: Series[str] = pa.Field(nullable=True)
    year: Series[float] = pa.Field(nullable=True, ge=1800, le=2100, coerce=True)

    # External identifiers (float due to pandas NaN handling)
    pubmed_id: Series[float] = pa.Field(nullable=True, coerce=True)
    doi: Series[str] = pa.Field(nullable=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns


class ChEMBLMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Molecule in Gold layer.

    Validated fields for high-quality molecule data export.
    """

    # Primary identifier
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)

    # Key metadata
    pref_name: Series[str] = pa.Field(nullable=True)
    molecule_type: Series[str] = pa.Field(nullable=True)
    max_phase: Series[float] = pa.Field(nullable=True, ge=0, le=4, coerce=True)

    # Flags
    oral: Series[bool] = pa.Field(nullable=True)
    therapeutic_flag: Series[bool] = pa.Field(nullable=True)
    withdrawn_flag: Series[bool] = pa.Field(nullable=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        strict = False  # Allow extra columns
