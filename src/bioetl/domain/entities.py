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
from datetime import datetime, timezone
from typing import Optional

from bioetl.domain.types import EntityID, ContentHash, BatchID, RunID, RunType


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
    source_batch_id: BatchID
    ingestion_ts: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

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
    target_chembl_id: Optional[str] = None
    assay_chembl_id: Optional[str] = None
    document_chembl_id: Optional[str] = None
    record_id: Optional[int] = None
    src_id: Optional[int] = None

    # Molecule data
    canonical_smiles: Optional[str] = None
    molecule_pref_name: Optional[str] = None
    parent_molecule_chembl_id: Optional[str] = None

    # Target data
    target_pref_name: Optional[str] = None
    target_organism: Optional[str] = None
    target_tax_id: Optional[str] = None

    # Assay data
    assay_type: Optional[str] = None
    assay_description: Optional[str] = None
    assay_variant_accession: Optional[str] = None
    assay_variant_mutation: Optional[str] = None

    # BAO (BioAssay Ontology) annotations
    bao_endpoint: Optional[str] = None
    bao_format: Optional[str] = None
    bao_label: Optional[str] = None

    # Raw activity values
    type: Optional[str] = None
    value: Optional[float] = None
    units: Optional[str] = None
    relation: Optional[str] = None
    upper_value: Optional[float] = None
    text_value: Optional[str] = None

    # Standardized activity values
    standard_type: Optional[str] = None
    standard_value: Optional[float] = None
    standard_units: Optional[str] = None
    standard_relation: Optional[str] = None
    standard_upper_value: Optional[float] = None
    standard_text_value: Optional[str] = None
    standard_flag: Optional[int] = None

    # Derived metrics
    pchembl_value: Optional[float] = None
    ligand_efficiency: Optional[str] = None  # JSON string of dict

    # Units ontology
    qudt_units: Optional[str] = None
    uo_units: Optional[str] = None

    # Document/Publication data
    document_journal: Optional[str] = None
    document_year: Optional[int] = None

    # Quality annotations
    activity_comment: Optional[str] = None
    data_validity_comment: Optional[str] = None
    data_validity_description: Optional[str] = None
    potential_duplicate: Optional[int] = None

    # Action and properties
    action_type: Optional[str] = None
    activity_properties: Optional[str] = None  # JSON string of list
    toid: Optional[int] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if not self.activity_id:
            raise ValueError("Activity ID is required")
        if not self.molecule_chembl_id:
            raise ValueError("Molecule ChEMBL ID is required")

        # Invariant: If pchembl_value is present, it must be non-negative
        if self.pchembl_value is not None and self.pchembl_value < 0:
            raise ValueError(f"pChemBL value must be non-negative, got {self.pchembl_value}")


@dataclass(frozen=True, kw_only=True)
class Compound(BaseEntity):
    """Represents a chemical compound (PubChem Compound)."""

    cid: str
    molecular_formula: Optional[str] = None
    molecular_weight: Optional[str] = None  # Kept as string to preserve precision/format

    # Structure representations
    canonical_smiles: Optional[str] = None
    isomeric_smiles: Optional[str] = None
    inchi: Optional[str] = None
    inchikey: Optional[str] = None
    iupac_name: Optional[str] = None

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
    organism_id: Optional[int] = None
    sequence_length: Optional[int] = None

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
    title: str
    abstract: Optional[str] = None
    journal: Optional[str] = None
    publication_year: Optional[int] = None
    authors: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Post-initialization validation."""
        super().__post_init__()
        if not self.pmid:
            raise ValueError("Publication PMID is required")
        if not self.title:
            raise ValueError("Publication title is required")
