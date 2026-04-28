# mypy: disable-error-code="misc"
"""ChEMBL activity and assay Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    StrictGoldContractSchema,
)


class ChEMBLActivityGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Activity in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    activity_id: Series[str] = pa.Field(nullable=False)

    # Core identifiers
    molecule_id: Series[str] = pa.Field(nullable=False)
    target_id: Series[str] = pa.Field(nullable=True)
    assay_id: Series[str] = pa.Field(nullable=True)
    publication_id: Series[str] = pa.Field(nullable=True)
    record_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver

    # Molecule data
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    molecule_pref_name: Series[str] = pa.Field(nullable=True)
    parent_molecule_id: Series[str] = pa.Field(nullable=True)

    # Target data
    target_pref_name: Series[str] = pa.Field(nullable=True)
    target_organism: Series[str] = pa.Field(nullable=True)
    target_taxonomy_id: Series[float] = pa.Field(nullable=True, coerce=True)

    # Assay data
    assay_type: Series[str] = pa.Field(nullable=True)
    assay_description: Series[str] = pa.Field(nullable=True)
    assay_variant_accession: Series[str] = pa.Field(nullable=True)
    assay_variant_mutation: Series[str] = pa.Field(nullable=True)

    # BAO annotations
    bao_endpoint: Series[str] = pa.Field(nullable=True)
    bao_format: Series[str] = pa.Field(nullable=True)
    bao_label: Series[str] = pa.Field(nullable=True)

    # Raw activity values
    type: Series[str] = pa.Field(nullable=True)
    value: Series[float] = pa.Field(nullable=True, coerce=True)
    units: Series[str] = pa.Field(nullable=True)
    relation: Series[str] = pa.Field(nullable=True)
    upper_value: Series[float] = pa.Field(nullable=True, coerce=True)
    text_value: Series[str] = pa.Field(nullable=True)

    # Standardized activity values
    standard_type: Series[str] = pa.Field(nullable=True)
    standard_value: Series[float] = pa.Field(nullable=True, coerce=True)
    standard_units: Series[str] = pa.Field(nullable=True)
    standard_relation: Series[str] = pa.Field(nullable=True)
    standard_upper_value: Series[float] = pa.Field(nullable=True, coerce=True)
    standard_text_value: Series[str] = pa.Field(nullable=True)
    standard_flag: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # Derived metrics
    pchembl_value: Series[float] = pa.Field(nullable=True, coerce=True)

    # Ligand efficiency metrics
    ligand_efficiency_bei: Series[float] = pa.Field(nullable=True, coerce=True)
    ligand_efficiency_le: Series[float] = pa.Field(nullable=True, coerce=True)
    ligand_efficiency_lle: Series[float] = pa.Field(nullable=True, coerce=True)
    ligand_efficiency_sei: Series[float] = pa.Field(nullable=True, coerce=True)

    # Units ontology
    qudt_units: Series[str] = pa.Field(nullable=True)
    uo_units: Series[str] = pa.Field(nullable=True)

    # Document/Publication data
    journal: Series[str] = pa.Field(nullable=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    publication_doi: Series[str] = pa.Field(nullable=True)
    publication_pmid: Series[str] = pa.Field(nullable=True)
    publication_pmc_id: Series[str] = pa.Field(nullable=True)

    # Quality annotations
    activity_comment: Series[str] = pa.Field(nullable=True)
    data_validity_comment: Series[str] = pa.Field(nullable=True)
    data_validity_description: Series[str] = pa.Field(nullable=True)
    potential_duplicate: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # Action type
    action_type: Series[str] = pa.Field(nullable=True)
    action_type_description: Series[str] = pa.Field(nullable=True)
    action_type_parent_type: Series[str] = pa.Field(nullable=True)

    # Activity properties
    activity_properties: Series[str] = pa.Field(nullable=True)
    toid: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver

    # Curation metadata
    manual_curation_flag: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 in Silver
    original_activity_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 in Silver


class ChEMBLAssayGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Assay in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    assay_id: Series[str] = pa.Field(nullable=False)
    target_id: Series[str] = pa.Field(nullable=True)
    publication_id: Series[str] = pa.Field(nullable=True)
    cell_id: Series[str] = pa.Field(nullable=True)
    tissue_id: Series[str] = pa.Field(nullable=True)
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)
    src_assay_id: Series[str] = pa.Field(nullable=True)
    aidx: Series[str] = pa.Field(nullable=True)
    assay_type: Series[str] = pa.Field(nullable=True)
    assay_type_description: Series[str] = pa.Field(nullable=True)
    assay_category: Series[str] = pa.Field(nullable=True)
    assay_test_type: Series[str] = pa.Field(nullable=True)
    assay_group: Series[str] = pa.Field(nullable=True)
    assay_organism: Series[str] = pa.Field(nullable=True)
    assay_taxonomy_id: Series[float] = pa.Field(nullable=True, coerce=True)
    assay_cell_type: Series[str] = pa.Field(nullable=True)
    assay_tissue: Series[str] = pa.Field(nullable=True)
    assay_strain: Series[str] = pa.Field(nullable=True)
    assay_subcellular_fraction: Series[str] = pa.Field(nullable=True)
    bao_format: Series[str] = pa.Field(nullable=True)
    bao_label: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    confidence_score: Series[float] = pa.Field(nullable=True, coerce=True)
    confidence_description: Series[str] = pa.Field(nullable=True)
    relationship_type: Series[str] = pa.Field(nullable=True)
    relationship_description: Series[str] = pa.Field(nullable=True)
    assay_pref_name: Series[str] = pa.Field(nullable=True)
    score: Series[float] = pa.Field(nullable=True, coerce=True)
    variant_accession: Series[str] = pa.Field(nullable=True)
    variant_isoform: Series[str] = pa.Field(nullable=True)
    variant_mutation: Series[str] = pa.Field(nullable=True)
    variant_organism: Series[str] = pa.Field(nullable=True)
    variant_sequence: Series[str] = pa.Field(nullable=True)
    variant_taxonomy_id: Series[float] = pa.Field(nullable=True, coerce=True)
    variant_sequence_json: Series[str] = pa.Field(nullable=True)
    assay_classifications: Series[str] = pa.Field(nullable=True)
    assay_parameters: Series[str] = pa.Field(nullable=True)


class ChEMBLAssayParametersGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL AssayParameters in Gold layer.

    Experimental parameters for bioassays: concentrations, pH, temperature, etc.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier (surrogate)
    assay_param_id: Series[float] = pa.Field(
        nullable=False, coerce=True
    )  # int64 in Silver

    # Foreign key
    assay_id: Series[str] = pa.Field(nullable=False)

    # Parameter type
    type: Series[str] = pa.Field(nullable=False)

    # Raw values
    relation: Series[str] = pa.Field(nullable=True)
    value: Series[float] = pa.Field(nullable=True, coerce=True)
    units: Series[str] = pa.Field(nullable=True)
    text_value: Series[str] = pa.Field(nullable=True)
    comments: Series[str] = pa.Field(nullable=True)

    # Standardized values
    standard_type: Series[str] = pa.Field(nullable=True)
    standard_relation: Series[str] = pa.Field(nullable=True)
    standard_value: Series[float] = pa.Field(nullable=True, coerce=True)
    standard_units: Series[str] = pa.Field(nullable=True)
    standard_text_value: Series[str] = pa.Field(nullable=True)


__all__ = [
    "ChEMBLActivityGoldSchema",
    "ChEMBLAssayGoldSchema",
    "ChEMBLAssayParametersGoldSchema",
]
