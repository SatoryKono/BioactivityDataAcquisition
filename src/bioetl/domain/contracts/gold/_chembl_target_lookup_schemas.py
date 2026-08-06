# mypy: disable-error-code="misc"
"""ChEMBL target and lookup Gold-layer contracts."""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

from bioetl.domain.contracts.gold._strict_gold_contract_schema import (
    CONTENT_HASH_HEX64_PATTERN,
    StrictGoldContractSchema,
)


class ChEMBLTargetGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Target in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )
    target_id: Series[str] = pa.Field(nullable=False)
    target_type: Series[str] = pa.Field(nullable=True)
    pref_name: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name
    organism: Series[str] = pa.Field(nullable=True)
    organism_class: Series[str] = pa.Field(nullable=True)
    species_group_flag: Series[bool] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    target_protein_synonyms: Series[str] = pa.Field(nullable=True)
    target_gene_synonyms: Series[str] = pa.Field(nullable=True)
    target_ec_numbers: Series[str] = pa.Field(nullable=True)
    target_xref_pdb_ids: Series[str] = pa.Field(nullable=True)
    target_xref_go_component: Series[str] = pa.Field(nullable=True)
    target_xref_go_function: Series[str] = pa.Field(nullable=True)
    target_xref_go_process: Series[str] = pa.Field(nullable=True)
    target_xref_hgnc_ids: Series[str] = pa.Field(nullable=True)
    target_xref_reactome_ids: Series[str] = pa.Field(nullable=True)
    target_xref_uniprot_ids: Series[str] = pa.Field(nullable=True)
    primary_component_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float (nullable)
    component_accessions: Series[str] = pa.Field(nullable=True)  # list[str]
    component_descriptions: Series[str] = pa.Field(nullable=True)
    component_ids: Series[str] = pa.Field(nullable=True)  # list[int]
    component_types: Series[str] = pa.Field(nullable=True)  # list[str]
    component_relationships: Series[str] = pa.Field(nullable=True)  # list[str]
    target_components: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    target_component_synonyms: Series[str] = pa.Field(nullable=True)


class ChEMBLTargetComponentGoldSchema(StrictGoldContractSchema):
    """Schema for ChEMBL Target Component in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )
    primary_component_id: Series[float] = pa.Field(
        nullable=False, coerce=True, alias="component_id"
    )  # int64
    accession: Series[str] = pa.Field(nullable=True)
    component_type: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    target_component_xrefs: Series[str] = pa.Field(nullable=True)
    protein_classifications: Series[str] = pa.Field(nullable=True)
    protein_classification_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float (nullable)
    protein_classification_ids: Series[str] = pa.Field(nullable=True)  # list[int]


class ChEMBLTargetProteinClassificationGoldSchema(StrictGoldContractSchema):
    """Gold schema for ChEMBL target protein classification relation rows."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )
    target_id: Series[str] = pa.Field(nullable=False)
    classification_status: Series[str] = pa.Field(
        nullable=False,
        isin=["resolved", "missing_classification", "quarantined"],
    )
    component_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    leaf_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    path_ids: Series[str] = pa.Field(nullable=True)
    path_names: Series[str] = pa.Field(nullable=True)
    path_labels: Series[str] = pa.Field(nullable=True)
    depth: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    root_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    is_leaf: Series[bool] = pa.Field(nullable=True)
    l1_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    l1_name: Series[str] = pa.Field(nullable=True)
    l1_desc: Series[str] = pa.Field(nullable=True)
    l2_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    l2_name: Series[str] = pa.Field(nullable=True)
    l2_desc: Series[str] = pa.Field(nullable=True)
    l3_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    l3_name: Series[str] = pa.Field(nullable=True)
    l3_desc: Series[str] = pa.Field(nullable=True)
    l4_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    l4_name: Series[str] = pa.Field(nullable=True)
    l4_desc: Series[str] = pa.Field(nullable=True)
    l5_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    l5_name: Series[str] = pa.Field(nullable=True)
    l5_desc: Series[str] = pa.Field(nullable=True)
    canonical_l1: Series[str] = pa.Field(nullable=True)
    l1_counts_for_target_type: Series[bool] = pa.Field(nullable=True)
    l1_mapping_version: Series[str] = pa.Field(nullable=True)
    target_type_rule_version: Series[str] = pa.Field(nullable=True)
    l1_normalization_status: Series[str] = pa.Field(
        nullable=True,
        isin=["ok", "non_counting", "missing", "fallback", "failed"],
    )
    l1_normalization_notes: Series[str] = pa.Field(nullable=True)
    dataset_version: Series[str] = pa.Field(nullable=True)
    source_url: Series[str] = pa.Field(nullable=True)
    chembl_release: Series[str] = pa.Field(nullable=True)
    chembl_api_version: Series[str] = pa.Field(nullable=True)
    source_manifest_status: Series[str] = pa.Field(
        nullable=True,
        isin=["release_metadata_available", "release_metadata_unavailable"],
    )
    source_snapshot_fingerprint: Series[str] = pa.Field(nullable=True)
    target_snapshot_row_count: Series[float] = pa.Field(
        nullable=True, ge=0, coerce=True
    )
    target_component_snapshot_row_count: Series[float] = pa.Field(
        nullable=True, ge=0, coerce=True
    )
    protein_class_snapshot_row_count: Series[float] = pa.Field(
        nullable=True, ge=0, coerce=True
    )


class ChEMBLTissueGoldSchema(StrictGoldContractSchema):
    """Gold schema for ChEMBL Tissue entity.

    Validates:
    - tissue_id: Required, CHEMBL format (aliased from tissue_chembl_id by transformer)
    - pref_name: Required, non-empty
    - Ontology IDs: Optional, format validation
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )

    # Primary key (transformer maps tissue_chembl_id → tissue_id)
    tissue_id: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^CHEMBL\d+$",
        description="ChEMBL tissue ID",
    )

    # Core metadata
    pref_name: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
        description="Preferred tissue name",
    )

    # Ontology identifiers (optional)
    # Underscore form matches domain tissue normalization (colon → underscore).
    bto_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^BTO_\d{7}$",
        description="BRENDA Tissue Ontology ID (underscore form, e.g. BTO_0000001)",
    )
    caloha_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^TS-\d{4}$",
        description="CALIPHO ID",
    )
    efo_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^EFO_\d{7}$",
        description="Experimental Factor Ontology ID (underscore form)",
    )
    uberon_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^UBERON_\d{7}$",
        description="Uberon Ontology ID (underscore form)",
    )


class ChEMBLSubcellularFractionGoldSchema(StrictGoldContractSchema):
    """Gold schema for ChEMBL Subcellular Fraction entity.

    Derived entity: unique subcellular fractions extracted from Assay records.
    Creates a lookup/reference table for biological context normalization.

    Validates:
    - entity_id: Required, 16-char SHA256 prefix
    - subcellular_fraction: Required, non-empty
    - assay_count: Optional, non-negative
    - example_assay_chembl_id: Optional, CHEMBL format
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(
        nullable=False,
        str_matches=CONTENT_HASH_HEX64_PATTERN,
    )

    # Primary key (normalized subcellular fraction name)
    subcellular_fraction: Series[str] = pa.Field(
        nullable=False,
        str_length={"min_value": 1, "max_value": 200},
        description="Subcellular fraction name",
    )

    # Statistics
    assay_count: Series[float] = pa.Field(
        nullable=True,
        coerce=True,
        description="Number of assays using this fraction",
    )

    # Example reference
    example_assay_id: Series[str] = pa.Field(
        nullable=True,
        description="Example assay ChEMBL ID",
    )


__all__ = [
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTargetProteinClassificationGoldSchema",
    "ChEMBLTissueGoldSchema",
]
