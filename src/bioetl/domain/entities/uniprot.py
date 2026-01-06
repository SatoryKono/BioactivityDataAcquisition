"""UniProt domain entities.

Contains entities for UniProt data:
- UniprotTarget: Domain entity (canonical name) for protein targets
- Protein: Deprecated alias for UniprotTarget (backward compatibility)
- IDMappingResult: ID mapping result entity

.. versionchanged:: 2.0.0
    Protein renamed to UniprotTarget for Ubiquitous Language alignment.
    The deprecated Protein alias remains for backward compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from bioetl.domain.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class IDMappingResult(BaseEntity):
    """Result of UniProt ID Mapping operation.

    Maps ChEMBL target IDs to UniProt accessions using UniProt ID Mapping REST API.

    Required fields: target_chembl_id, mapping_status
    Optional fields: uniprot_accession (None if mapping not found)

    Attributes:
        target_chembl_id: Source ChEMBL target identifier (e.g., CHEMBL204)
        uniprot_accession: Mapped UniProt accession (e.g., P00742) or None if not found
        mapping_status: Status of mapping operation: 'found', 'not_found', 'error'
    """

    target_chembl_id: str
    uniprot_accession: str | None = None
    mapping_status: Literal["found", "not_found", "error"] = "not_found"

    def __post_init__(self) -> None:
        """Validate required fields."""
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        """Validate domain-specific invariants."""
        if not self.target_chembl_id:
            raise ValueError("target_chembl_id is required")
        if self.mapping_status not in ("found", "not_found", "error"):
            raise ValueError(
                f"Invalid mapping_status: {self.mapping_status}. "
                "Must be one of: 'found', 'not_found', 'error'"
            )
        # If status is 'found', accession should be present
        if self.mapping_status == "found" and not self.uniprot_accession:
            raise ValueError(
                "uniprot_accession is required when mapping_status is 'found'"
            )


@dataclass(frozen=True, kw_only=True)
class UniprotTarget(BaseEntity):
    """Represents a protein target (UniProt).

    Canonical name for UniProt's Protein entity, aligned with Ubiquitous Language.
    In the bioactivity domain, proteins are typically biological targets.

    Extended entity with comprehensive UniProt data including:
    - Core identifiers (accession, entry_name, entry_type)
    - Protein names (recommended, short, alternative, EC numbers)
    - Gene information (primary, synonyms, ORF names)
    - Organism and taxonomy
    - Evidence and quality metrics
    - Sequence information
    - Functional annotations (comments)
    - Cross-references (GO, DrugBank, ChEMBL, GtoPdb)
    - Features and keywords

    Required fields: accession, entry_name
    All other fields are optional.

    .. versionadded:: 2.0.0
        Replaces :class:`Protein` as the canonical entity name.
    """

    # Core identifiers
    accession: str
    entry_name: str
    entry_type: str | None = None
    secondary_accessions: str | None = None  # JSON array

    # Protein names
    protein_name: str | None = None
    protein_short_names: str | None = None  # JSON array
    protein_alternative_names: str | None = None  # JSON array
    protein_ec_numbers: str | None = None  # JSON array
    flag: str | None = None  # Fragment/Precursor

    # Gene names
    gene_names: list[str] = field(default_factory=list)
    gene_primary: str | None = None
    gene_synonyms: str | None = None  # JSON array
    gene_orf_names: str | None = None  # JSON array

    # Organism
    organism_scientific: str | None = None
    organism_common: str | None = None
    organism_id: int | None = None  # Legacy: same as taxonomy_id
    taxonomy_id: int | None = None
    lineage: str | None = None  # JSON array

    # Evidence & Quality
    protein_existence: str | None = None
    annotation_score: int | None = None
    reviewed: bool = False

    # Sequence
    sequence: str | None = None
    sequence_length: int | None = None
    sequence_mass: int | None = None
    sequence_checksum: str | None = None
    sequence_modified: str | None = None  # ISO date

    # Entry metadata
    entry_version: int | None = None
    entry_created: str | None = None  # ISO date
    entry_modified: str | None = None  # ISO date

    # Functional annotations (JSON arrays)
    function_comment: str | None = None
    catalytic_activity: str | None = None
    activity_regulation: str | None = None
    subunit: str | None = None
    pathway: str | None = None
    subcellular_location: str | None = None
    tissue_specificity: str | None = None
    alternative_products: str | None = None
    disease_involvement: str | None = None
    pharmaceutical_use: str | None = None
    similarity_comment: str | None = None
    caution: str | None = None

    # Cross-references (JSON arrays)
    go_terms: str | None = None
    drugbank_ids: str | None = None
    chembl_ids: str | None = None
    guidetopharmacology_ids: str | None = None

    # Features & Keywords (JSON arrays)
    features: str | None = None
    keywords: str | None = None

    # Counts
    cross_reference_count: int | None = None
    feature_count: int | None = None
    keyword_count: int | None = None
    publication_count: int | None = None
    isoform_count: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.accession:
            raise ValueError("UniprotTarget accession is required")
        if not self.entry_name:
            raise ValueError("UniprotTarget entry_name is required")
        self._validate_sequence_length()
        self._validate_annotation_score()

    def _validate_sequence_length(self) -> None:
        """Validate sequence_length is positive if present."""
        if self.sequence_length is not None and self.sequence_length <= 0:
            raise ValueError(
                f"Sequence length must be positive, got {self.sequence_length}"
            )

    def _validate_annotation_score(self) -> None:
        """Validate annotation_score is 1-5 if present."""
        if self.annotation_score is not None and not 1 <= self.annotation_score <= 5:
            raise ValueError(
                f"Annotation score must be 1-5, got {self.annotation_score}"
            )


# === Deprecated Aliases (backward compatibility) ===

# Protein is a deprecated alias for UniprotTarget.
# Use UniprotTarget in new code for Ubiquitous Language alignment.
#
# .. deprecated:: 2.0.0
#     Use :class:`UniprotTarget` instead.
#
# Migration:
#     # Before
#     from bioetl.domain.entities import Protein
#
#     # After
#     from bioetl.domain.entities import UniprotTarget
Protein = UniprotTarget
