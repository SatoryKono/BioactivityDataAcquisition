"""Cell domain entity.

Represents a cell line from ChEMBL database.
A Cell is a cell line used in biological assays.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, ClassVar, Mapping

from bioetl.domain.entities.base import EntityBase, extract_field
from bioetl.domain.value_objects import ChemblId


@dataclass(frozen=True)
class Cell(EntityBase):
    """Domain entity representing a cell line.

    A Cell encapsulates information about a cell line used in assays,
    including its name, type, and source organism.

    Attributes:
        cell_chembl_id: Unique ChEMBL cell identifier (primary key).
        cell_name: Preferred name of the cell line.
        cell_type: High-level cell type classification.
        cell_source_organism: Organism the cell originates from.
        cell_description: Free text description.

    Business Key:
        The business key is (cell_chembl_id) as it's the unique identifier.

    Example:
        >>> cell = Cell.from_record({
        ...     'cell_chembl_id': 'CHEMBL3307641',
        ...     'cell_name': 'HeLa',
        ...     'cell_type': 'Epithelial',
        ...     'cell_source_organism': 'Homo sapiens',
        ... })
    """

    # Primary identifier
    cell_chembl_id: str

    # Cell information
    cell_name: str | None = None
    cell_type: str | None = None
    cell_source_organism: str | None = None
    cell_description: str | None = None

    # Class configuration
    BUSINESS_KEY_FIELDS: ClassVar[tuple[str, ...]] = ("cell_chembl_id",)
    PRIMARY_KEY_FIELD: ClassVar[str] = "cell_chembl_id"

    def __post_init__(self) -> None:
        """Validate entity invariants."""
        # Validate ChEMBL ID format
        if not self.cell_chembl_id.startswith("CHEMBL"):
            raise ValueError(f"Invalid cell_chembl_id format: {self.cell_chembl_id}")

    @property
    def chembl_id(self) -> ChemblId:
        """Return cell ID as ChemblId value object."""
        return ChemblId(self.cell_chembl_id)

    @property
    def is_human(self) -> bool:
        """Check if cell is from human."""
        return self.cell_source_organism == "Homo sapiens"

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Cell":
        """Create Cell from raw record dictionary.

        Args:
            record: Dictionary from API response or database.

        Returns:
            Cell entity instance.

        Raises:
            ValueError: If required fields are missing.
        """
        return cls(
            cell_chembl_id=extract_field(record, "cell_chembl_id", required=True),
            cell_name=extract_field(record, "cell_name"),
            cell_type=extract_field(record, "cell_type"),
            cell_source_organism=extract_field(record, "cell_source_organism"),
            cell_description=extract_field(record, "cell_description"),
        )


__all__ = ["Cell"]
