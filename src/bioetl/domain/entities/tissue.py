"""Tissue domain entity.

Represents a tissue from ChEMBL database.
A Tissue is a biological tissue used in assays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Tissue(EntityBase):
    """Domain entity representing a biological tissue.

    A Tissue encapsulates information about a tissue type used in assays,
    including its name, type, and source organism.

    Attributes:
        tissue_chembl_id: Unique ChEMBL tissue identifier (primary key).
        tissue_name: Preferred name of the tissue.
        tissue_type: High-level tissue classification.
        tissue_source_organism: Organism the tissue originates from.
        tissue_description: Free text description.

    Business Key:
        The business key is (tissue_chembl_id) as it's the unique identifier.

    Example:
        >>> tissue = Tissue.from_record({
        ...     'tissue_chembl_id': 'CHEMBL3638',
        ...     'tissue_name': 'Liver',
        ...     'tissue_source_organism': 'Homo sapiens',
        ... })
    """

    # Primary identifier
    tissue_chembl_id: str

    # Tissue information
    tissue_name: str | None = None
    tissue_type: str | None = None
    tissue_source_organism: str | None = None
    tissue_description: str | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("tissue_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "tissue_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.tissue_chembl_id.startswith("CHEMBL"):
            raise ValueError(
                f"Invalid tissue_chembl_id format: {self.tissue_chembl_id}"
            )

    @property
    def chembl_id(self) -> ChemblId:
        """Return tissue ID as ChemblId value object."""
        return ChemblId(self.tissue_chembl_id)

    @property
    def is_human(self) -> bool:
        """Check if tissue is from human."""
        return self.tissue_source_organism == "Homo sapiens"

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Tissue":
        """Create Tissue from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Tissue entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            tissue_chembl_id=extract_field(record, "tissue_chembl_id", required=True),
            tissue_name=extract_field(record, "tissue_name"),
            tissue_type=extract_field(record, "tissue_type"),
            tissue_source_organism=extract_field(record, "tissue_source_organism"),
            tissue_description=extract_field(record, "tissue_description"),
        )


__all__ = ["Tissue"]
