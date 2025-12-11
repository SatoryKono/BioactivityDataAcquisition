"""Target domain entity.

Represents a biological target from ChEMBL database.
A Target is the biological entity (protein, cell, organism, etc.)
that compounds are tested against in assays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Target(EntityBase):
    """Domain entity representing a biological target.

    A Target encapsulates information about the biological entity
    against which compounds are tested, including its type, organism,
    and external references.

    Attributes:
        target_chembl_id: Unique ChEMBL target identifier (primary key).
        target_type: Type of target (SINGLE PROTEIN, FAMILY, etc.).
        pref_name: Preferred name of the target.
        organism: Target organism.
        tax_id: NCBI Taxonomy ID.
        uniprot_id: Primary UniProt accession (for proteins).

    Business Key:
        The business key is (target_chembl_id) as it's the unique identifier.

    Example:
        >>> target = Target.from_record({
        ...     'target_chembl_id': 'CHEMBL1234',
        ...     'target_type': 'SINGLE PROTEIN',
        ...     'pref_name': 'Acetylcholinesterase',
        ...     'organism': 'Homo sapiens',
        ... })
    """

    # Primary identifier
    target_chembl_id: str

    # Target classification
    target_type: str
    pref_name: str | None = None

    # Organism information
    organism: str | None = None
    tax_id: int | None = None
    species_group_flag: bool | None = None

    # External references
    uniprot_id: str | None = None
    cross_references: str | None = None

    # Extended data (JSON serialized)
    target_components: str | None = None

    # Search relevance
    score: float | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("target_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "target_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.target_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid target_chembl_id format: {self.target_chembl_id}"
            )

    @property
    def chembl_id(self) -> ChemblId:
        """Return target ID as ChemblId value object."""
        return ChemblId(self.target_chembl_id)

    @property
    def is_single_protein(self) -> bool:
        """Check if target is a single protein."""
        return self.target_type == "SINGLE PROTEIN"

    @property
    def is_protein_family(self) -> bool:
        """Check if target is a protein family."""
        return self.target_type in ("PROTEIN FAMILY", "SELECTIVITY GROUP")

    @property
    def is_organism(self) -> bool:
        """Check if target is an organism."""
        return self.target_type == "ORGANISM"

    @property
    def is_cell_line(self) -> bool:
        """Check if target is a cell line."""
        return self.target_type == "CELL-LINE"

    @property
    def has_uniprot(self) -> bool:
        """Check if target has UniProt reference."""
        return self.uniprot_id is not None

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Target":
        """Create Target from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Target entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            # Required fields
            target_chembl_id=extract_field(record, "target_chembl_id", required=True),
            target_type=extract_field(record, "target_type", required=True),
            # Optional fields
            pref_name=extract_field(record, "pref_name"),
            organism=extract_field(record, "organism"),
            tax_id=extract_field(record, "tax_id", coerce=int),
            species_group_flag=extract_field(record, "species_group_flag"),
            uniprot_id=extract_field(record, "uniprot_id"),
            cross_references=extract_field(record, "cross_references"),
            target_components=extract_field(record, "target_components"),
            score=extract_field(record, "score", coerce=float),
        )


__all__ = ["Target"]
