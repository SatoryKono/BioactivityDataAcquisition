"""Gold layer Pandera schemas for data validation.

Defines the Pandera DataFrameModels for various entities in the Gold layer.
Used for validating data quality before writing to the Gold layer.
"""

from __future__ import annotations

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
    standard_value: Series[float] = pa.Field(nullable=True, coerce=True)
    standard_units: Series[str] = pa.Field(nullable=True)
    pchembl_value: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra columns


class PubChemCompoundGoldSchema(pa.DataFrameModel):
    """Schema for PubChem Compound in Gold layer."""

    cid: Series[str] = pa.Field(nullable=False)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[str] = pa.Field(nullable=True)
    canonical_smiles: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera configuration."""

        strict = False


class UniProtProteinGoldSchema(pa.DataFrameModel):
    """Schema for UniProt Protein in Gold layer."""

    accession: Series[str] = pa.Field(nullable=False)
    entry_name: Series[str] = pa.Field(nullable=True)
    protein_name: Series[str] = pa.Field(nullable=True)
    sequence_length: Series[int] = pa.Field(nullable=True, ge=0, coerce=True)

    class Config:
        """Pandera configuration."""

        strict = False


class PubMedPublicationGoldSchema(pa.DataFrameModel):
    """Schema for PubMed Publication in Gold layer.

    Fields match Publication entity from domain/entities.py.
    See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
    """

    # Primary identifiers
    pmid: Series[str] = pa.Field(nullable=False)
    doi: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)

    # Title and abstract
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)

    # Journal information
    journal: Series[str] = pa.Field(nullable=True)
    journal_abbrev: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    pages: Series[str] = pa.Field(nullable=True)

    # Dates
    pub_date: Series[str] = pa.Field(nullable=True)
    pub_year: Series[float] = pa.Field(nullable=True, coerce=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)
    accepted_date: Series[str] = pa.Field(nullable=True)
    received_date: Series[str] = pa.Field(nullable=True)
    revised_date: Series[str] = pa.Field(nullable=True)
    epub_date: Series[str] = pa.Field(nullable=True)

    # Additional metadata
    language: Series[str] = pa.Field(nullable=True)
    country: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera configuration."""

        strict = False  # Allow extra columns (authors, keywords, mesh_terms, etc.)


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
    confidence_score: Series[int] = pa.Field(nullable=True, ge=0, le=9, coerce=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera configuration."""

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
    # Note: protein_classifications not available in /target endpoint
    # Use ChEMBLTargetComponentGoldSchema for protein classification data

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera configuration."""

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
        """Pandera configuration."""

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
        """Pandera configuration."""

        strict = False  # Allow extra columns


class ChEMBLMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Molecule in Gold layer.

    Flat fields only - no JSON strings.
    JSON fields (molecule_hierarchy, molecule_properties, molecule_structures,
    molecule_synonyms, cross_references, atc_classifications) are excluded
    from Gold and retained only in Silver for forensic purposes.
    """

    # Primary identifier
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)

    # Core metadata
    pref_name: Series[str] = pa.Field(nullable=True)
    molecule_type: Series[str] = pa.Field(nullable=True)
    structure_type: Series[str] = pa.Field(nullable=True)
    max_phase: Series[float] = pa.Field(nullable=True, ge=0, le=4, coerce=True)
    first_approval: Series[float] = pa.Field(nullable=True, coerce=True)

    # Administration flags
    oral: Series[bool] = pa.Field(nullable=True)
    parenteral: Series[bool] = pa.Field(nullable=True)
    topical: Series[bool] = pa.Field(nullable=True)

    # Status flags
    therapeutic_flag: Series[bool] = pa.Field(nullable=True)
    withdrawn_flag: Series[bool] = pa.Field(nullable=True)
    black_box_warning: Series[float] = pa.Field(nullable=True, coerce=True)

    # Hierarchy (flattened from molecule_hierarchy)
    hierarchy_parent_chembl_id: Series[str] = pa.Field(nullable=True)
    hierarchy_active_chembl_id: Series[str] = pa.Field(nullable=True)

    # Physicochemical properties (flattened from molecule_properties)
    property_mw_freebase: Series[float] = pa.Field(nullable=True, coerce=True)
    property_alogp: Series[float] = pa.Field(nullable=True, coerce=True)
    property_hba: Series[float] = pa.Field(nullable=True, coerce=True)
    property_hbd: Series[float] = pa.Field(nullable=True, coerce=True)
    property_psa: Series[float] = pa.Field(nullable=True, coerce=True)
    property_rtb: Series[float] = pa.Field(nullable=True, coerce=True)
    property_ro5_violations: Series[float] = pa.Field(
        nullable=True, ge=0, le=4, coerce=True
    )
    property_qed_weighted: Series[float] = pa.Field(
        nullable=True, ge=0, le=1, coerce=True
    )
    property_full_molformula: Series[str] = pa.Field(nullable=True)

    # Structural identifiers (flattened from molecule_structures)
    structure_canonical_smiles: Series[str] = pa.Field(nullable=True)
    structure_standard_inchi: Series[str] = pa.Field(nullable=True)
    structure_standard_inchi_key: Series[str] = pa.Field(nullable=True)

    # Metadata
    _run_id: Series[str] = pa.Field(nullable=False)
    _ingestion_ts: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera configuration."""

        strict = False  # Allow transition period
