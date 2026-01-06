"""Gold layer Pandera schemas for data validation.

Defines the Pandera DataFrameModels for various entities in the Gold layer.
Updated to match Silver layer schemas exactly (identical column sets).
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class ChEMBLActivityGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Activity in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    activity_id: Series[str] = pa.Field(nullable=False)

    # Core identifiers
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=True)
    assay_chembl_id: Series[str] = pa.Field(nullable=True)
    document_chembl_id: Series[str] = pa.Field(nullable=True)
    record_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver

    # Molecule data
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    molecule_pref_name: Series[str] = pa.Field(nullable=True)
    parent_molecule_chembl_id: Series[str] = pa.Field(nullable=True)

    # Target data
    target_pref_name: Series[str] = pa.Field(nullable=True)
    target_organism: Series[str] = pa.Field(nullable=True)
    target_tax_id: Series[str] = pa.Field(nullable=True)

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
    standard_flag: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 in Silver

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
    document_journal: Series[str] = pa.Field(nullable=True)
    document_year: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 in Silver

    # Quality annotations
    activity_comment: Series[str] = pa.Field(nullable=True)
    data_validity_comment: Series[str] = pa.Field(nullable=True)
    data_validity_description: Series[str] = pa.Field(nullable=True)
    potential_duplicate: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64 in Silver

    # Action type
    action_type_action_type: Series[str] = pa.Field(nullable=True)
    action_type_description: Series[str] = pa.Field(nullable=True)
    action_type_parent_type: Series[str] = pa.Field(nullable=True)

    # Activity properties
    activity_properties: Series[str] = pa.Field(nullable=True)
    toid: Series[float] = pa.Field(nullable=True, coerce=True)  # int64 in Silver

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class PubChemCompoundGoldSchema(pa.DataFrameModel):
    """Schema for PubChem Compound in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    cid: Series[str] = pa.Field(nullable=False)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[str] = pa.Field(nullable=True)
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    isomeric_smiles: Series[str] = pa.Field(nullable=True)
    inchi: Series[str] = pa.Field(nullable=True)
    inchikey: Series[str] = pa.Field(nullable=True)
    iupac_name: Series[str] = pa.Field(nullable=True)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class UniProtProteinGoldSchema(pa.DataFrameModel):
    """Schema for UniProt Protein in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    accession: Series[str] = pa.Field(nullable=False)
    entry_name: Series[str] = pa.Field(nullable=True)
    protein_name: Series[str] = pa.Field(nullable=True)
    gene_names: Series[object] = pa.Field(nullable=True)  # list[str]
    organism_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    sequence_length: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    content_hash: Series[str] = pa.Field(nullable=False)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class UniProtIDMappingGoldSchema(pa.DataFrameModel):
    """Schema for UniProt ID Mapping in Gold layer.

    Maps ChEMBL target IDs to UniProt accessions.
    Records with mapping_status='not_found' have null uniprot_accession.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key (source identifier)
    target_chembl_id: Series[str] = pa.Field(nullable=False)

    # Mapped identifier (nullable - None if not found)
    uniprot_accession: Series[str] = pa.Field(nullable=True)

    # Mapping status: 'found', 'not_found', 'error'
    mapping_status: Series[str] = pa.Field(nullable=False)

    # DQ warning flag (True for not_found)
    dq_warn: Series[bool] = pa.Field(nullable=False, alias="_dq_warn")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class PubMedPublicationGoldSchema(pa.DataFrameModel):
    """Schema for PubMed Publication in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    pmid: Series[str] = pa.Field(nullable=False)
    doi: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    journal_abbrev: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    pages: Series[str] = pa.Field(nullable=True)
    authors: Series[object] = pa.Field(nullable=True)  # list[str]
    pub_date: Series[str] = pa.Field(nullable=True)
    pub_year: Series[float] = pa.Field(nullable=True, coerce=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)
    accepted_date: Series[str] = pa.Field(nullable=True)
    received_date: Series[str] = pa.Field(nullable=True)
    revised_date: Series[str] = pa.Field(nullable=True)
    epub_date: Series[str] = pa.Field(nullable=True)
    publication_types: Series[object] = pa.Field(nullable=True)  # list[str]
    keywords: Series[object] = pa.Field(nullable=True)  # list[str]
    mesh_terms: Series[object] = pa.Field(nullable=True)  # list[str]
    language: Series[str] = pa.Field(nullable=True)
    country: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLAssayGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Assay in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    assay_chembl_id: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=True)
    document_chembl_id: Series[str] = pa.Field(nullable=True)
    cell_chembl_id: Series[str] = pa.Field(nullable=True)
    tissue_chembl_id: Series[str] = pa.Field(nullable=True)
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)
    src_assay_id: Series[str] = pa.Field(nullable=True)
    aidx: Series[str] = pa.Field(nullable=True)
    assay_type: Series[str] = pa.Field(nullable=True)
    assay_type_description: Series[str] = pa.Field(nullable=True)
    assay_category: Series[str] = pa.Field(nullable=True)
    assay_test_type: Series[str] = pa.Field(nullable=True)
    assay_group: Series[str] = pa.Field(nullable=True)
    assay_organism: Series[str] = pa.Field(nullable=True)
    assay_tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
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
    variant_tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
    variant_sequence_json: Series[str] = pa.Field(nullable=True)
    assay_classifications: Series[str] = pa.Field(nullable=True)
    assay_parameters: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLTargetGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    target_chembl_id: Series[str] = pa.Field(nullable=False)
    pref_name: Series[str] = pa.Field(nullable=True)
    target_type: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
    species_group_flag: Series[bool] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    downgraded: Series[bool] = pa.Field(nullable=True, coerce=True)
    dap_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    pipeline_stages: Series[str] = pa.Field(nullable=True)
    target_constraints: Series[str] = pa.Field(nullable=True)
    target_components: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    component_accessions: Series[object] = pa.Field(nullable=True)  # list[str]
    component_ids: Series[object] = pa.Field(nullable=True)  # list[int]
    component_types: Series[object] = pa.Field(nullable=True)  # list[str]
    component_relationships: Series[object] = pa.Field(nullable=True)  # list[str]
    component_descriptions: Series[object] = pa.Field(nullable=True)  # list[str]
    component_organisms: Series[object] = pa.Field(nullable=True)  # list[str]
    component_tax_ids: Series[object] = pa.Field(nullable=True)  # list[int]

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLTargetComponentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target Component in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    component_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64
    accession: Series[str] = pa.Field(nullable=True)
    component_type: Series[str] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    tax_id: Series[float] = pa.Field(nullable=True, coerce=True)
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    target_component_xrefs: Series[str] = pa.Field(nullable=True)
    protein_classifications: Series[str] = pa.Field(nullable=True)
    protein_classification_ids: Series[object] = pa.Field(nullable=True)  # list[int]

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLDocumentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    document_chembl_id: Series[str] = pa.Field(nullable=False)
    pubmed_id: Series[str] = pa.Field(nullable=True)  # Numeric string (matches Silver)
    doi: Series[str] = pa.Field(nullable=True)
    patent_id: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    doc_type: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    journal_full_title: Series[str] = pa.Field(nullable=True)
    year: Series[float] = pa.Field(nullable=True, coerce=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLDocumentTermGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Term in Gold layer.

    Derived entity extracted from Document records by flattening
    the 1:M relationship between documents and their terms.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Composite key fields
    document_chembl_id: Series[str] = pa.Field(nullable=False)
    term: Series[str] = pa.Field(nullable=False)
    term_type: Series[str] = pa.Field(nullable=False)

    # MeSH-specific fields
    mesh_id: Series[str] = pa.Field(nullable=True)
    qualifier: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    pref_name: Series[str] = pa.Field(nullable=True)
    molecule_type: Series[str] = pa.Field(nullable=True)
    structure_type: Series[str] = pa.Field(nullable=True)
    max_phase: Series[float] = pa.Field(nullable=True, coerce=True)
    first_approval: Series[float] = pa.Field(nullable=True, coerce=True)
    chirality: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    dosed_ingredient: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    availability_type: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    usan_stem: Series[str] = pa.Field(nullable=True)
    usan_stem_definition: Series[str] = pa.Field(nullable=True)
    usan_substem: Series[str] = pa.Field(nullable=True)
    usan_year: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    helm_notation: Series[str] = pa.Field(nullable=True)
    molecule_species: Series[str] = pa.Field(nullable=True)
    oral: Series[bool] = pa.Field(nullable=True)
    parenteral: Series[bool] = pa.Field(nullable=True)
    topical: Series[bool] = pa.Field(nullable=True)
    black_box_warning: Series[float] = pa.Field(nullable=True, coerce=True)
    natural_product: Series[float] = pa.Field(nullable=True, coerce=True)
    first_in_class: Series[float] = pa.Field(nullable=True, coerce=True)
    prodrug: Series[float] = pa.Field(nullable=True, coerce=True)
    therapeutic_flag: Series[bool] = pa.Field(nullable=True)
    withdrawn_flag: Series[bool] = pa.Field(nullable=True)
    inorganic_flag: Series[float] = pa.Field(nullable=True, coerce=True)
    polymer_flag: Series[float] = pa.Field(nullable=True, coerce=True)
    molecule_hierarchy: Series[str] = pa.Field(nullable=True)
    molecule_properties: Series[str] = pa.Field(nullable=True)
    molecule_structures: Series[str] = pa.Field(nullable=True)
    molecule_synonyms: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    atc_classifications: Series[str] = pa.Field(nullable=True)
    hierarchy_parent_chembl_id: Series[str] = pa.Field(nullable=True)
    hierarchy_active_chembl_id: Series[str] = pa.Field(nullable=True)
    hierarchy_child_chembl_id: Series[str] = pa.Field(nullable=True)
    property_alogp: Series[float] = pa.Field(nullable=True, coerce=True)
    property_mw_freebase: Series[float] = pa.Field(nullable=True, coerce=True)
    property_full_mwt: Series[float] = pa.Field(nullable=True, coerce=True)
    property_hba: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    property_hbd: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    property_psa: Series[float] = pa.Field(nullable=True, coerce=True)
    property_rtb: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    property_ro5_violations: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64
    property_heavy_atoms: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    property_aromatic_rings: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int64
    property_qed_weighted: Series[float] = pa.Field(nullable=True, coerce=True)
    property_full_molformula: Series[str] = pa.Field(nullable=True)
    property_ro3_pass: Series[str] = pa.Field(nullable=True)
    structure_canonical_smiles: Series[str] = pa.Field(nullable=True)
    structure_standard_inchi: Series[str] = pa.Field(nullable=True)
    structure_standard_inchi_key: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLCompoundRecordGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Compound Record in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    record_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # Foreign keys
    molecule_chembl_id: Series[str] = pa.Field(nullable=False)
    document_chembl_id: Series[str] = pa.Field(nullable=False)

    # Original compound names from document
    compound_key: Series[str] = pa.Field(nullable=True)
    compound_name: Series[str] = pa.Field(nullable=True)

    # Source information
    src_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver
    src_compound_id: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLCellLineGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Cell Line in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    cell_chembl_id: Series[str] = pa.Field(nullable=False)

    # Core metadata
    cell_name: Series[str] = pa.Field(nullable=False)
    cell_description: Series[str] = pa.Field(nullable=True)

    # Source information
    cell_source_tissue: Series[str] = pa.Field(nullable=True)
    cell_source_organism: Series[str] = pa.Field(nullable=True)
    cell_source_tax_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # External identifiers
    cellosaurus_id: Series[str] = pa.Field(nullable=True)
    cl_lincs_id: Series[str] = pa.Field(nullable=True)
    efo_id: Series[str] = pa.Field(nullable=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLDocumentSimilarityGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document Similarity in Gold layer.

    Represents similarity between two ChEMBL documents based on Tanimoto coefficients.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    sim_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # Foreign keys
    doc_1: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver
    doc_2: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # PubMed identifiers (numeric strings - matches Silver)
    pubmed_id1: Series[str] = pa.Field(nullable=True)
    pubmed_id2: Series[str] = pa.Field(nullable=True)

    # Tanimoto coefficients
    tid_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
    mol_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)

    # Derived metrics
    avg_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)
    max_tani: Series[float] = pa.Field(nullable=True, ge=0, le=1, coerce=True)

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class SemanticScholarPublicationGoldSchema(pa.DataFrameModel):
    """Schema for Semantic Scholar Publication in Gold layer.

    Used for enriching publication records with Semantic Scholar metadata.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    paper_id: Series[str] = pa.Field(nullable=False)

    # External IDs
    doi: Series[str] = pa.Field(nullable=True)
    pmid: Series[str] = pa.Field(nullable=True)
    pmcid: Series[str] = pa.Field(nullable=True)
    arxiv_id: Series[str] = pa.Field(nullable=True)
    corpus_id: Series[float] = pa.Field(nullable=True, coerce=True)  # int64

    # Core fields
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    tldr: Series[str] = pa.Field(nullable=True)
    year: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    publication_date: Series[str] = pa.Field(nullable=True)

    # Journal/Venue
    journal: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    pages: Series[str] = pa.Field(nullable=True)
    venue: Series[str] = pa.Field(nullable=True)

    # Metrics
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)  # int64
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)  # int64

    # Open Access
    is_open_access: Series[bool] = pa.Field(nullable=True)
    open_access_url: Series[str] = pa.Field(nullable=True)
    open_access_status: Series[str] = pa.Field(nullable=True)

    # Classification (JSON strings)
    fields_of_study: Series[str] = pa.Field(nullable=True)
    publication_types: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)

    # Source tracking
    source: Series[str] = pa.Field(nullable=True)

    # Lookup metadata
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_doi: Series[str] = pa.Field(nullable=True, alias="_original_doi")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class CrossRefPublicationGoldSchema(pa.DataFrameModel):
    """Schema for CrossRef Publication in Gold layer.

    Used for enriching publication records with CrossRef metadata via DOI resolution.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    doi: Series[str] = pa.Field(nullable=False)

    # Core fields
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    authors: Series[object] = pa.Field(nullable=True)  # list[str]
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[object] = pa.Field(nullable=True)  # list[str]
    publisher: Series[str] = pa.Field(nullable=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    first_page: Series[str] = pa.Field(nullable=True)
    last_page: Series[str] = pa.Field(nullable=True)

    # Date fields
    year: Series[float] = pa.Field(nullable=True, ge=1900, le=2100, coerce=True)
    published_print: Series[str] = pa.Field(nullable=True)
    published_online: Series[str] = pa.Field(nullable=True)

    # Metadata
    doc_type: Series[str] = pa.Field(nullable=True)
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    reference_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)
    license_url: Series[str] = pa.Field(nullable=True)
    subjects: Series[object] = pa.Field(nullable=True)  # list[str]
    source: Series[str] = pa.Field(nullable=True)

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class OpenAlexPublicationGoldSchema(pa.DataFrameModel):
    """Schema for OpenAlex Publication in Gold layer.

    Used for batch DOI resolution with title fallback via OpenAlex Works API.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary key
    openalex_id: Series[str] = pa.Field(nullable=False)

    # Core fields
    doi: Series[str] = pa.Field(nullable=True)
    title: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    authors: Series[object] = pa.Field(nullable=True)  # list[str]
    concepts: Series[object] = pa.Field(nullable=True)  # list[str]

    # Journal info
    journal: Series[str] = pa.Field(nullable=True)
    issn: Series[str] = pa.Field(nullable=True)
    publisher: Series[str] = pa.Field(nullable=True)

    # Date fields
    year: Series[float] = pa.Field(nullable=True, ge=1500, le=2100, coerce=True)
    publication_date: Series[str] = pa.Field(nullable=True)

    # Metadata
    doc_type: Series[str] = pa.Field(nullable=False)
    is_oa: Series[bool] = pa.Field(nullable=True)
    oa_status: Series[str] = pa.Field(nullable=True)
    # OpenAlex source field: cited_by_count
    # Unified BioETL field: citation_count (standardized across all providers)
    citation_count: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    language: Series[str] = pa.Field(nullable=True)
    source: Series[str] = pa.Field(nullable=False)

    # Lookup metadata
    lookup_method: Series[str] = pa.Field(nullable=False, alias="_lookup_method")
    original_doi: Series[str] = pa.Field(nullable=True, alias="_original_doi")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLProteinClassGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Protein Classification in Gold layer.

    Hierarchical classification of protein targets (enzyme classes, receptor types, etc.).
    Self-referencing structure with up to 8 levels of depth.
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    protein_class_id: Series[float] = pa.Field(nullable=False, ge=1, coerce=True)

    # Hierarchy
    parent_id: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    class_level: Series[float] = pa.Field(nullable=True, ge=1, le=8, coerce=True)

    # Classification data
    pref_name: Series[str] = pa.Field(nullable=True)
    short_name: Series[str] = pa.Field(nullable=True)
    protein_class_desc: Series[str] = pa.Field(nullable=True)
    definition: Series[str] = pa.Field(nullable=True)

    # Additional metadata
    sort_order: Series[float] = pa.Field(nullable=True, coerce=True)
    replaced_by: Series[float] = pa.Field(nullable=True, ge=1, coerce=True)
    downgraded: Series[float] = pa.Field(nullable=True, isin=[0, 1], coerce=True)

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True


class ChEMBLAssayParametersGoldSchema(pa.DataFrameModel):
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
    assay_chembl_id: Series[str] = pa.Field(nullable=False)

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

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        strict = True
