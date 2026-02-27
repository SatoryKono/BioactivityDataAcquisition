"""ChEMBL Gold layer data contracts.

Contains Pandera DataFrameModel schemas for ChEMBL entities in the Gold layer:
- Activity: Bioassay activity records with molecule-target-assay relationships
- Assay: Bioassay protocols and parameters
- AssayParameters: Experimental assay parameters (concentrations, pH, temperature)
- CellLine: Cell line metadata
- CompoundRecord: Document-molecule linkages
- Document (Publication): Publication records
- DocumentSimilarity: Document similarity (Tanimoto coefficients)
- DocumentTerm: Document-term associations (flattened 1:M relationship)
- Molecule: Chemical structures with properties
- ProteinClass: Hierarchical protein classifications
- Target: Protein targets with taxonomic info
- TargetComponent: Target protein components

Int→Float coercion note:
    Fields marked with `coerce=True` and `Series[float]` that are `int64` in Silver
    use float to handle nullable integers. This is a deliberate design decision
    documented in RULES.md §2.6.
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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLAssayGoldSchema(pa.DataFrameModel):
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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLCellLineGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Cell Line in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    cell_id: Series[str] = pa.Field(nullable=False)

    # Core metadata
    cell_name: Series[str] = pa.Field(nullable=False)
    cell_description: Series[str] = pa.Field(nullable=True)

    # Source information
    cell_source_tissue: Series[str] = pa.Field(nullable=True)
    cell_source_organism: Series[str] = pa.Field(nullable=True)
    cell_source_taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name

    # External identifiers
    cellosaurus_id: Series[str] = pa.Field(nullable=True)
    cl_lincs_id: Series[str] = pa.Field(nullable=True)
    efo_id: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLCompoundRecordGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Compound Record in Gold layer."""

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

    # Primary identifier
    record_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver

    # Foreign keys
    molecule_id: Series[str] = pa.Field(nullable=False)
    publication_id: Series[str] = pa.Field(nullable=False)

    # Original compound names from document
    compound_key: Series[str] = pa.Field(nullable=True)
    compound_name: Series[str] = pa.Field(nullable=True)

    # Source information
    src_id: Series[float] = pa.Field(nullable=False, coerce=True)  # int64 in Silver
    src_compound_id: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLDocumentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Document in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    publication_id: Series[str] = pa.Field(nullable=False)
    # Cross-reference IDs (prefixed, for linking publications across providers)
    publication_doi: Series[str] = pa.Field(nullable=True)
    publication_pmid: Series[str] = pa.Field(nullable=True)
    publication_pmc_id: Series[str] = pa.Field(nullable=True)
    # Cross-reference IDs (raw identifiers from Silver)
    doi: Series[str] = pa.Field(nullable=True)
    pmc_id: Series[str] = pa.Field(nullable=True)
    pmid: Series[str] = pa.Field(nullable=True)
    # patent_id excluded from unified publication schema
    title: Series[str] = pa.Field(nullable=True)
    authors: Series[str] = pa.Field(nullable=True)
    abstract: Series[str] = pa.Field(nullable=True)
    affiliation_list: Series[str] = pa.Field(nullable=True)  # JSON array
    author_keys: Series[str] = pa.Field(nullable=True)  # Pipe-delimited Surname_F keys
    author_orcids: Series[str] = pa.Field(nullable=True)
    publication_type: Series[str] = pa.Field(nullable=True)
    publication_type_unified: Series[str] = pa.Field(nullable=True)
    publication_subclass: Series[str] = pa.Field(nullable=True)
    publication_class: Series[str] = pa.Field(nullable=True)
    publication_date: Series[str] = pa.Field(nullable=True)
    journal: Series[str] = pa.Field(nullable=True)
    publication_year: Series[float] = pa.Field(nullable=True, coerce=True)
    volume: Series[str] = pa.Field(nullable=True)
    issue: Series[str] = pa.Field(nullable=True)
    page_first: Series[str] = pa.Field(nullable=True)
    page_last: Series[str] = pa.Field(nullable=True)
    language: Series[str] = pa.Field(nullable=True)
    is_oa: Series[bool] = pa.Field(nullable=True, coerce=True)
    citations_received: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    citations_made: Series[float] = pa.Field(nullable=True, ge=0, coerce=True)
    src_id: Series[float] = pa.Field(nullable=True, coerce=True)

    # ChEMBL release metadata
    chembl_release: Series[str] = pa.Field(nullable=True)
    creation_date: Series[str] = pa.Field(nullable=True)

    # System field (per SYSTEM_FIELDS_PREFIX)
    source: Series[str] = pa.Field(nullable=True, alias="_source")

    # Lookup metadata
    # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
    # _original_id: Original identifier used for lookup (publication_id for direct)
    lookup_method: Series[str] = pa.Field(nullable=True, alias="_lookup_method")
    original_id: Series[str] = pa.Field(nullable=True, alias="_original_id")

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

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
    publication_id: Series[str] = pa.Field(nullable=False)
    term: Series[str] = pa.Field(nullable=False)
    term_type: Series[str] = pa.Field(nullable=False)

    # MeSH-specific fields
    mesh_id: Series[str] = pa.Field(nullable=True)
    qualifier: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLMoleculeGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Molecule in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    molecule_id: Series[str] = pa.Field(nullable=False)
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
    logp: Series[float] = pa.Field(nullable=True, coerce=True)
    logp_method: Series[str] = pa.Field(nullable=True)
    molecular_weight: Series[float] = pa.Field(nullable=True, coerce=True)
    mw_freebase: Series[float] = pa.Field(nullable=True, coerce=True)
    polar_surface_area: Series[float] = pa.Field(nullable=True, coerce=True)
    rotatable_bond_count: Series[float] = pa.Field(nullable=True, coerce=True)
    ro5_violation_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    heavy_atom_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    aromatic_ring_count: Series[float] = pa.Field(nullable=True, coerce=True)  # int64
    hba_count: Series[float] = pa.Field(nullable=True, coerce=True)
    hbd_count: Series[float] = pa.Field(nullable=True, coerce=True)
    qed_score: Series[float] = pa.Field(nullable=True, coerce=True)
    molecular_formula: Series[str] = pa.Field(nullable=True)
    ro3_pass: Series[str] = pa.Field(nullable=True)
    # Flattened Structures (unified naming without structure_ prefix)
    canonical_smiles: Series[str] = pa.Field(nullable=True)
    standard_inchi: Series[str] = pa.Field(nullable=True)
    inchi_key: Series[str] = pa.Field(nullable=True)

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Lineage metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLTargetGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
    target_id: Series[str] = pa.Field(nullable=False)
    pref_name: Series[str] = pa.Field(nullable=True)
    target_type: Series[str] = pa.Field(nullable=True)
    organism: Series[str] = pa.Field(nullable=True)
    taxonomy_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # Standardized name
    organism_class: Series[str] = pa.Field(nullable=True)
    species_group_flag: Series[bool] = pa.Field(nullable=True)
    description: Series[str] = pa.Field(nullable=True)
    downgraded: Series[bool] = pa.Field(nullable=True, coerce=True)
    pipeline_stages: Series[str] = pa.Field(nullable=True)
    target_components: Series[str] = pa.Field(nullable=True)
    cross_references: Series[str] = pa.Field(nullable=True)
    target_component_synonyms: Series[str] = pa.Field(nullable=True)
    component_accessions: Series[str] = pa.Field(nullable=True)  # list[str]
    primary_component_id: Series[float] = pa.Field(
        nullable=True, coerce=True
    )  # int → float (nullable)
    component_ids: Series[str] = pa.Field(nullable=True)  # list[int]
    component_types: Series[str] = pa.Field(nullable=True)  # list[str]
    component_descriptions: Series[str] = pa.Field(nullable=True)
    component_relationships: Series[str] = pa.Field(nullable=True)  # list[str]

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLTargetComponentGoldSchema(pa.DataFrameModel):
    """Schema for ChEMBL Target Component in Gold layer."""

    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)
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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLTissueGoldSchema(pa.DataFrameModel):
    """Gold schema for ChEMBL Tissue entity.

    Validates:
    - tissue_id: Required, CHEMBL format (aliased from tissue_chembl_id by transformer)
    - pref_name: Required, non-empty
    - Ontology IDs: Optional, format validation
    """

    # System fields
    entity_id: Series[str] = pa.Field(nullable=False)
    content_hash: Series[str] = pa.Field(nullable=False)

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
    bto_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^BTO:\d{7}$",
        description="BRENDA Tissue Ontology ID",
    )
    caloha_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^TS-\d{4}$",
        description="CALIPHO ID",
    )
    efo_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^EFO:\d{7}$",
        description="Experimental Factor Ontology ID",
    )
    uberon_id: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^UBERON:\d{7}$",
        description="Uberon Ontology ID",
    )

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


class ChEMBLSubcellularFractionGoldSchema(pa.DataFrameModel):
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
    content_hash: Series[str] = pa.Field(nullable=False)

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

    # DQ fields
    dq_warn: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_warn")
    dq_error: Series[bool] = pa.Field(nullable=False, default=False, alias="_dq_error")

    # Metadata
    run_id: Series[str] = pa.Field(nullable=False, alias="_run_id")
    run_type: Series[str] = pa.Field(nullable=False, alias="_run_type")
    source_batch_id: Series[str] = pa.Field(nullable=True, alias="_source_batch_id")
    ingestion_ts: Series[str] = pa.Field(nullable=False, alias="_ingestion_ts")
    index: Series[int] = pa.Field(nullable=False, alias="_index")

    class Config:
        """Pandera configuration for strict schema validation."""

        strict = True


__all__ = [
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
    "ChEMBLSubcellularFractionGoldSchema",
    "ChEMBLTargetComponentGoldSchema",
    "ChEMBLTargetGoldSchema",
    "ChEMBLTissueGoldSchema",
]
