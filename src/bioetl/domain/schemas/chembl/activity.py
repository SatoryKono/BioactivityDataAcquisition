# pyright: reportIncompatibleVariableOverride=false
# Schema field override residual (PD3).
"""Pandera schema for ChEMBL Activity entity aligned with RULES.md v5.24 and ChEMBL 34 schema."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.base import ETLRecordSchema
from bioetl.domain.schemas.constants import (
    ACTIVITY_STANDARD_TYPES,
    ACTIVITY_STANDARD_UNITS,
    ASSAY_TYPES,
    BAO_ID_PATTERN,
    CHEMBL_ID_PATTERN,
    DATA_VALIDITY_COMMENTS,
    ONTOLOGY_MAPPING_STATUSES,
    STANDARD_RELATIONS,
    UO_ID_PATTERN,
)
from bioetl.domain.validation import MAX_PUBLICATION_YEAR, MIN_PUBLICATION_YEAR

__all__ = ["ActivitySchema"]

HTTP_IRI_PATTERN = r"^https?://[^\s]+$"


class ActivitySchema(ETLRecordSchema):
    """Activity validation schema for Silver layer."""

    source_batch_id: Series[str] = pa.Field(
        alias="_source_batch_id",
        nullable=False,
        description="Batch context ID from the source.",
    )
    state: Series[str] = pa.Field(
        alias="_state",
        nullable=False,
        isin=["raw", "normalized", "validated"],
        description="Processing state for the activity record.",
    )
    # === Primary Key ===
    activity_id: Series[str] = pa.Field(nullable=False, description="Primary key.")
    # === Foreign Keys ===
    assay_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Foreign key to assay.",
    )
    molecule_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Foreign key to molecule.",
    )
    target_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Foreign key to target.",
    )
    publication_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=CHEMBL_ID_PATTERN,
        description="Foreign key to document.",
    )
    # === Standardized Values ===
    standard_relation: Series[str] = pa.Field(
        nullable=False,
        isin=list(STANDARD_RELATIONS),
        description="Standardized operator.",
    )
    standard_value: Series[float] = pa.Field(
        nullable=False,
        ge=0,
        description="Standardized value.",
    )
    standard_units: Series[str] = pa.Field(
        nullable=False,
        isin=list(ACTIVITY_STANDARD_UNITS),
        description="Standardized units.",
    )
    standard_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(ACTIVITY_STANDARD_TYPES),
        description="Standardized measurement type.",
    )
    standard_flag: Series[int] = pa.Field(
        nullable=False,
        isin=[0, 1],
        description="Standardization flag.",
    )
    # === Derived Metrics ===
    pchembl_value: Series[float] = pa.Field(
        nullable=False,
        ge=0,
        le=14,
        description="-log10 of molar activity.",
    )
    # === Comments & Quality ===
    data_validity_comment: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(DATA_VALIDITY_COMMENTS),
        description="Data quality comment.",
    )
    activity_comment: Series[str] | None = pa.Field(
        nullable=True, description="Textual comment."
    )
    potential_duplicate: Series[int] = pa.Field(
        nullable=False,
        isin=[0, 1],
        description="Duplicate flag.",
    )
    # === Ontologies ===
    bao_endpoint: Series[str] = pa.Field(
        nullable=False,
        str_matches=BAO_ID_PATTERN,
        description="BAO ID.",
    )
    bao_endpoint_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the BAO endpoint ID.",
    )
    bao_endpoint_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="BAO endpoint IRI mapping status.",
    )
    bao_format_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the BAO format ID.",
    )
    bao_format_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="BAO format IRI mapping status.",
    )
    bao_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="BAO ontology release/version used for IRI mapping.",
    )
    uo_units: Series[str] = pa.Field(
        nullable=False,
        str_matches=UO_ID_PATTERN,
        description="Units Ontology ID.",
    )
    uo_unit_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent IRI for the Units Ontology unit ID.",
    )
    uo_unit_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="Units Ontology IRI mapping status.",
    )
    uo_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="Units Ontology release/version used for IRI mapping.",
    )
    qudt_units: Series[str] | None = pa.Field(nullable=True, description="QUDT unit.")
    qudt_unit_iri: Series[str] | None = pa.Field(
        nullable=True,
        str_matches=HTTP_IRI_PATTERN,
        description="Persistent QUDT unit IRI.",
    )
    qudt_unit_mapping_status: Series[str] | None = pa.Field(
        nullable=True,
        isin=list(ONTOLOGY_MAPPING_STATUSES),
        description="QUDT unit IRI mapping status.",
    )
    qudt_ontology_version: Series[str] | None = pa.Field(
        nullable=True,
        description="QUDT ontology release/version used for IRI mapping.",
    )
    # === Original Values & Other Fields ===
    src_id: Series[int] = pa.Field(nullable=False, description="Source ID.")
    record_id: Series[int] = pa.Field(
        nullable=False, description="FK to compound_record."
    )
    activity_type: Series[str] | None = pa.Field(
        nullable=True, description="Original type."
    )
    activity_relation: Series[str] = pa.Field(
        nullable=False, description="Original operator."
    )
    activity_value: Series[float] = pa.Field(
        nullable=False, description="Original value."
    )
    units: Series[str] = pa.Field(nullable=False, description="Original units.")
    text_value: Series[str] | None = pa.Field(nullable=True, description="Text value.")
    standard_text_value: Series[str] | None = pa.Field(
        nullable=True, description="Standardized text value."
    )
    upper_value: Series[float] | None = pa.Field(
        nullable=True, description="Upper bound."
    )
    standard_upper_value: Series[float] | None = pa.Field(
        nullable=True, description="Standardized upper bound."
    )
    toid: Series[float] | None = pa.Field(
        nullable=True, description="Test Occasion ID (float for nullable int)."
    )
    manual_curation_flag: Series[pd.Int64Dtype] | None = pa.Field(
        nullable=True,
        isin=[0, 1],
        description="Manual curation flag.",
    )
    original_activity_id: Series[float] | None = pa.Field(
        nullable=True, description="Original activity ID (float for nullable int)."
    )
    data_validity_description: Series[str] | None = pa.Field(
        nullable=True, description="Human-readable data validity explanation."
    )
    # === Flattened Fields (from JSON) ===
    ligand_efficiency_bei: Series[float] | None = pa.Field(
        nullable=True, description="Binding Efficiency Index (BEI)."
    )
    ligand_efficiency_le: Series[float] | None = pa.Field(
        nullable=True, description="Ligand Efficiency (LE)."
    )
    ligand_efficiency_lle: Series[float] | None = pa.Field(
        nullable=True, description="Lipophilic Ligand Efficiency (LLE)."
    )
    ligand_efficiency_sei: Series[float] | None = pa.Field(
        nullable=True, description="Surface Efficiency Index (SEI)."
    )
    action_type: Series[str] | None = pa.Field(
        nullable=True, description="Action type classification."
    )
    action_type_description: Series[str] | None = pa.Field(
        nullable=True, description="Action type description."
    )
    action_type_parent_type: Series[str] | None = pa.Field(
        nullable=True, description="Parent action type category."
    )
    activity_properties: Series[str] | None = pa.Field(
        nullable=True, description="JSON string of activity properties."
    )
    # === Additional Fields from Silver Schema ===
    canonical_smiles: Series[str] = pa.Field(
        nullable=False, description="Canonical SMILES of molecule."
    )
    molecule_pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Molecule preferred name."
    )
    parent_molecule_id: Series[str] | None = pa.Field(
        nullable=True, description="Parent molecule ChEMBL ID."
    )
    target_pref_name: Series[str] | None = pa.Field(
        nullable=True, description="Target preferred name."
    )
    target_organism: Series[str] = pa.Field(
        nullable=False, description="Target organism."
    )
    target_taxonomy_id: Series[pd.Int64Dtype] = pa.Field(
        nullable=False,
        description="Target taxonomy ID.",
    )
    assay_type: Series[str] = pa.Field(
        nullable=False,
        isin=list(ASSAY_TYPES),
        description="Assay type (B/F/A/T/P/U).",
    )
    assay_description: Series[str] = pa.Field(
        nullable=False, description="Assay description text."
    )
    assay_variant_accession: Series[str] | None = pa.Field(
        nullable=True, description="Assay variant protein accession."
    )
    assay_variant_mutation: Series[str] | None = pa.Field(
        nullable=True, description="Assay variant mutation description."
    )
    bao_format: Series[str] = pa.Field(
        nullable=False,
        str_matches=BAO_ID_PATTERN,
        description="BioAssay Ontology format ID.",
    )
    bao_label: Series[str] = pa.Field(
        nullable=False, description="BioAssay Ontology label."
    )
    journal: Series[str] = pa.Field(nullable=False, description="Journal name.")
    publication_doi: Series[str] | None = pa.Field(
        nullable=True, description="Publication DOI."
    )
    publication_pmid: Series[str] | None = pa.Field(
        nullable=True, description="Publication PMID."
    )
    publication_pmc_id: Series[str] | None = pa.Field(
        nullable=True, description="Publication PMC ID."
    )
    publication_year: Series[int] = pa.Field(
        nullable=False,
        ge=MIN_PUBLICATION_YEAR,
        le=MAX_PUBLICATION_YEAR,
        description="Publication year.",
    )

    class Config:  # pyright: ignore[reportIncompatibleVariableOverride]
        """Pandera configuration."""
        strict = True
        ordered = False
        coerce = True
