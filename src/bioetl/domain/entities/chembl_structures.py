"""ChEMBL structural domain entities.

Contains ChemblPublication, DocumentTerm, DocumentSimilarity, Target,
TargetComponent, CellLine, Molecule, and ProteinClassification entities.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class ChemblPublication(BaseEntity):
    """Represents a scientific document/publication (ChEMBL Document).

    Maps to ChEMBL API endpoint: /document

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
            raise ValueError("ChemblPublication document_chembl_id is required")
        if self.year is not None and (self.year < 1800 or self.year > 2100):
            raise ValueError(f"Year must be between 1800-2100, got {self.year}")


@dataclass(frozen=True, kw_only=True)
class DocumentTerm(BaseEntity):
    """Represents a term associated with a ChEMBL Document.

    Terms include MeSH headings, MeSH qualifiers, keywords, and concepts
    extracted from Document records. This is a derived entity that flattens
    the 1:M relationship between documents and their associated terms.

    Source: Nested in ChEMBL API /document response (mesh_terms, keywords fields)

    Composite Key: document_chembl_id + term_type + term (normalized)
    See: https://www.ebi.ac.uk/chembl/api/data/document
    """

    # === Composite Key Fields ===
    document_chembl_id: str  # FK → Document
    term: str  # Term text (e.g., "Aspirin", "kinase inhibitor")
    term_type: str  # MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT

    # === MeSH-specific Fields ===
    mesh_id: str | None = None  # MeSH identifier (e.g., "D001241")
    qualifier: str | None = None  # MeSH qualifier (e.g., "pharmacology")

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.document_chembl_id:
            raise ValueError("Document ChEMBL ID is required")
        if not self.term:
            raise ValueError("Term text is required")
        if not self.term_type:
            raise ValueError("Term type is required")
        valid_term_types = {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"}
        if self.term_type not in valid_term_types:
            raise ValueError(
                f"term_type must be one of {valid_term_types}, got {self.term_type}"
            )


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
class CellLine(BaseEntity):
    """Represents a cell line (ChEMBL Cell Line).

    Cell lines are biological objects used for in vitro experiments.
    They have M:N relationship with Assay (via assay.cell_chembl_id FK).

    Contains all fields from ChEMBL cell_line API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/cell_line
    """

    # Primary identifier (REQUIRED)
    cell_chembl_id: str

    # Core metadata (cell_name is REQUIRED per task spec)
    cell_name: str

    # Optional metadata (API-OPTIONAL)
    cell_description: str | None = None

    # Source information (API-OPTIONAL)
    cell_source_tissue: str | None = None
    cell_source_organism: str | None = None
    cell_source_tax_id: int | None = None

    # Cell type classification (API-OPTIONAL)
    cell_type: str | None = None

    # External identifiers (API-OPTIONAL)
    cellosaurus_id: str | None = None
    clo_id: str | None = None
    cl_lincs_id: str | None = None
    efo_id: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.cell_chembl_id:
            raise ValueError("Cell ChEMBL ID is required")
        if not self.cell_name:
            raise ValueError("Cell name is required")
        if self.cell_source_tax_id is not None and self.cell_source_tax_id < 1:
            raise ValueError(
                f"cell_source_tax_id must be >= 1, got {self.cell_source_tax_id}"
            )


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

    # Flattened Structures (unified naming without structure_ prefix)
    canonical_smiles: str | None = None
    standard_inchi: str | None = None
    inchi_key: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ChEMBL ID is required")
        if self.max_phase is not None and not (0 <= self.max_phase <= 4):
            raise ValueError(f"max_phase must be 0-4, got {self.max_phase}")


def _validate_tanimoto(value: float | None, field_name: str) -> None:
    """Validate Tanimoto coefficient is in [0.0, 1.0] range."""
    if value is not None and not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be in [0.0, 1.0], got {value}")


@dataclass(frozen=True, kw_only=True)
class DocumentSimilarity(BaseEntity):
    """Represents similarity between two ChEMBL documents.

    Based on Tanimoto coefficients calculated from:
    - Molecules described in documents (mol_tani)
    - Targets described in documents (tid_tani)

    Source: ChEMBL API /document_similarity
    See: https://www.ebi.ac.uk/chembl/api/data/document_similarity
    """

    # === Primary Key ===
    sim_id: int

    # === Foreign Keys (internal document IDs) ===
    doc_1: int
    doc_2: int

    # === PubMed Identifiers ===
    pubmed_id1: int | None = None
    pubmed_id2: int | None = None

    # === Tanimoto Coefficients ===
    tid_tani: float | None = None  # Target-based
    mol_tani: float | None = None  # Molecule-based

    # === Derived Metrics (computed in transformer) ===
    avg_tani: float | None = None
    max_tani: float | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if self.sim_id <= 0:
            raise ValueError(f"sim_id must be positive, got {self.sim_id}")
        if self.doc_1 <= 0 or self.doc_2 <= 0:
            raise ValueError("doc_1 and doc_2 must be positive")
        if self.doc_1 == self.doc_2:
            raise ValueError("Document cannot be similar to itself")
        _validate_tanimoto(self.tid_tani, "tid_tani")
        _validate_tanimoto(self.mol_tani, "mol_tani")
        _validate_tanimoto(self.avg_tani, "avg_tani")
        _validate_tanimoto(self.max_tani, "max_tani")


@dataclass(frozen=True, kw_only=True)
class ProteinClassification(BaseEntity):
    """Represents a protein classification hierarchy node (ChEMBL protein_class).

    Hierarchical classification of protein targets. Self-referencing
    structure with up to 8 levels of depth. Used to annotate Target entities
    and aggregate bioactivity data by protein family.

    Entity ID: protein_class_id (string representation)
    Hierarchy: parent_id → protein_class_id
    Source: ChEMBL API /protein_class
    """

    # Primary identifier (REQUIRED)
    protein_class_id: int

    # Hierarchy (API-OPTIONAL)
    parent_id: int | None = None
    class_level: int | None = None

    # Classification data (API-OPTIONAL)
    pref_name: str | None = None
    short_name: str | None = None
    protein_class_desc: str | None = None
    definition: str | None = None

    # Additional metadata (API-OPTIONAL)
    sort_order: int | None = None
    replaced_by: int | None = None
    downgraded: int | None = None  # 0 or 1

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if self.protein_class_id < 1:
            raise ValueError(
                f"protein_class_id must be >= 1, got {self.protein_class_id}"
            )
        self._validate_class_level()
        self._validate_downgraded()

    def _validate_class_level(self) -> None:
        """Validate class_level is within 1-8 range if present."""
        if self.class_level is not None and not 1 <= self.class_level <= 8:
            raise ValueError(f"class_level must be 1-8, got {self.class_level}")

    def _validate_downgraded(self) -> None:
        """Validate downgraded flag is 0 or 1 if present."""
        if self.downgraded is not None and self.downgraded not in (0, 1):
            raise ValueError(f"downgraded must be 0 or 1, got {self.downgraded}")

    def is_root(self) -> bool:
        """Check if this is a root node (no parent)."""
        return self.parent_id is None

    def is_deprecated(self) -> bool:
        """Check if this classification is deprecated."""
        return self.replaced_by is not None or self.downgraded == 1


# Backward compatibility alias (deprecated)
# See ADR-024: Entity Naming Unification
Document = ChemblPublication
