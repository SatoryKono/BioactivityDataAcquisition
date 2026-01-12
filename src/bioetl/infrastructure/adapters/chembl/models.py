"""Pydantic models for ChEMBL API responses.

These models provide type-safe parsing and validation for ChEMBL API responses.
They are infrastructure-layer models (not domain models) for raw API data.

Naming convention:
- *Response: Raw API response structure
- *Record: Individual record within a response

Configuration:
- extra='ignore': Ignores unknown fields from API
- populate_by_name=True: Allows both field names and aliases

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# === Shared Models ===


class LigandEfficiency(BaseModel):
    """Ligand efficiency metrics for an activity record."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    bei: str | None = Field(default=None, description="Binding Efficiency Index")
    le: str | None = Field(default=None, description="Ligand Efficiency")
    lle: str | None = Field(default=None, description="Lipophilic Ligand Efficiency")
    sei: str | None = Field(default=None, description="Surface Efficiency Index")


class ActionType(BaseModel):
    """Action type details for an activity record."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    action_type: str | None = Field(default=None, description="Action type name")
    description: str | None = Field(default=None, description="Action description")
    parent_type: str | None = Field(default=None, description="Parent action type")


class ChemblPageMeta(BaseModel):
    """Pagination metadata from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    limit: int = Field(description="Number of records per page")
    offset: int = Field(description="Current offset")
    total_count: int = Field(description="Total number of records available")
    next: str | None = Field(default=None, description="Next page URL")
    previous: str | None = Field(default=None, description="Previous page URL")


# === Activity Models ===


class ChemblActivityRecord(BaseModel):
    """Individual activity record from ChEMBL API.

    Represents a single bioactivity measurement from the ChEMBL database.
    Maps to the 'activities' array in the API response.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    activity_id: int = Field(description="Primary activity identifier")

    # Foreign Keys
    assay_chembl_id: str = Field(description="ChEMBL ID of the assay")
    molecule_chembl_id: str = Field(description="ChEMBL ID of the molecule")
    target_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the target"
    )
    document_chembl_id: str | None = Field(
        default=None, description="ChEMBL ID of the source document"
    )

    # Standardized Values
    standard_relation: str | None = Field(
        default=None, description="Standardized relation operator (=, <, >, etc.)"
    )
    standard_value: str | float | None = Field(
        default=None, description="Standardized activity value"
    )
    standard_units: str | None = Field(
        default=None, description="Standardized units (nM, uM, etc.)"
    )
    standard_type: str | None = Field(
        default=None, description="Standardized measurement type (IC50, EC50, etc.)"
    )
    standard_flag: int | None = Field(
        default=None, description="Standardization flag (0 or 1)"
    )
    standard_text_value: str | None = Field(
        default=None, description="Standardized text value"
    )
    standard_upper_value: float | None = Field(
        default=None, description="Standardized upper bound"
    )

    # Derived Metrics
    pchembl_value: str | float | None = Field(
        default=None, description="-log10 of molar activity"
    )

    # Ligand Efficiency
    ligand_efficiency: LigandEfficiency | None = Field(
        default=None, description="Ligand efficiency metrics"
    )

    # Action Type
    action_type: ActionType | str | None = Field(
        default=None, description="Action type details"
    )

    # Original Values
    type: str | None = Field(default=None, description="Original measurement type")
    relation: str | None = Field(default=None, description="Original relation operator")
    value: str | float | None = Field(default=None, description="Original value")
    units: str | None = Field(default=None, description="Original units")
    text_value: str | None = Field(default=None, description="Text value")
    upper_value: float | None = Field(default=None, description="Upper bound value")

    # Data Quality
    data_validity_comment: str | None = Field(
        default=None, description="Data quality comment"
    )
    data_validity_description: str | None = Field(
        default=None, description="Data validity description"
    )
    activity_comment: str | None = Field(
        default=None, description="Activity textual comment"
    )
    potential_duplicate: int | None = Field(
        default=None, description="Duplicate flag (0 or 1)"
    )

    # Ontologies
    bao_endpoint: str | None = Field(default=None, description="BAO endpoint ID")
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")
    uo_units: str | None = Field(default=None, description="Units Ontology ID")
    qudt_units: str | None = Field(default=None, description="QUDT unit URI")

    # Source and Record Info
    src_id: int | None = Field(default=None, description="Source ID")
    record_id: int | None = Field(
        default=None, description="Foreign key to compound_record"
    )
    toid: int | None = Field(default=None, description="Test Occasion ID")

    # Assay Details (denormalized)
    assay_description: str | None = Field(default=None, description="Assay description")
    assay_type: str | None = Field(default=None, description="Assay type code")
    assay_variant_accession: str | None = Field(
        default=None, description="Assay variant accession"
    )
    assay_variant_mutation: str | None = Field(
        default=None, description="Assay variant mutation"
    )

    # Molecule Details (denormalized)
    canonical_smiles: str | None = Field(
        default=None, description="Canonical SMILES structure"
    )
    molecule_pref_name: str | None = Field(
        default=None, description="Molecule preferred name"
    )
    parent_molecule_chembl_id: str | None = Field(
        default=None, description="Parent molecule ChEMBL ID"
    )

    # Target Details (denormalized)
    target_pref_name: str | None = Field(
        default=None, description="Target preferred name"
    )
    target_organism: str | None = Field(
        default=None, description="Target organism name"
    )
    target_tax_id: str | None = Field(default=None, description="Target taxonomy ID")

    # Document Details (denormalized)
    document_journal: str | None = Field(
        default=None, description="Source journal name"
    )
    document_year: int | None = Field(default=None, description="Publication year")

    # Activity Properties (complex field)
    activity_properties: list[dict[str, Any]] | None = Field(
        default_factory=list, description="Additional activity properties"
    )


class ChemblActivityResponse(BaseModel):
    """Complete ChEMBL Activity API response.

    Represents the full response from /chembl/api/data/activity.json endpoint.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    activities: list[ChemblActivityRecord] = Field(
        default_factory=list, description="List of activity records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Assay Models ===


class ChemblAssayRecord(BaseModel):
    """Individual assay record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    assay_chembl_id: str = Field(description="ChEMBL ID of the assay")

    # Core Fields
    assay_type: str | None = Field(default=None, description="Assay type code")
    assay_type_description: str | None = Field(
        default=None, description="Assay type description"
    )
    description: str | None = Field(default=None, description="Assay description")
    assay_test_type: str | None = Field(default=None, description="Test type")
    assay_category: str | None = Field(default=None, description="Assay category")
    assay_cell_type: str | None = Field(default=None, description="Cell type used")
    assay_organism: str | None = Field(
        default=None, description="Organism in the assay"
    )
    assay_strain: str | None = Field(default=None, description="Strain used")
    assay_subcellular_fraction: str | None = Field(
        default=None, description="Subcellular fraction"
    )
    assay_tissue: str | None = Field(default=None, description="Tissue type")

    # Foreign Keys
    document_chembl_id: str | None = Field(
        default=None, description="Source document ChEMBL ID"
    )
    target_chembl_id: str | None = Field(default=None, description="Target ChEMBL ID")
    cell_chembl_id: str | None = Field(default=None, description="Cell line ChEMBL ID")
    tissue_chembl_id: str | None = Field(default=None, description="Tissue ChEMBL ID")

    # Ontology
    bao_format: str | None = Field(default=None, description="BAO format ID")
    bao_label: str | None = Field(default=None, description="BAO label")

    # Confidence
    confidence_score: int | None = Field(
        default=None, description="Target confidence score"
    )
    confidence_description: str | None = Field(
        default=None, description="Confidence description"
    )

    # Source
    src_id: int | None = Field(default=None, description="Source ID")
    src_assay_id: str | None = Field(default=None, description="Source assay ID")

    # Variants
    variant_sequence: str | None = Field(default=None, description="Variant sequence")
    assay_parameters: list[dict[str, Any]] | None = Field(
        default_factory=list, description="Assay parameters"
    )


class ChemblAssayResponse(BaseModel):
    """Complete ChEMBL Assay API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    assays: list[ChemblAssayRecord] = Field(
        default_factory=list, description="List of assay records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Molecule Models ===


class MoleculeHierarchy(BaseModel):
    """Molecule hierarchy information."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    molecule_chembl_id: str | None = Field(default=None)
    parent_chembl_id: str | None = Field(default=None)
    active_chembl_id: str | None = Field(default=None)


class MoleculeProperties(BaseModel):
    """Molecule calculated properties."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    alogp: float | None = Field(default=None, description="ALogP value")
    aromatic_rings: int | None = Field(default=None)
    cx_logd: float | None = Field(default=None)
    cx_logp: float | None = Field(default=None)
    cx_most_apka: float | None = Field(default=None)
    cx_most_bpka: float | None = Field(default=None)
    full_molformula: str | None = Field(default=None)
    full_mwt: float | None = Field(default=None)
    hba: int | None = Field(default=None, description="H-bond acceptors")
    hba_lipinski: int | None = Field(default=None)
    hbd: int | None = Field(default=None, description="H-bond donors")
    hbd_lipinski: int | None = Field(default=None)
    heavy_atoms: int | None = Field(default=None)
    molecular_species: str | None = Field(default=None)
    mw_freebase: float | None = Field(default=None)
    mw_monoisotopic: float | None = Field(default=None)
    np_likeness_score: float | None = Field(default=None)
    num_lipinski_ro5_violations: int | None = Field(default=None)
    num_ro5_violations: int | None = Field(default=None)
    psa: float | None = Field(default=None, description="Polar surface area")
    qed_weighted: float | None = Field(default=None)
    ro3_pass: str | None = Field(default=None)
    rtb: int | None = Field(default=None, description="Rotatable bonds")


class MoleculeStructures(BaseModel):
    """Molecule structure representations."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    canonical_smiles: str | None = Field(default=None)
    molfile: str | None = Field(default=None)
    standard_inchi: str | None = Field(default=None)
    standard_inchi_key: str | None = Field(default=None)


class ChemblMoleculeRecord(BaseModel):
    """Individual molecule record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    molecule_chembl_id: str = Field(description="ChEMBL ID of the molecule")

    # Core Properties
    pref_name: str | None = Field(default=None, description="Preferred name")
    max_phase: float | None = Field(default=None, description="Maximum clinical phase")
    structure_type: str | None = Field(default=None, description="Structure type")
    molecule_type: str | None = Field(default=None, description="Molecule type")
    first_approval: int | None = Field(
        default=None, description="Year of first approval"
    )

    # Flags
    therapeutic_flag: bool | None = Field(default=None)
    oral: bool | None = Field(default=None)
    parenteral: bool | None = Field(default=None)
    topical: bool | None = Field(default=None)
    black_box_warning: int | None = Field(default=None)
    natural_product: int | None = Field(default=None)
    first_in_class: int | None = Field(default=None)
    prodrug: int | None = Field(default=None)
    inorganic_flag: int | None = Field(default=None)
    polymer_flag: int | None = Field(default=None)
    withdrawn_flag: bool | None = Field(default=None)
    chirality: int | None = Field(default=None)
    availability_type: int | None = Field(default=None)

    # Complex Fields
    molecule_hierarchy: MoleculeHierarchy | None = Field(default=None)
    molecule_properties: MoleculeProperties | None = Field(default=None)
    molecule_structures: MoleculeStructures | None = Field(default=None)
    molecule_synonyms: list[dict[str, Any]] | None = Field(default_factory=list)
    cross_references: list[dict[str, Any]] | None = Field(default_factory=list)
    atc_classifications: list[str] | None = Field(default_factory=list)

    # USAN Info
    usan_year: int | None = Field(default=None)
    usan_stem: str | None = Field(default=None)
    usan_substem: str | None = Field(default=None)
    usan_stem_definition: str | None = Field(default=None)

    # Indication
    indication_class: str | None = Field(default=None)

    # Withdrawn Info
    withdrawn_year: int | None = Field(default=None)
    withdrawn_country: str | None = Field(default=None)
    withdrawn_reason: str | None = Field(default=None)
    withdrawn_class: str | None = Field(default=None)


class ChemblMoleculeResponse(BaseModel):
    """Complete ChEMBL Molecule API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    molecules: list[ChemblMoleculeRecord] = Field(
        default_factory=list, description="List of molecule records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Target Models ===


class ChemblTargetRecord(BaseModel):
    """Individual target record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    target_chembl_id: str = Field(description="ChEMBL ID of the target")

    # Core Fields
    pref_name: str | None = Field(default=None, description="Preferred name")
    target_type: str | None = Field(default=None, description="Target type")
    organism: str | None = Field(default=None, description="Target organism")
    tax_id: int | None = Field(default=None, description="Taxonomy ID")
    species_group_flag: int | None = Field(default=None)

    # Complex Fields
    target_components: list[dict[str, Any]] | None = Field(default_factory=list)
    cross_references: list[dict[str, Any]] | None = Field(default_factory=list)


class ChemblTargetResponse(BaseModel):
    """Complete ChEMBL Target API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    targets: list[ChemblTargetRecord] = Field(
        default_factory=list, description="List of target records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Document Models ===


class ChemblDocumentRecord(BaseModel):
    """Individual document record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    document_chembl_id: str = Field(description="ChEMBL ID of the document")

    # Core Fields
    doc_type: str | None = Field(default=None, description="Document type")
    title: str | None = Field(default=None, description="Document title")
    abstract: str | None = Field(default=None, description="Document abstract")
    authors: str | None = Field(default=None, description="Authors")

    # Journal Info
    journal: str | None = Field(default=None, description="Journal name")
    journal_full_title: str | None = Field(default=None)
    volume: str | None = Field(default=None)
    issue: str | None = Field(default=None)
    first_page: str | None = Field(default=None)
    last_page: str | None = Field(default=None)
    year: int | None = Field(default=None, description="Publication year")

    # External IDs
    doi: str | None = Field(default=None, description="Digital Object Identifier")
    pubmed_id: int | None = Field(default=None, description="PubMed ID")
    patent_id: str | None = Field(default=None, description="Patent ID")

    # Source
    src_id: int | None = Field(default=None, description="Source ID")


class ChemblDocumentResponse(BaseModel):
    """Complete ChEMBL Document API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    documents: list[ChemblDocumentRecord] = Field(
        default_factory=list, description="List of document records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Target Component Models ===


class ChemblTargetComponentRecord(BaseModel):
    """Individual target component record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    component_id: int = Field(description="Component ID")

    # Core Fields
    component_type: str | None = Field(default=None)
    accession: str | None = Field(default=None, description="UniProt accession")
    sequence: str | None = Field(default=None, description="Protein sequence")
    sequence_md5sum: str | None = Field(default=None)
    description: str | None = Field(default=None)
    organism: str | None = Field(default=None)
    tax_id: int | None = Field(default=None)

    # GO Classifications
    go_slims: list[dict[str, Any]] | None = Field(default_factory=list)

    # Protein Classifications
    protein_classifications: list[dict[str, Any]] | None = Field(default_factory=list)

    # Target Relations
    target_component_synonyms: list[dict[str, Any]] | None = Field(default_factory=list)
    target_component_xrefs: list[dict[str, Any]] | None = Field(default_factory=list)


class ChemblTargetComponentResponse(BaseModel):
    """Complete ChEMBL Target Component API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    target_components: list[ChemblTargetComponentRecord] = Field(
        default_factory=list, description="List of target component records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Cell Line Models ===


class ChemblCellLineRecord(BaseModel):
    """Individual cell line record from ChEMBL API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    cell_chembl_id: str = Field(description="ChEMBL ID of the cell line")

    # Core Fields
    cell_name: str | None = Field(default=None)
    cell_description: str | None = Field(default=None)
    cell_source_organism: str | None = Field(default=None)
    cell_source_tax_id: int | None = Field(default=None)
    cell_source_tissue: str | None = Field(default=None)
    cell_type: str | None = Field(default=None)

    # Identifiers
    cellosaurus_id: str | None = Field(default=None)
    clo_id: str | None = Field(default=None)
    efo_id: str | None = Field(default=None)


class ChemblCellLineResponse(BaseModel):
    """Complete ChEMBL Cell Line API response."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    cell_lines: list[ChemblCellLineRecord] = Field(
        default_factory=list, description="List of cell line records"
    )
    page_meta: ChemblPageMeta | None = Field(
        default=None, description="Pagination metadata"
    )


# === Status Response ===


# === Response Type Mapping ===

# Mapping from entity type to response class for factory usage
CHEMBL_RESPONSE_MODELS: dict[str, type[BaseModel]] = {
    "activity": ChemblActivityResponse,
    "assay": ChemblAssayResponse,
    "molecule": ChemblMoleculeResponse,
    "compound": ChemblMoleculeResponse,
    "target": ChemblTargetResponse,
    "target_component": ChemblTargetComponentResponse,
    "document": ChemblDocumentResponse,
    "cell_line": ChemblCellLineResponse,
}

# Mapping from entity type to record class for individual record validation
CHEMBL_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "activity": ChemblActivityRecord,
    "assay": ChemblAssayRecord,
    "molecule": ChemblMoleculeRecord,
    "compound": ChemblMoleculeRecord,
    "target": ChemblTargetRecord,
    "target_component": ChemblTargetComponentRecord,
    "document": ChemblDocumentRecord,
    "cell_line": ChemblCellLineRecord,
}
