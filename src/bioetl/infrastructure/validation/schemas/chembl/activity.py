"""Pandera schema for normalized ChEMBL activity table.

This schema validates the structure and content of activity data
after normalization. Field definitions are based on domain specifications
in bioetl.domain.schemas.field_specs.
"""

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.schemas.field_specs import (
    BAO_ID_PATTERN,
    CHEMBL_ID_PATTERN,
)
from bioetl.infrastructure.validation.schemas.pandera_base import (
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)

__all__ = ["ActivityTableSchema", "OUTPUT_COLUMN_ORDER"]

# Business columns in canonical order
_ACTIVITY_BUSINESS_COLUMNS: list[str] = [
    "action_type",
    "activity_comment",
    "activity_id",
    "activity_properties",
    "assay_chembl_id",
    "assay_description",
    "assay_type",
    "assay_variant_accession",
    "assay_variant_mutation",
    "bao_endpoint",
    "bao_format",
    "bao_label",
    "canonical_smiles",
    "data_validity_comment",
    "data_validity_description",
    "document_chembl_id",
    "document_journal",
    "document_year",
    "ligand_efficiency",
    "molecule_chembl_id",
    "molecule_pref_name",
    "parent_molecule_chembl_id",
    "pchembl_value",
    "potential_duplicate",
    "qudt_units",
    "record_id",
    "relation",
    "src_id",
    "standard_flag",
    "standard_relation",
    "standard_text_value",
    "standard_type",
    "standard_units",
    "standard_upper_value",
    "standard_value",
    "target_chembl_id",
    "target_organism",
    "target_pref_name",
    "target_tax_id",
    "text_value",
    "toid",
    "type",
    "units",
    "uo_units",
    "upper_value",
    "value",
]

OUTPUT_COLUMN_ORDER: list[str] = build_output_column_order(_ACTIVITY_BUSINESS_COLUMNS)


class ActivityTableSchema(BaseGeneratedColumnsSchema):
    """Pandera schema describing the normalized Activity table.

    Validates ChEMBL activity measurements including:
    - Molecule and target identifiers
    - Activity values (raw and standardized)
    - Assay metadata
    - Quality flags and comments
    """

    action_type: Series[str] = pa.Field(
        nullable=True, description="Action type (agonist, antagonist)"
    )
    activity_comment: Series[str] = pa.Field(
        nullable=True, description="Comment on activity measurement"
    )
    activity_id: Series[int] = pa.Field(ge=1, description="Internal activity ID")
    activity_properties: Series[str] = pa.Field(
        nullable=True, description="Additional activity properties (JSON)"
    )
    assay_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL assay identifier"
    )
    assay_description: Series[str] = pa.Field(
        nullable=True, description="Textual assay description"
    )
    assay_type: Series[str] = pa.Field(
        isin=["B", "F", "A", "T", "P", "U", "b", "f", "a", "t", "p", "u"],
        description=(
            "Assay type (B=binding, F=functional, A=ADMET, T=toxicity, "
            "P=physicochemical, U=unknown)"
        ),
    )
    assay_variant_accession: Series[str] = pa.Field(
        nullable=True, description="Protein variant accession"
    )
    assay_variant_mutation: Series[str] = pa.Field(
        nullable=True, description="Protein variant mutation description"
    )
    bao_endpoint: Series[str] = pa.Field(
        nullable=True,
        str_matches=BAO_ID_PATTERN,
        description="BioAssay Ontology endpoint term",
    )
    bao_format: Series[str] = pa.Field(
        nullable=True,
        str_matches=BAO_ID_PATTERN,
        description="BioAssay Ontology format term",
    )
    bao_label: Series[str] = pa.Field(
        nullable=True, description="BAO endpoint/format label"
    )
    canonical_smiles: Series[str] = pa.Field(
        nullable=True, description="Canonical SMILES of molecule"
    )
    data_validity_comment: Series[str] = pa.Field(
        nullable=True, description="Data quality/validity comment"
    )
    data_validity_description: Series[str] = pa.Field(
        nullable=True, description="Description of data issues"
    )
    document_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL document identifier"
    )
    document_journal: Series[str] = pa.Field(nullable=True, description="Journal name")
    document_year: Series[float] = pa.Field(
        nullable=True, description="Publication year"
    )
    ligand_efficiency: Series[object] = pa.Field(
        nullable=True, description="Ligand efficiency metrics (JSON)"
    )
    molecule_chembl_id: Series[str] = pa.Field(
        str_matches=CHEMBL_ID_PATTERN, description="ChEMBL molecule identifier"
    )
    molecule_pref_name: Series[str] = pa.Field(
        nullable=True, description="Molecule preferred name"
    )
    parent_molecule_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="Parent molecule ChEMBL ID",
    )
    pchembl_value: Series[float] = pa.Field(
        nullable=True,
        ge=0,
        le=15,
        description="Normalized activity (-log10, range 0-15)",
    )
    potential_duplicate: Series[bool] = pa.Field(
        nullable=True, description="Flag for potential duplicate"
    )
    qudt_units: Series[str] = pa.Field(nullable=True, description="QUDT units URI")
    record_id: Series[float] = pa.Field(
        nullable=True, ge=1, description="Compound record ID"
    )
    relation: Series[str] = pa.Field(
        nullable=True,
        isin=["=", ">", "<", ">=", "<=", "~"],
        description="Original relation (=, >, <, etc.)",
    )
    src_id: Series[float] = pa.Field(nullable=True, description="Data source ID")
    standard_flag: Series[bool] = pa.Field(
        description="Flag indicating standardized type/value"
    )
    standard_relation: Series[str] = pa.Field(
        nullable=True,
        isin=["=", ">", "<", ">=", "<=", "~"],
        description="Standardized relation",
    )
    standard_text_value: Series[str] = pa.Field(
        nullable=True, description="Standardized text for qualitative values"
    )
    standard_type: Series[str] = pa.Field(
        nullable=True, description="Standardized activity type"
    )
    standard_units: Series[str] = pa.Field(
        nullable=True, description="Standardized units"
    )
    standard_upper_value: Series[float] = pa.Field(
        nullable=True, description="Upper bound of standardized interval"
    )
    standard_value: Series[float] = pa.Field(
        nullable=True, description="Standardized numeric value"
    )
    target_chembl_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=CHEMBL_ID_PATTERN,
        description="ChEMBL target identifier",
    )
    target_organism: Series[str] = pa.Field(
        nullable=True, description="Target organism"
    )
    target_pref_name: Series[str] = pa.Field(
        nullable=True, description="Target preferred name"
    )
    target_tax_id: Series[float] = pa.Field(
        nullable=True, description="Target NCBI Taxonomy ID"
    )
    text_value: Series[str] = pa.Field(nullable=True, description="Original text value")
    toid: Series[str] = pa.Field(nullable=True, description="Target Ontology ID")
    type: Series[str] = pa.Field(nullable=True, description="Original activity type")
    units: Series[str] = pa.Field(
        nullable=True, description="Original measurement units"
    )
    uo_units: Series[str] = pa.Field(nullable=True, description="Unit Ontology ID")
    upper_value: Series[float] = pa.Field(
        nullable=True, description="Upper bound of original interval"
    )
    value: Series[float] = pa.Field(nullable=True, description="Original numeric value")
