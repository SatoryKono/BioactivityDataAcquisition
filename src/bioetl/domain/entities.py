"""Domain entities for BioETL.

Defines rich domain objects with invariants and business logic.
Implements part of the Domain Layer (RULES.md §1).

These entities are distinct from:
- DTOs/TypedDicts (used for serialization/transport)
- Infrastructure Schemas (PyArrow/Pandera used for validation)

Design Principles:
- Immutable (frozen dataclasses)
- Validated on construction (__post_init__)
- Pure Python (no external dependencies)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from bioetl.domain.types import BatchID, ContentHash, EntityID, RunID, RunType


@dataclass(frozen=True, kw_only=True)
class BaseEntity:
    """Base class for all domain entities.

    Contains system fields required for lineage and versioning.
    """

    entity_id: EntityID
    content_hash: ContentHash

    # Lineage Metadata
    run_id: RunID
    run_type: RunType
    source_batch_id: BatchID | None = None  # None when batch context unavailable
    ingestion_ts: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.entity_id:
            raise ValueError("Entity ID cannot be empty")
        if not self.content_hash:
            raise ValueError("Content hash cannot be empty")


@dataclass(frozen=True, kw_only=True)
class Activity(BaseEntity):
    """Represents a bioactivity measurement (ChEMBL Activity).

    Contains all fields from ChEMBL activity API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/activity
    """

    # Primary identifier
    activity_id: str

    # Core identifiers
    molecule_chembl_id: str
    target_chembl_id: str | None = None
    assay_chembl_id: str | None = None
    document_chembl_id: str | None = None
    record_id: int | None = None
    src_id: int | None = None

    # Molecule data
    canonical_smiles: str | None = None
    molecule_pref_name: str | None = None
    parent_molecule_chembl_id: str | None = None

    # Target data
    target_pref_name: str | None = None
    target_organism: str | None = None
    target_tax_id: str | None = None

    # Assay data
    assay_type: str | None = None
    assay_description: str | None = None
    assay_variant_accession: str | None = None
    assay_variant_mutation: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_endpoint: str | None = None
    bao_format: str | None = None
    bao_label: str | None = None

    # Raw activity values
    type: str | None = None
    value: float | None = None
    units: str | None = None
    relation: str | None = None
    upper_value: float | None = None
    text_value: str | None = None

    # Standardized activity values
    standard_type: str | None = None
    standard_value: float | None = None
    standard_units: str | None = None
    standard_relation: str | None = None
    standard_upper_value: float | None = None
    standard_text_value: str | None = None
    standard_flag: int | None = None

    # Derived metrics
    pchembl_value: float | None = None

    # Ligand efficiency metrics (flattened from ChEMBL API dict)
    ligand_efficiency_bei: float | None = None  # Binding Efficiency Index
    ligand_efficiency_le: float | None = None  # Ligand Efficiency
    ligand_efficiency_lle: float | None = None  # Lipophilic Ligand Efficiency
    ligand_efficiency_sei: float | None = None  # Surface Efficiency Index

    # Units ontology
    qudt_units: str | None = None
    uo_units: str | None = None

    # Document/Publication data
    document_journal: str | None = None
    document_year: int | None = None

    # Quality annotations
    activity_comment: str | None = None
    data_validity_comment: str | None = None
    data_validity_description: str | None = None
    potential_duplicate: int | None = None

    # Action type (flattened from ChEMBL API nested structure)
    action_type_action_type: str | None = None  # Type of action (INHIBITOR, AGONIST, etc.)
    action_type_description: str | None = None  # Description of the action type
    action_type_parent_type: str | None = None  # Higher-level grouping (nullable)

    # Activity properties
    activity_properties: str | None = None  # JSON string of list
    toid: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ID is required")
        self._validate_pchembl_value()

    def _validate_pchembl_value(self) -> None:
        """Validate pchembl_value is non-negative if present."""
        if self.pchembl_value is not None and self.pchembl_value < 0:
            raise ValueError(
                f"pChemBL value must be non-negative, got {self.pchembl_value}"
            )


@dataclass(frozen=True, kw_only=True)
class Compound(BaseEntity):
    """Represents a chemical compound (PubChem Compound)."""

    cid: str
    molecular_formula: str | None = None
    molecular_weight: str | None = None  # Kept as string to preserve precision/format

    # Structure representations
    canonical_smiles: str | None = None
    isomeric_smiles: str | None = None
    inchi: str | None = None
    inchikey: str | None = None
    iupac_name: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.cid:
            raise ValueError("Compound CID is required")

        # Invariant: At least one structural representation should be present
        if not any([self.canonical_smiles, self.isomeric_smiles, self.inchi]):
            raise ValueError(
                "Compound must have at least one structural identifier (SMILES/InChI)"
            )


@dataclass(frozen=True, kw_only=True)
class Protein(BaseEntity):
    """Represents a protein target (UniProt)."""

    accession: str
    entry_name: str
    protein_name: str
    gene_names: list[str] = field(default_factory=list)
    organism_id: int | None = None
    sequence_length: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.accession:
            raise ValueError("Protein accession is required")

        if self.sequence_length is not None and self.sequence_length <= 0:
            raise ValueError(
                f"Sequence length must be positive, got {self.sequence_length}"
            )


@dataclass(frozen=True, kw_only=True)
class Publication(BaseEntity):
    """Represents a scientific publication from PubMed.

    Contains comprehensive metadata extracted from PubMed XML via Entrez API.
    See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
    """

    # Primary identifier
    pmid: str
    doi: str | None = None

    # Title and abstract
    title: str | None = None
    abstract: str | None = None

    # Journal information
    journal: str | None = None
    journal_abbrev: str | None = None
    issn: str | None = None
    volume: str | None = None
    issue: str | None = None
    pages: str | None = None

    # Authors
    authors: list[str] = field(default_factory=list)

    # Dates (stored as ISO strings YYYY-MM-DD or partial YYYY-MM, YYYY)
    pub_date: str | None = None  # Publication date
    pub_year: int | None = None  # Publication year (for partitioning)
    accepted_date: str | None = None  # Date accepted
    received_date: str | None = None  # Date received
    revised_date: str | None = None  # Date revised
    epub_date: str | None = None  # Electronic publication date

    # Classification
    publication_types: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    mesh_terms: list[str] = field(default_factory=list)

    # Additional metadata
    language: str | None = None
    country: str | None = None
    pmc_id: str | None = None  # PubMed Central ID

    # Legacy field (kept for backward compatibility)
    publication_year: int | None = None  # Alias for pub_year

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.pmid:
            raise ValueError("Publication PMID is required")


@dataclass(frozen=True, kw_only=True)
class Document(BaseEntity):
    """Represents a scientific document/publication (ChEMBL Document).

    Contains all fields from ChEMBL document API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/document
    """

    # Primary identifier
    document_chembl_id: str

    # Publication identifiers
    pubmed_id: int | None = None
    doi: str | None = None
    patent_id: str | None = None

    # Core metadata
    title: str | None = None
    authors: str | None = None  # Combined authors string
    abstract: str | None = None
    doc_type: str | None = None  # PUBLICATION, PATENT, etc.

    # Journal information
    journal: str | None = None
    journal_full_title: str | None = None
    year: int | None = None
    volume: str | None = None
    issue: str | None = None
    first_page: str | None = None
    last_page: str | None = None

    # Source information
    src_id: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.document_chembl_id:
            raise ValueError("Document ChEMBL ID is required")
        if self.year is not None and (self.year < 1800 or self.year > 2100):
            raise ValueError(f"Year must be between 1800-2100, got {self.year}")


@dataclass(frozen=True, kw_only=True)
class Target(BaseEntity):
    """Represents a biological target (ChEMBL Target).

    Contains all fields from ChEMBL target API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/target
    """

    # Primary identifier
    target_chembl_id: str

    # Core metadata
    pref_name: str | None = None
    target_type: str | None = None  # SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM, etc.
    organism: str | None = None
    tax_id: int | None = None
    species_group_flag: bool | None = None
    description: str | None = None  # General target description
    downgraded: bool | None = None  # Flag for deprecated/downgraded records

    # Optional fields (present for specific target types)
    dap_id: int | None = None  # Drug-Affinity Panel ID (if available)
    pipeline_stages: str | None = None  # JSON string (for complexes/families)
    target_constraints: str | None = None  # JSON string (if available)

    # Complex fields (JSON serialized)
    target_components: str | None = None  # JSON string of array
    target_component_synonyms: str | None = None  # JSON string of aggregated synonyms
    cross_references: str | None = None  # JSON string of array

    # Flattened component fields (aggregated lists)
    component_accessions: list[str] | None = None
    component_ids: list[int] | None = None
    component_types: list[str] | None = None
    component_relationships: list[str] | None = None
    component_descriptions: list[str] | None = None
    component_organisms: list[str] | None = None  # Organisms from components
    component_tax_ids: list[int] | None = None  # Tax IDs from components

    # Note: protein_classifications are NOT available in /target endpoint.
    # They are only available via /target_component endpoint (TargetComponent entity).

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.target_chembl_id:
            raise ValueError("Target ChEMBL ID is required")


@dataclass(frozen=True, kw_only=True)
class TargetComponent(BaseEntity):
    """Represents a target component (ChEMBL Target Component).

    Contains all fields from ChEMBL target_component API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/target_component
    """

    # Primary identifier
    component_id: int

    # Core metadata
    accession: str | None = None
    component_type: str | None = None
    description: str | None = None
    organism: str | None = None
    tax_id: int | None = None

    # Complex fields (JSON serialized)
    target_component_synonyms: str | None = None  # JSON string of list
    target_component_xrefs: str | None = None  # JSON string of list
    protein_classifications: str | None = None  # JSON string of list (forensic)

    # Flattened fields (extracted from protein_classifications)
    protein_classification_ids: list[int] | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.component_id:
            raise ValueError("Component ID is required")


@dataclass(frozen=True, kw_only=True)
class Molecule(BaseEntity):
    """Represents a chemical compound (ChEMBL Molecule).

    Contains all fields from ChEMBL molecule API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/molecule
    """

    # Primary identifier
    molecule_chembl_id: str

    # Core metadata
    pref_name: str | None = None
    molecule_type: str | None = None  # Small molecule, Protein, Antibody, etc.
    structure_type: str | None = None  # MOL, NONE, SEQ, BOTH
    max_phase: int | None = None  # Clinical phase 0-4
    first_approval: int | None = None

    # Flags
    oral: bool | None = None
    parenteral: bool | None = None
    topical: bool | None = None
    black_box_warning: int | None = None
    natural_product: int | None = None
    first_in_class: int | None = None
    prodrug: int | None = None
    therapeutic_flag: bool | None = None
    withdrawn_flag: bool | None = None
    inorganic_flag: int | None = None
    polymer_flag: int | None = None
    chirality: int | None = None  # -1 (single), 0 (achiral), 1 (racemic), 2 (mixture)
    dosed_ingredient: int | None = None
    availability_type: int | None = None  # -2 to 2

    # Note: withdrawn_year, withdrawn_country, withdrawn_reason are not available
    # in the /molecule endpoint. Use /drug_warning endpoint for detailed info.

    # USAN naming
    usan_stem: str | None = None
    usan_stem_definition: str | None = None
    usan_substem: str | None = None
    usan_year: int | None = None

    # Other metadata
    helm_notation: str | None = None
    molecule_species: str | None = None  # ACID, BASE, NEUTRAL, ZWITTERION

    # Complex fields (JSON serialized)
    molecule_hierarchy: str | None = None  # JSON string
    molecule_properties: str | None = None  # JSON string
    molecule_structures: str | None = None  # JSON string
    molecule_synonyms: str | None = None  # JSON string
    cross_references: str | None = None  # JSON string
    atc_classifications: str | None = None  # JSON string

    # Flattened Hierarchy
    hierarchy_parent_chembl_id: str | None = None
    hierarchy_active_chembl_id: str | None = None
    hierarchy_child_chembl_id: str | None = None  # For parent molecules

    # Flattened Properties
    property_alogp: float | None = None
    property_mw_freebase: float | None = None
    property_full_mwt: float | None = None
    property_hba: int | None = None
    property_hbd: int | None = None
    property_psa: float | None = None
    property_rtb: int | None = None
    property_ro5_violations: int | None = None
    property_heavy_atoms: int | None = None
    property_aromatic_rings: int | None = None
    property_qed_weighted: float | None = None
    # Note: property_acd_logd, property_acd_logp, property_acd_most_apka,
    # property_acd_most_bpka are not available in the public ChEMBL API
    property_full_molformula: str | None = None
    property_ro3_pass: str | None = None  # "Y" or "N"

    # Flattened Structures
    structure_canonical_smiles: str | None = None
    structure_standard_inchi: str | None = None
    structure_standard_inchi_key: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ChEMBL ID is required")
        if self.max_phase is not None and not (0 <= self.max_phase <= 4):
            raise ValueError(f"max_phase must be 0-4, got {self.max_phase}")


@dataclass(frozen=True, kw_only=True)
class Assay(BaseEntity):
    """Represents a bioassay definition (ChEMBL Assay).

    Contains all fields from ChEMBL assay API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/assay
    """

    # Primary identifier
    assay_chembl_id: str

    # Core identifiers
    target_chembl_id: str | None = None
    document_chembl_id: str | None = None
    cell_chembl_id: str | None = None
    tissue_chembl_id: str | None = None
    src_id: int | None = None
    src_assay_id: str | None = None
    aidx: str | None = None

    # Assay classification
    assay_type: str | None = None
    assay_type_description: str | None = None
    assay_category: str | None = None
    assay_test_type: str | None = None
    assay_group: str | None = None

    # Biological context
    assay_organism: str | None = None
    assay_tax_id: int | None = None
    assay_cell_type: str | None = None
    assay_tissue: str | None = None
    assay_strain: str | None = None
    assay_subcellular_fraction: str | None = None

    # BAO (BioAssay Ontology) annotations
    bao_format: str | None = None
    bao_label: str | None = None

    # Description and confidence
    description: str | None = None
    confidence_score: int | None = None
    confidence_description: str | None = None
    relationship_type: str | None = None
    relationship_description: str | None = None

    # Additional metadata
    assay_pref_name: str | None = None  # Preferred assay name (if available)
    score: float | None = None  # Assay score (distinct from confidence_score)

    # Variant information (flattened from ChEMBL API nested structure)
    variant_accession: str | None = None  # UniProt accession
    variant_isoform: str | None = None  # Isoform identifier
    variant_mutation: str | None = None  # Mutation description (e.g., V600E)
    variant_organism: str | None = None  # Organism name
    variant_sequence: str | None = None  # Amino acid sequence
    variant_tax_id: int | None = None  # NCBI Taxonomy ID
    # Forensic: original JSON
    variant_sequence_json: str | None = None

    # Complex fields (stored as JSON strings)
    assay_classifications: str | None = None  # JSON string of list
    assay_parameters: str | None = None  # JSON string of list

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.assay_chembl_id:
            raise ValueError("Assay ChEMBL ID is required")
        if self.confidence_score is not None and not (0 <= self.confidence_score <= 9):
            raise ValueError(
                f"Confidence score must be 0-9, got {self.confidence_score}"
            )
