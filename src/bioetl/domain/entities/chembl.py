"""ChEMBL DTO models for type-safe data transfer.

These Pydantic models provide strict validation at domain boundaries.
Unlike infrastructure models (extra='ignore'), these use extra='forbid'
to detect API changes early.

Design:
- DTOs are pure data containers (no lineage fields like run_id)
- Adapters return DTOs, transformers convert to Domain Entities
- frozen=True ensures immutability
- extra='forbid' rejects unknown fields for early API change detection

Usage:
    # In adapter (with validation)
    record = ActivityRecord.model_validate(api_response)

    # For trusted data (skip validation for performance)
    record = ActivityRecord.model_construct(**trusted_dict)

    # Convert to dict for storage
    data = record.model_dump()

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ActivityRecord(BaseModel):
    """Bioactivity measurement DTO from ChEMBL.

    Represents a single activity measurement from ChEMBL API.
    Required fields: activity_id, molecule_chembl_id.

    Example:
        >>> record = ActivityRecord(
        ...     activity_id="12345",
        ...     molecule_chembl_id="CHEMBL25",
        ...     assay_chembl_id="CHEMBL1000",
        ...     standard_type="IC50",
        ...     standard_value=5.0,
        ...     standard_units="nM",
        ... )
        >>> record.model_dump()
        {'activity_id': '12345', 'molecule_chembl_id': 'CHEMBL25', ...}
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    activity_id: str = Field(description="Unique activity identifier")

    # Core identifiers (REQUIRED: molecule_chembl_id)
    molecule_chembl_id: str = Field(description="ChEMBL ID of tested molecule")
    assay_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the assay"
    )
    target_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the target"
    )
    document_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the source document"
    )

    # Standardized activity values
    standard_type: str | None = Field(
        default=None, description="Standardized measurement type (IC50, EC50, Ki, etc.)"
    )
    standard_value: float | None = Field(
        default=None, description="Standardized activity value"
    )
    standard_units: str | None = Field(
        default=None, description="Standardized units (nM, uM, etc.)"
    )
    standard_relation: str | None = Field(
        default=None, description="Relation operator (=, <, >, etc.)"
    )
    standard_upper_value: float | None = Field(
        default=None, description="Standardized upper bound for ranges"
    )
    standard_text_value: str | None = Field(
        default=None, description="Standardized text value"
    )
    standard_flag: int | None = Field(
        default=None, description="Standardization flag (0 or 1)"
    )

    # Derived metrics
    pchembl_value: float | None = Field(
        default=None, description="-log10 of molar activity value"
    )

    # Original (non-standardized) values
    type: str | None = Field(default=None, description="Original measurement type")
    value: float | None = Field(default=None, description="Original activity value")
    units: str | None = Field(default=None, description="Original units")
    relation: str | None = Field(default=None, description="Original relation operator")
    upper_value: float | None = Field(default=None, description="Original upper bound")
    text_value: str | None = Field(default=None, description="Original text value")

    # Molecule data (denormalized)
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES structure"
    )
    molecule_pref_name: str | None = Field(
        default=None, description="Molecule preferred name"
    )
    parent_molecule_chembl_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )

    # Target data (denormalized)
    target_pref_name: str | None = Field(
        default=None, description="Target preferred name"
    )
    target_organism: str | None = Field(
        default=None, description="Target organism name"
    )
    target_tax_id: str | None = Field(default=None, description="Target taxonomy ID")

    # Assay data (denormalized)
    assay_type: str | None = Field(default=None, description="Assay type code (B/F/A)")
    assay_description: str | None = Field(
        default=None, description="Assay description text"
    )
    assay_variant_accession: str | None = Field(
        default=None, description="Variant UniProt accession"
    )
    assay_variant_mutation: str | None = Field(
        default=None, description="Variant mutation description"
    )

    # BioAssay Ontology annotations
    bao_endpoint: str | None = Field(default=None, description="BAO endpoint ID")
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")

    # Unit ontologies
    qudt_units: str | None = Field(default=None, description="QUDT unit URI")
    uo_units: str | None = Field(default=None, description="Units Ontology ID")

    # Source and record info
    src_id: int | None = Field(default=None, description="Data source ID")
    record_id: int | None = Field(
        default=None, description="FK to compound_record table"
    )
    toid: int | None = Field(default=None, description="Test Occasion ID")

    # Document data (denormalized)
    document_journal: str | None = Field(
        default=None, description="Source journal name"
    )
    document_year: int | None = Field(default=None, description="Publication year")

    # Data quality annotations
    activity_comment: str | None = Field(
        default=None, description="Activity textual comment"
    )
    data_validity_comment: str | None = Field(
        default=None, description="Data quality comment"
    )
    data_validity_description: str | None = Field(
        default=None, description="Data validity description"
    )
    potential_duplicate: int | None = Field(
        default=None, description="Potential duplicate flag"
    )

    # Ligand efficiency metrics (flattened)
    ligand_efficiency_bei: float | None = Field(
        default=None, description="Binding Efficiency Index"
    )
    ligand_efficiency_le: float | None = Field(
        default=None, description="Ligand Efficiency"
    )
    ligand_efficiency_lle: float | None = Field(
        default=None, description="Lipophilic Ligand Efficiency"
    )
    ligand_efficiency_sei: float | None = Field(
        default=None, description="Surface Efficiency Index"
    )

    # Action type (flattened)
    action_type: str | None = Field(
        default=None, description="Action type (INHIBITOR, AGONIST, etc.)"
    )
    action_type_description: str | None = Field(
        default=None, description="Action type description"
    )
    action_type_parent: str | None = Field(
        default=None, description="Parent action type"
    )

    # Complex fields (JSON serialized for forensic)
    activity_properties_json: str | None = Field(
        default=None, description="Activity properties as JSON string"
    )


class AssayRecord(BaseModel):
    """Bioassay definition DTO from ChEMBL.

    Represents a bioassay protocol from ChEMBL API.
    Required field: assay_chembl_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    assay_chembl_id: str = Field(description="Unique assay ChEMBL ID")

    # Core identifiers
    target_chembl_id: str | None = Field(default=None, description="Target ChEMBL ID")
    document_chembl_id: str | None = Field(
        default=None, description="Source document ChEMBL ID"
    )
    cell_chembl_id: str | None = Field(default=None, description="Cell line ChEMBL ID")
    tissue_chembl_id: str | None = Field(default=None, description="Tissue ChEMBL ID")
    src_id: int | None = Field(default=None, description="Data source ID")
    src_assay_id: str | None = Field(
        default=None, description="Original source assay ID"
    )
    aidx: str | None = Field(default=None, description="Assay index")

    # Assay classification
    assay_type: str | None = Field(
        default=None, description="Assay type code (B/F/A/T/P/U)"
    )
    assay_type_description: str | None = Field(
        default=None, description="Full assay type description"
    )
    assay_category: str | None = Field(default=None, description="Assay category")
    assay_test_type: str | None = Field(
        default=None, description="Test type (in vivo/in vitro)"
    )
    assay_group: str | None = Field(default=None, description="Assay group")

    # Biological context
    assay_organism: str | None = Field(
        default=None, description="Organism used in assay"
    )
    assay_tax_id: int | None = Field(
        default=None, description="NCBI Taxonomy ID for assay organism"
    )
    assay_cell_type: str | None = Field(default=None, description="Cell type used")
    assay_tissue: str | None = Field(default=None, description="Tissue type used")
    assay_strain: str | None = Field(default=None, description="Strain used")
    assay_subcellular_fraction: str | None = Field(
        default=None, description="Subcellular fraction"
    )

    # BioAssay Ontology annotations
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")

    # Description and confidence
    description: str | None = Field(default=None, description="Full assay description")
    confidence_score: int | None = Field(
        default=None, description="Target confidence score (0-9)"
    )
    confidence_description: str | None = Field(
        default=None, description="Confidence level description"
    )
    relationship_type: str | None = Field(
        default=None, description="Target-assay relationship type"
    )
    relationship_description: str | None = Field(
        default=None, description="Relationship description"
    )

    # Additional metadata
    assay_pref_name: str | None = Field(
        default=None, description="Preferred assay name"
    )
    score: float | None = Field(
        default=None, description="Assay score (distinct from confidence)"
    )

    # Variant information (flattened)
    variant_accession: str | None = Field(
        default=None, description="Variant UniProt accession"
    )
    variant_isoform: str | None = Field(default=None, description="Variant isoform")
    variant_mutation: str | None = Field(
        default=None, description="Variant mutation (e.g., V600E)"
    )
    variant_organism: str | None = Field(default=None, description="Variant organism")
    variant_sequence: str | None = Field(
        default=None, description="Variant amino acid sequence"
    )
    variant_tax_id: int | None = Field(
        default=None, description="Variant NCBI Taxonomy ID"
    )

    # Complex fields (JSON serialized)
    assay_classifications_json: str | None = Field(
        default=None, description="Assay classifications as JSON"
    )
    assay_parameters_json: str | None = Field(
        default=None, description="Assay parameters as JSON"
    )
    variant_sequence_json: str | None = Field(
        default=None, description="Original variant sequence as JSON"
    )


class MoleculeRecord(BaseModel):
    """Chemical compound DTO from ChEMBL.

    Represents a molecule/compound from ChEMBL API.
    Required field: molecule_chembl_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    molecule_chembl_id: str = Field(description="Unique molecule ChEMBL ID")

    # Core metadata
    pref_name: str | None = Field(default=None, description="Preferred molecule name")
    molecule_type: str | None = Field(
        default=None, description="Type (Small molecule, Protein, Antibody, etc.)"
    )
    structure_type: str | None = Field(
        default=None, description="Structure type (MOL, NONE, SEQ, BOTH)"
    )
    max_phase: int | None = Field(
        default=None, description="Maximum clinical phase (0-4)"
    )
    first_approval: int | None = Field(
        default=None, description="Year of first approval"
    )

    # Flags
    oral: bool | None = Field(default=None, description="Oral administration flag")
    parenteral: bool | None = Field(
        default=None, description="Parenteral administration flag"
    )
    topical: bool | None = Field(
        default=None, description="Topical administration flag"
    )
    black_box_warning: int | None = Field(
        default=None, description="Black box warning flag"
    )
    natural_product: int | None = Field(
        default=None, description="Natural product flag"
    )
    first_in_class: int | None = Field(default=None, description="First in class flag")
    prodrug: int | None = Field(default=None, description="Prodrug flag")
    therapeutic_flag: bool | None = Field(
        default=None, description="Therapeutic use flag"
    )
    withdrawn_flag: bool | None = Field(default=None, description="Withdrawn drug flag")
    inorganic_flag: int | None = Field(
        default=None, description="Inorganic compound flag"
    )
    polymer_flag: int | None = Field(default=None, description="Polymer flag")
    chirality: int | None = Field(
        default=None,
        description="Chirality (-1 single, 0 achiral, 1 racemic, 2 mixture)",
    )
    dosed_ingredient: int | None = Field(
        default=None, description="Dosed ingredient flag"
    )
    availability_type: int | None = Field(
        default=None, description="Availability type (-2 to 2)"
    )

    # USAN naming
    usan_stem: str | None = Field(default=None, description="USAN stem")
    usan_stem_definition: str | None = Field(
        default=None, description="USAN stem definition"
    )
    usan_substem: str | None = Field(default=None, description="USAN substem")
    usan_year: int | None = Field(default=None, description="USAN year")

    # Other metadata
    helm_notation: str | None = Field(
        default=None, description="HELM notation for biopolymers"
    )
    molecule_species: str | None = Field(
        default=None, description="Species (ACID, BASE, NEUTRAL, ZWITTERION)"
    )

    # Flattened hierarchy
    hierarchy_parent_chembl_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )
    hierarchy_active_chembl_id: str | None = Field(
        default=None, description="Active form ChEMBL ID"
    )
    hierarchy_child_chembl_id: str | None = Field(
        default=None, description="Child molecule ChEMBL ID"
    )

    # Flattened properties
    property_alogp: float | None = Field(default=None, description="ALogP value")
    property_mw_freebase: float | None = Field(
        default=None, description="Molecular weight (freebase)"
    )
    property_full_mwt: float | None = Field(
        default=None, description="Full molecular weight"
    )
    property_hba: int | None = Field(default=None, description="H-bond acceptor count")
    property_hbd: int | None = Field(default=None, description="H-bond donor count")
    property_psa: float | None = Field(default=None, description="Polar surface area")
    property_rtb: int | None = Field(default=None, description="Rotatable bond count")
    property_ro5_violations: int | None = Field(
        default=None, description="Rule of 5 violations"
    )
    property_heavy_atoms: int | None = Field(
        default=None, description="Heavy atom count"
    )
    property_aromatic_rings: int | None = Field(
        default=None, description="Aromatic ring count"
    )
    property_qed_weighted: float | None = Field(
        default=None, description="QED weighted score"
    )
    property_full_molformula: str | None = Field(
        default=None, description="Full molecular formula"
    )
    property_ro3_pass: str | None = Field(
        default=None, description="Rule of 3 pass (Y/N)"
    )

    # Flattened structures
    structure_canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES"
    )
    structure_standard_inchi: str | None = Field(
        default=None, description="Standard InChI"
    )
    structure_standard_inchi_key: str | None = Field(
        default=None, description="Standard InChI Key"
    )

    # Complex fields (JSON serialized)
    molecule_hierarchy_json: str | None = Field(
        default=None, description="Molecule hierarchy as JSON"
    )
    molecule_properties_json: str | None = Field(
        default=None, description="Molecule properties as JSON"
    )
    molecule_structures_json: str | None = Field(
        default=None, description="Molecule structures as JSON"
    )
    molecule_synonyms_json: str | None = Field(
        default=None, description="Molecule synonyms as JSON"
    )
    cross_references_json: str | None = Field(
        default=None, description="Cross references as JSON"
    )
    atc_classifications_json: str | None = Field(
        default=None, description="ATC classifications as JSON"
    )


class TargetRecord(BaseModel):
    """Biological target DTO from ChEMBL.

    Represents a drug target from ChEMBL API.
    Required field: target_chembl_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    target_chembl_id: str = Field(description="Unique target ChEMBL ID")

    # Core metadata
    pref_name: str | None = Field(default=None, description="Preferred target name")
    target_type: str | None = Field(
        default=None,
        description="Type (SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM, etc.)",
    )
    organism: str | None = Field(default=None, description="Target organism")
    tax_id: int | None = Field(default=None, description="NCBI Taxonomy ID")
    species_group_flag: bool | None = Field(
        default=None, description="Species group flag"
    )
    description: str | None = Field(default=None, description="Target description")
    downgraded: bool | None = Field(
        default=None, description="Deprecated/downgraded flag"
    )

    # Optional fields
    dap_id: int | None = Field(default=None, description="Drug-Affinity Panel ID")
    pipeline_stages: str | None = Field(
        default=None, description="Pipeline stages JSON"
    )
    target_constraints: str | None = Field(
        default=None, description="Target constraints JSON"
    )

    # Flattened component fields
    component_accessions: list[str] | None = Field(
        default=None, description="Component UniProt accessions"
    )
    component_ids: list[int] | None = Field(default=None, description="Component IDs")
    component_types: list[str] | None = Field(
        default=None, description="Component types"
    )
    component_relationships: list[str] | None = Field(
        default=None, description="Component relationships"
    )
    component_descriptions: list[str] | None = Field(
        default=None, description="Component descriptions"
    )
    component_organisms: list[str] | None = Field(
        default=None, description="Component organisms"
    )
    component_tax_ids: list[int] | None = Field(
        default=None, description="Component taxonomy IDs"
    )

    # Complex fields (JSON serialized)
    target_components_json: str | None = Field(
        default=None, description="Target components as JSON"
    )
    target_component_synonyms_json: str | None = Field(
        default=None, description="Component synonyms as JSON"
    )
    cross_references_json: str | None = Field(
        default=None, description="Cross references as JSON"
    )


class DocumentRecord(BaseModel):
    """Scientific document DTO from ChEMBL.

    Represents a publication/document from ChEMBL API.
    Required field: document_chembl_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    document_chembl_id: str = Field(description="Unique document ChEMBL ID")

    # Publication identifiers
    pubmed_id: int | None = Field(default=None, description="PubMed ID")
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    patent_id: str | None = Field(default=None, description="Patent ID")

    # Core metadata
    title: str | None = Field(default=None, description="Document title")
    authors: str | None = Field(default=None, description="Combined authors string")
    abstract: str | None = Field(default=None, description="Document abstract")
    doc_type: str | None = Field(
        default=None, description="Type (PUBLICATION, PATENT, etc.)"
    )

    # Journal information
    journal: str | None = Field(default=None, description="Journal name")
    journal_full_title: str | None = Field(
        default=None, description="Full journal title"
    )
    year: int | None = Field(default=None, description="Publication year")
    volume: str | None = Field(default=None, description="Volume number")
    issue: str | None = Field(default=None, description="Issue number")
    first_page: str | None = Field(default=None, description="First page")
    last_page: str | None = Field(default=None, description="Last page")

    # Source information
    src_id: int | None = Field(default=None, description="Data source ID")


class DocumentTermRecord(BaseModel):
    """Document term DTO from ChEMBL.

    Represents a term (MeSH heading, keyword, concept) associated with
    a ChEMBL document. This is a derived entity extracted from Document
    records by flattening the 1:M relationship.

    Required fields: document_chembl_id, term, term_type.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # === Composite Key Fields (REQUIRED) ===
    document_chembl_id: str = Field(description="FK → Document ChEMBL ID")
    term: str = Field(min_length=1, description="Term text (e.g., 'Aspirin')")
    term_type: str = Field(
        description="Term type: MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT"
    )

    # === MeSH-specific Fields ===
    mesh_id: str | None = Field(
        default=None, description="MeSH identifier (e.g., 'D001241')"
    )
    qualifier: str | None = Field(
        default=None, description="MeSH qualifier (e.g., 'pharmacology')"
    )


class CellLineRecord(BaseModel):
    """Cell line DTO from ChEMBL.

    Represents a cell line from ChEMBL API.
    Required fields: cell_chembl_id, cell_name.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    cell_chembl_id: str = Field(description="Unique cell line ChEMBL ID")

    # Core metadata (REQUIRED)
    cell_name: str = Field(description="Cell line name")

    # Optional metadata
    cell_description: str | None = Field(
        default=None, description="Cell line description"
    )

    # Source information
    cell_source_tissue: str | None = Field(default=None, description="Source tissue")
    cell_source_organism: str | None = Field(
        default=None, description="Source organism"
    )
    cell_source_tax_id: int | None = Field(
        default=None, description="Source organism taxonomy ID"
    )

    # External identifiers
    cellosaurus_id: str | None = Field(default=None, description="Cellosaurus ID")
    cl_lincs_id: str | None = Field(default=None, description="LINCS cell line ID")
    efo_id: str | None = Field(default=None, description="EFO ontology ID")


class TargetComponentRecord(BaseModel):
    """Target component DTO from ChEMBL.

    Represents a target component from ChEMBL API.
    Required field: component_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    component_id: int = Field(description="Unique component ID")

    # Core metadata
    accession: str | None = Field(default=None, description="UniProt accession")
    component_type: str | None = Field(default=None, description="Component type")
    description: str | None = Field(default=None, description="Component description")
    organism: str | None = Field(default=None, description="Organism name")
    tax_id: int | None = Field(default=None, description="NCBI Taxonomy ID")

    # Flattened fields
    protein_classification_ids: list[int] | None = Field(
        default=None, description="Protein classification IDs"
    )

    # Complex fields (JSON serialized)
    target_component_synonyms_json: str | None = Field(
        default=None, description="Synonyms as JSON"
    )
    target_component_xrefs_json: str | None = Field(
        default=None, description="Cross references as JSON"
    )
    protein_classifications_json: str | None = Field(
        default=None, description="Protein classifications as JSON"
    )


class ProteinClassRecord(BaseModel):
    """Protein classification DTO from ChEMBL.

    Represents a protein classification hierarchy node from ChEMBL API.
    Required field: protein_class_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Primary identifier (REQUIRED)
    protein_class_id: int = Field(description="Unique protein class ID")

    # Hierarchy
    parent_id: int | None = Field(default=None, description="Parent class ID")
    class_level: int | None = Field(default=None, description="Hierarchy level (1-8)")

    # Classification data
    pref_name: str | None = Field(default=None, description="Preferred name")
    short_name: str | None = Field(default=None, description="Short name")
    protein_class_desc: str | None = Field(default=None, description="Full description")
    definition: str | None = Field(
        default=None, description="Classification definition"
    )

    # Additional metadata
    sort_order: int | None = Field(default=None, description="Sort order")
    replaced_by: int | None = Field(
        default=None, description="ID of replacement class if deprecated"
    )
    downgraded: int | None = Field(
        default=None, description="Deprecation flag (0 or 1)"
    )


__all__ = [
    "ActivityRecord",
    "AssayRecord",
    "CellLineRecord",
    "DocumentRecord",
    "DocumentTermRecord",
    "MoleculeRecord",
    "ProteinClassRecord",
    "TargetComponentRecord",
    "TargetRecord",
]
