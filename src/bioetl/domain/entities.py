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
    ligand_efficiency: str | None = None  # JSON string of dict

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

    # Action and properties
    action_type: str | None = None
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
            raise ValueError(f"pChemBL value must be non-negative, got {self.pchembl_value}")


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
            raise ValueError("Compound must have at least one structural identifier (SMILES/InChI)")


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
            raise ValueError(f"Sequence length must be positive, got {self.sequence_length}")


@dataclass(frozen=True, kw_only=True)
class Publication(BaseEntity):
    """Represents a scientific publication (e.g., from PubMed)."""

    pmid: str
    title: str | None = None  # None when title unavailable from source
    abstract: str | None = None
    journal: str | None = None
    publication_year: int | None = None
    authors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.pmid:
            raise ValueError("Publication PMID is required")
