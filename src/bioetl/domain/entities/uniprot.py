"""UniProt domain entities.

Contains entities for UniProt data: Protein, IDMappingResult.
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
class Protein(BaseEntity):
    """Represents a protein target (UniProt).

    Required fields: accession, entry_name
    Optional fields: protein_name, gene_names, organism_id, sequence_length
    """

    accession: str
    entry_name: str
    protein_name: str | None = None
    gene_names: list[str] = field(default_factory=list)
    organism_id: int | None = None
    sequence_length: int | None = None

    def __post_init__(self) -> None:
        super().__post_init__()
        self._validate_invariants()

    def _validate_invariants(self) -> None:
        if not self.accession:
            raise ValueError("Protein accession is required")
        if not self.entry_name:
            raise ValueError("Protein entry_name is required")
        self._validate_sequence_length()

    def _validate_sequence_length(self) -> None:
        """Validate sequence_length is positive if present."""
        if self.sequence_length is not None and self.sequence_length <= 0:
            raise ValueError(
                f"Sequence length must be positive, got {self.sequence_length}"
            )
