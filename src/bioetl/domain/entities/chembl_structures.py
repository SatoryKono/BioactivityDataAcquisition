"""ChEMBL structural domain entities.

Contains ChemblPublication, DocumentTerm, DocumentSimilarity, Target,
TargetComponent, CellLine, Molecule, and ProteinClassification entities.
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.entities.base import BaseEntity
from bioetl.domain.entities.publication_base import PublicationEntityBase


@dataclass(frozen=True, kw_only=True)
class ChemblPublication(PublicationEntityBase):
    """Represents a scientific document/publication (ChEMBL Document).

    Maps to ChEMBL API endpoint: /document

    Содержит только поля ChEMBL; общие поля публикации наследуются
    из PublicationEntityBase.
    See: https://www.ebi.ac.uk/chembl/api/data/document
    """

    # Primary identifier
    publication_id: str

    volume: str | None = None
    issue: str | None = None

    # Source information
    src_id: int | None = None

    # ChEMBL release metadata
    chembl_release: str | None = None  # e.g., CHEMBL_1, CHEMBL_34
    creation_date: str | None = None  # Record creation date in ChEMBL (YYYY-MM-DD)

    # Note: _dq_warn and _dq_error are inherited from BaseEntity

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.publication_id:
            raise ValueError("ChemblPublication publication_id is required")


@dataclass(frozen=True, kw_only=True)
class DocumentTerm(BaseEntity):
    """Represents a term associated with a ChEMBL Document.

    Terms include MeSH headings, MeSH qualifiers, keywords, and concepts
    extracted from Document records. This is a derived entity that flattens
    the 1:M relationship between documents and their associated terms.

    Source: Nested in ChEMBL API /document response (mesh_terms, keywords fields)

    Composite Key: publication_id + term_type + term (normalized)
    See: https://www.ebi.ac.uk/chembl/api/data/document
    """

    # === Composite Key Fields ===
    publication_id: str  # FK → Document
    term: str  # Term text (e.g., "Aspirin", "kinase inhibitor")
    term_type: str  # MESH_HEADING, MESH_QUALIFIER, KEYWORD, CONCEPT

    # === MeSH-specific Fields ===
    mesh_id: str | None = None  # MeSH identifier (e.g., "D001241")
    qualifier: str | None = None  # MeSH qualifier (e.g., "pharmacology")

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.publication_id:
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
    target_id: str

    # Core metadata
    pref_name: str | None = None
    target_type: str | None = None  # SINGLE PROTEIN, PROTEIN COMPLEX, ORGANISM, etc.
    organism: str | None = None
    # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
    taxonomy_id: int | None = None
    # Organism cellularity classification (acellular/unicellular/multicellular)
    organism_class: str | None = None
    species_group_flag: bool | None = None
    description: str | None = None
    downgraded: bool | None = None  # Flag for deprecated/downgraded records
    pipeline_stages: str | None = None  # JSON string (for complexes/families)

    # Complex fields (JSON serialized)
    target_components: str | None = None  # JSON string of array
    target_component_synonyms: str | None = None  # JSON string of aggregated synonyms
    cross_references: str | None = None  # JSON string of array

    # Flattened component fields (aggregated lists)
    component_accessions: list[str] | None = None
    primary_component_id: int | None = None  # Primary component ID
    component_ids: list[int] | None = None
    component_types: list[str] | None = None
    component_relationships: list[str] | None = None
    component_descriptions: list[str] | None = None

    # Note: protein_classifications are NOT available in /target endpoint.
    # They are only available via /target_component endpoint (TargetComponent entity).

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.target_id:
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
    # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
    taxonomy_id: int | None = None

    # Complex fields (JSON serialized)
    target_component_synonyms: str | None = None  # JSON string of list
    target_component_xrefs: str | None = None  # JSON string of list
    protein_classifications: str | None = None  # JSON string of list (forensic)

    # Flattened fields (extracted from protein_classifications)
    protein_classification_id: int | None = (
        None  # Primary classification (first from list)
    )
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
    They have M:N relationship with Assay (via assay.cell_id FK).

    Contains all fields from ChEMBL cell_line API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/cell_line
    """

    # Primary identifier (REQUIRED)
    cell_id: str

    # Core metadata (cell_name is REQUIRED per task spec)
    cell_name: str

    # Optional metadata (API-OPTIONAL)
    cell_description: str | None = None

    # Source information (API-OPTIONAL)
    cell_source_tissue: str | None = None
    cell_source_organism: str | None = None
    # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
    cell_source_taxonomy_id: int | None = None

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
        if not self.cell_id:
            raise ValueError("Cell ChEMBL ID is required")
        if not self.cell_name:
            raise ValueError("Cell name is required")
        if (
            self.cell_source_taxonomy_id is not None
            and self.cell_source_taxonomy_id < 1
        ):
            raise ValueError(
                f"cell_source_taxonomy_id must be >= 1, got {self.cell_source_taxonomy_id}"
            )


@dataclass(frozen=True, kw_only=True)
class Molecule(BaseEntity):
    """Represents a chemical compound (ChEMBL Molecule).

    Contains all fields from ChEMBL molecule API endpoint.
    See: https://www.ebi.ac.uk/chembl/api/data/molecule
    """

    # Primary identifier
    molecule_id: str

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

    # Flattened Properties (canonical alias names, unified for Gold)
    logp: float | None = None
    logp_method: str | None = None
    mw_freebase: float | None = None
    molecular_weight: float | None = None
    hba_count: int | None = None
    hbd_count: int | None = None
    polar_surface_area: float | None = None
    rotatable_bond_count: int | None = None
    ro5_violation_count: int | None = None
    heavy_atom_count: int | None = None
    aromatic_ring_count: int | None = None
    qed_score: float | None = None
    molecular_formula: str | None = None
    ro3_pass: str | None = None  # "Y" or "N"

    # Flattened Structures (unified naming without structure_ prefix)
    canonical_smiles: str | None = None
    standard_inchi: str | None = None
    # Standardized to 'inchi_key' (no underscore) for IUPAC/PubChem consistency
    inchi_key: str | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.molecule_id:
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
    pubmed_id1: str | None = None  # Numeric string for cross-provider consistency
    pubmed_id2: str | None = None  # Numeric string for cross-provider consistency

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


__all__ = [
    "CellLine",
    "ChemblPublication",
    "DocumentSimilarity",
    "DocumentTerm",
    "Molecule",
    "ProteinClassification",
    "Target",
    "TargetComponent",
]
