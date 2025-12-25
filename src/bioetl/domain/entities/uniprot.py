"""UniProt domain entities.

Contains entities for UniProt data: Protein.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.entities.base import BaseEntity


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
